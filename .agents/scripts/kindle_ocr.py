"""
kindle_ocr.py
Kindle Cloud Reader を Playwright で自動操作し、全書籍をページ単位でスクリーンショット撮影、
Gemini API で構造化 Markdown に変換して Source/KindleOCR/ へ保存する。

使い方:
  python .agents/scripts/kindle_ocr.py

環境変数:
  GEMINI_API_KEY  Google AI Studio で取得したAPIキー
  VAULT_PATH      Vault のルートパス（省略時はスクリプトの3階層上）
"""

import os
import sys
import json
import time
import tempfile
import shutil
import re
from datetime import datetime
from pathlib import Path

# ---------- 設定 ----------
KINDLE_URL = "https://read.amazon.co.jp"
GEMINI_MODEL = "gemini-3.1-flash-lite-preview"
RATE_LIMIT_SLEEP = 1.5      # Gemini APIコール間のスリープ（秒）
MAX_RETRIES = 3             # Gemini APIリトライ上限
DUPLICATE_THRESHOLD = 5     # 連続同一スクリーンショット数で読了と判定

OCR_PROMPT = """この画像はKindleの電子書籍のページです。ページの文字をMarkdownに変換してください。

ルール：
- 見出し・箇条書き・太字・引用（>）はMarkdownで再現する
- ふりがな（ルビ）は除去する
- ページ番号・ヘッダー・フッターは除去する
- 図・表・グラフは ![[図: 簡潔な説明]] というプレースホルダーに置き換える
- Markdownテキストのみを返す。説明・前置き・コードブロックは不要
""".strip()


# ---------- パス解決 ----------
def get_vault_path() -> Path:
    env = os.environ.get("VAULT_PATH")
    if env:
        return Path(env)
    return Path(__file__).parent.parent.parent


def get_ocr_dir(vault: Path) -> Path:
    d = vault / "Source" / "KindleOCR"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_log_path(vault: Path) -> Path:
    return vault / ".agents" / "logs" / "kindle_ocr_log.json"


# ---------- ログ管理 ----------
def load_log(vault: Path) -> dict:
    log_path = get_log_path(vault)
    if not log_path.exists():
        return {"processed": [], "in_progress": {}}
    try:
        return json.loads(log_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        return {"processed": [], "in_progress": {}}


def save_log(vault: Path, log: dict) -> None:
    log_path = get_log_path(vault)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = log_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(log_path)


# ---------- ユーティリティ ----------
def sanitize_filename(title: str) -> str:
    """Windows禁止文字を除去してファイル名に使える文字列を返す"""
    return re.sub(r'[\\/:*?"<>|]', "_", title).strip()


def find_kindle_highlight_file(vault: Path, title: str) -> str | None:
    """Source/Kindle/ 内でタイトルを含むファイルを探し Obsidian リンク文字列を返す"""
    kindle_dir = vault / "Source" / "Kindle"
    if not kindle_dir.exists():
        return None
    # タイトルの主要部分（記号を除いた単語）で部分一致検索
    title_clean = re.sub(r'[^\w\u3040-\u9FFF]', '', title)
    for f in kindle_dir.iterdir():
        if f.suffix == ".md":
            fname_clean = re.sub(r'[^\w\u3040-\u9FFF]', '', f.stem)
            if title_clean and title_clean in fname_clean:
                return f"[[Source/Kindle/{f.name}]]"
    return None


# ---------- Gemini連携 ----------
def build_ocr_client(api_key: str):
    try:
        from google import genai
    except ImportError:
        print("ERROR: google-genai がインストールされていません。")
        print("  pip install google-genai")
        sys.exit(1)
    return genai.Client(api_key=api_key)


def ocr_page(client, screenshot_path: Path, retry: int = 0) -> str:
    """スクリーンショットを Gemini に送り Markdown テキストを返す"""
    from google.genai import types as genai_types

    try:
        img_file = client.files.upload(
            file=str(screenshot_path),
            config=genai_types.UploadFileConfig(mime_type="image/png")
        )

        # アップロード完了待機
        while img_file.state.name == "PROCESSING":
            time.sleep(1)
            img_file = client.files.get(name=img_file.name)

        if img_file.state.name == "FAILED":
            raise RuntimeError(f"Gemini アップロード失敗: {screenshot_path.name}")

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[OCR_PROMPT, img_file]
        )

        # アップロードしたファイルを削除
        try:
            client.files.delete(name=img_file.name)
        except Exception:
            pass

        return response.text.strip()

    except Exception as e:
        if retry < MAX_RETRIES:
            wait = 2 * (retry + 1)
            print(f"    リトライ {retry + 1}/{MAX_RETRIES}（{wait}秒後）: {e}")
            time.sleep(wait)
            return ocr_page(client, screenshot_path, retry + 1)
        raise


# ---------- 画像比較 ----------
def images_are_identical(path_a: Path, path_b: Path, threshold: int = 1000) -> bool:
    """2枚のPNGのピクセル差分合計が threshold 未満なら同一と判定"""
    try:
        from PIL import Image, ImageChops
    except ImportError:
        print("ERROR: Pillow がインストールされていません。")
        print("  pip install pillow")
        sys.exit(1)

    img_a = Image.open(path_a).convert("RGB")
    img_b = Image.open(path_b).convert("RGB")
    if img_a.size != img_b.size:
        return False
    diff = ImageChops.difference(img_a, img_b)
    total = sum(sum(pixel) for pixel in diff.getdata())
    return total < threshold


# ---------- Playwright操作 ----------
def launch_browser(pw):
    """ヘッドフルモードで Chromium を起動"""
    browser = pw.chromium.launch(headless=False)
    context = browser.new_context(
        viewport={"width": 1280, "height": 800},
        locale="ja-JP"
    )
    page = context.new_page()
    return browser, page


def open_kindle_library(page) -> None:
    """Kindle Cloud Reader のライブラリ画面に遷移して待機"""
    print(f"Kindle Cloud Reader を開いています: {KINDLE_URL}")
    page.goto(KINDLE_URL, timeout=60000)

    # ログイン済みの場合はライブラリが表示される
    # ライブラリの書籍タイル、またはログイン画面が現れるまで待機
    try:
        page.wait_for_selector(
            '[data-testid="content-tile-list"], .kp-notebook-library-each-book, '
            '#library-container, .book-list, .Ebook-shelf',
            timeout=30000
        )
    except Exception:
        print("  ライブラリ読み込みタイムアウト。ログインが必要な場合は手動でログインしてください。")
        print("  ログイン完了後 Enter を押してください: ", end="", flush=True)
        input()
        page.wait_for_timeout(3000)


def get_library_books(page) -> list[dict]:
    """ライブラリから全書籍タイトルとクリック要素を収集する"""
    print("書籍リストを収集中...")

    # 仮想スクロールで全タイルを読み込む
    prev_count = 0
    for _ in range(50):  # 最大50スクロール
        page.keyboard.press("End")
        page.wait_for_timeout(800)
        tiles = page.query_selector_all(
            '[data-testid="content-tile-list"] > *, '
            '.book-list .book-container, '
            '.kp-notebook-library-each-book, '
            '.Ebook-shelf .book'
        )
        if len(tiles) == prev_count:
            break
        prev_count = len(tiles)

    # タイトル抽出
    books = []
    for tile in tiles:
        try:
            # 複数のセレクタパターンを試みる
            title_el = (
                tile.query_selector('[data-testid="content-title"]') or
                tile.query_selector('.book-title') or
                tile.query_selector('.title') or
                tile.query_selector('h2') or
                tile.query_selector('h3')
            )
            if title_el:
                title = title_el.inner_text().strip()
            else:
                title = tile.get_attribute("aria-label") or ""
                title = title.strip()

            if title:
                books.append({"title": title, "tile": tile})
        except Exception:
            continue

    print(f"  {len(books)} 冊見つかりました")
    return books


def open_book(page, book: dict) -> dict:
    """書籍タイルをクリックしてリーダーを起動、メタデータを返す"""
    title = book["title"]
    print(f"\n書籍を開いています: {title}")

    book["tile"].click()

    # リーダーの読書エリアが現れるまで待機（最大60秒）
    try:
        page.wait_for_selector(
            '#book-reader, .book-reader, iframe#KindleReaderIframe, '
            '[data-testid="reader-container"], .kr-page-turn-area',
            timeout=60000
        )
    except Exception:
        print("  リーダー起動タイムアウト。手動で開いて Enter を押してください: ", end="", flush=True)
        input()

    page.wait_for_timeout(2000)

    # 著者情報の取得を試みる（取得できなければ空文字）
    author = ""
    try:
        author_el = page.query_selector(
            '.book-author, [data-testid="content-author"], .author'
        )
        if author_el:
            author = author_el.inner_text().strip()
    except Exception:
        pass

    return {"title": title, "author": author}


def screenshot_current_page(page, out_path: Path) -> None:
    """読書エリアのスクリーンショットを撮影して保存"""
    # リーダー領域を特定してクリップ
    reader_el = (
        page.query_selector('#book-reader') or
        page.query_selector('.book-reader') or
        page.query_selector('[data-testid="reader-container"]') or
        page.query_selector('.kr-page-turn-area')
    )
    if reader_el:
        reader_el.screenshot(path=str(out_path))
    else:
        # フォールバック: ページ全体
        page.screenshot(path=str(out_path))


def turn_page(page) -> None:
    """右矢印キーでページをめくり、アニメーション完了を待機"""
    page.keyboard.press("ArrowRight")
    page.wait_for_timeout(500)


def close_book(page) -> None:
    """ライブラリ画面に戻る"""
    try:
        # 「戻る」ボタンまたは閉じるボタンを探す
        back_btn = (
            page.query_selector('[data-testid="back-to-library"]') or
            page.query_selector('.close-button') or
            page.query_selector('[aria-label="ライブラリに戻る"]')
        )
        if back_btn:
            back_btn.click()
            page.wait_for_timeout(2000)
        else:
            page.goto(KINDLE_URL)
            page.wait_for_timeout(3000)
    except Exception:
        page.goto(KINDLE_URL)
        page.wait_for_timeout(3000)


# ---------- ファイル出力 ----------
def get_partial_path(vault: Path, title: str) -> Path:
    ocr_dir = get_ocr_dir(vault)
    return ocr_dir / f"{sanitize_filename(title)}.partial.md"


def write_partial(vault: Path, title: str, pages: list[str]) -> None:
    """処理途中のテキストを .partial.md に保存（クラッシュ時の再開用）"""
    partial_path = get_partial_path(vault, title)
    partial_path.write_text("\n\n---\n\n".join(pages), encoding="utf-8")


def read_partial(vault: Path, title: str) -> list[str]:
    """既存の .partial.md からページテキストリストを復元"""
    partial_path = get_partial_path(vault, title)
    if not partial_path.exists():
        return []
    content = partial_path.read_text(encoding="utf-8")
    return [p.strip() for p in content.split("\n\n---\n\n") if p.strip()]


def write_ocr_output(vault: Path, meta: dict, pages: list[str]) -> None:
    """最終的な OCR 結果を Source/KindleOCR/[title].md に書き出す"""
    ocr_dir = get_ocr_dir(vault)
    filename = sanitize_filename(meta["title"]) + ".md"
    out_path = ocr_dir / filename

    # Source/Kindle/ の対応ハイライトファイルへのリンクを探す
    highlight_link = find_kindle_highlight_file(vault, meta["title"])
    highlight_line = (
        f'kindle_highlights: "{highlight_link}"'
        if highlight_link else
        "kindle_highlights: null"
    )

    frontmatter = f"""---
title: "{meta['title']}"
author: "{meta.get('author', '')}"
processed_date: {datetime.now().strftime('%Y-%m-%d')}
source: kindle_ocr
pages: {len(pages)}
{highlight_line}
---"""

    body = "\n\n---\n\n".join(pages)
    out_path.write_text(frontmatter + "\n\n" + body + "\n", encoding="utf-8")
    print(f"  → 保存: {out_path.relative_to(vault)}")

    # partial ファイルを削除
    partial_path = get_partial_path(vault, meta["title"])
    if partial_path.exists():
        partial_path.unlink()


# ---------- 書籍処理ループ ----------
def process_book(page, book_meta: dict, client, log: dict, vault: Path, tmpdir: Path) -> None:
    title = book_meta["title"]
    print(f"  OCR 処理開始: {title}")

    # 再開ページ番号と既存テキストの復元
    in_progress_info = log.get("in_progress", {}).get(title, {})
    start_page = in_progress_info.get("last_page", 0)
    pages_text = read_partial(vault, title) if start_page > 0 else []

    if start_page > 0:
        print(f"  前回の中断から再開: ページ {start_page} から")
        for _ in range(start_page):
            turn_page(page)

    consecutive_dupes = 0
    prev_screenshot: Path | None = None
    n = start_page

    while True:
        current_screenshot = tmpdir / f"{sanitize_filename(title)}_page_{n:04d}.png"
        screenshot_current_page(page, current_screenshot)

        # 読了判定（連続同一画像）
        if prev_screenshot and prev_screenshot.exists():
            if images_are_identical(prev_screenshot, current_screenshot):
                consecutive_dupes += 1
                print(f"  ページ {n}: 同一画像 ({consecutive_dupes}/{DUPLICATE_THRESHOLD})")
                if consecutive_dupes >= DUPLICATE_THRESHOLD:
                    print("  読了を検出しました。")
                    current_screenshot.unlink(missing_ok=True)
                    break
            else:
                consecutive_dupes = 0

        # OCR
        try:
            print(f"  ページ {n}: OCR中...", end="", flush=True)
            text = ocr_page(client, current_screenshot)
            pages_text.append(text)
            print(f" {len(text)}文字")
        except Exception as e:
            print(f"\n  ERROR ページ {n}: {e}")
            # エラーページはスキップして続行
            pages_text.append(f"<!-- OCRエラー: ページ {n} -->")

        # スクリーンショット削除
        current_screenshot.unlink(missing_ok=True)

        # 進捗保存
        if "in_progress" not in log:
            log["in_progress"] = {}
        log["in_progress"][title] = {
            "last_page": n + 1,
            "title": title,
            "author": book_meta.get("author", "")
        }
        save_log(vault, log)
        write_partial(vault, title, pages_text)

        prev_screenshot = current_screenshot  # パスのみ保持（既に削除済み）

        turn_page(page)
        time.sleep(RATE_LIMIT_SLEEP)
        n += 1

    # 最終出力
    write_ocr_output(vault, book_meta, pages_text)

    # ログ更新
    if title not in log.get("processed", []):
        log.setdefault("processed", []).append(title)
    log.get("in_progress", {}).pop(title, None)
    save_log(vault, log)

    print(f"  完了: {n} ページ処理")


# ---------- エントリーポイント ----------
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Kindle Cloud Reader OCR Pipeline")
    parser.add_argument("--one", action="store_true", help="1冊だけ処理して終了する")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: 環境変数 GEMINI_API_KEY が設定されていません。")
        print("  Google AI Studio (https://aistudio.google.com) でAPIキーを取得し、")
        print("  環境変数 GEMINI_API_KEY に設定してください。")
        sys.exit(1)

    vault = get_vault_path()
    print(f"Vault: {vault}")

    ocr_dir = get_ocr_dir(vault)
    print(f"出力先: {ocr_dir}")

    log = load_log(vault)
    client = build_ocr_client(api_key)

    # 一時フォルダ（OS の temp 領域、Vault外）
    tmpdir = Path(tempfile.mkdtemp(prefix="kindle_ocr_"))
    print(f"一時フォルダ: {tmpdir}")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: playwright がインストールされていません。")
        print("  pip install playwright && playwright install chromium")
        sys.exit(1)

    try:
        with sync_playwright() as pw:
            browser, page = launch_browser(pw)
            try:
                open_kindle_library(page)
                books = get_library_books(page)

                if not books:
                    print("書籍が見つかりませんでした。ライブラリを確認してください。")
                    return

                processed = log.get("processed", [])
                unprocessed = [b for b in books if b["title"] not in processed]
                if args.one:
                    unprocessed = unprocessed[:1]
                print(f"\n未処理書籍: {len(unprocessed)} / {len(books)} 冊")

                for book in unprocessed:
                    try:
                        open_kindle_library(page)
                        book_meta = open_book(page, book)
                        process_book(page, book_meta, client, log, vault, tmpdir)
                    except KeyboardInterrupt:
                        print("\n中断しました。次回実行時に続きから再開できます。")
                        raise
                    except Exception as e:
                        print(f"  ERROR 書籍処理失敗 ({book['title']}): {e}")
                        try:
                            close_book(page)
                        except Exception:
                            pass

                print("\n全書籍の処理が完了しました。")

            finally:
                browser.close()

    except KeyboardInterrupt:
        pass
    finally:
        # 一時フォルダを削除
        shutil.rmtree(tmpdir, ignore_errors=True)
        print(f"一時フォルダを削除しました: {tmpdir}")


if __name__ == "__main__":
    main()
