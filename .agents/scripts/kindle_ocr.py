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
import subprocess
from datetime import datetime
from pathlib import Path

# ---------- 設定 ----------
KINDLE_URL = "https://read.amazon.co.jp"
GEMINI_MODEL = "gemini-3.1-flash-lite-preview"
RATE_LIMIT_SLEEP = 1.5      # Gemini APIコール間のスリープ（秒）
MAX_RETRIES = 3             # Gemini APIリトライ上限
DUPLICATE_THRESHOLD = 5     # 連続同一スクリーンショット数で読了と判定
MIN_PAGES_FOR_COMPLETE = 10 # これ未満で終了した場合は読込失敗の可能性が高い
OPPOSITE_PAGE_KEY = {"ArrowRight": "ArrowLeft", "ArrowLeft": "ArrowRight"}

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


# ---------- スキップリスト ----------
SKIP_LIST_PATH = "Source/KindleOCR/kindle_skip_list.md"

def load_skip_list(vault: Path) -> list[str]:
    """Tasks/kindle_skip_list.md のチェック済み項目をスキップタイトルとして返す"""
    skip_path = vault / SKIP_LIST_PATH
    if not skip_path.exists():
        return []
    skipped = []
    for line in skip_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("- [x]") or line.startswith("- [X]"):
            title = line[5:].strip()
            if title:
                skipped.append(title)
    return skipped


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


def is_kindle_pc_running() -> bool:
    """WindowsのKindle for PCプロセス起動有無を返す"""
    if os.name != "nt":
        return False
    try:
        proc = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq Kindle.exe"],
            capture_output=True,
            text=True,
            encoding="cp932",
            errors="ignore",
            check=False,
        )
        return "Kindle.exe" in proc.stdout
    except Exception:
        return False


def close_kindle_pc() -> bool:
    """Kindle for PCを終了する。終了指示を出せたらTrue"""
    if os.name != "nt":
        return False
    try:
        subprocess.run(
            ["taskkill", "/IM", "Kindle.exe", "/F"],
            capture_output=True,
            text=True,
            encoding="cp932",
            errors="ignore",
            check=False,
        )
        return True
    except Exception:
        return False


def open_kindle_library(page) -> None:
    """Kindle Cloud Reader のライブラリ画面に遷移して待機"""
    if is_kindle_pc_running():
        print("Kindle for PC が起動中のため終了します...")
        close_kindle_pc()
        page.wait_for_timeout(800)

    print(f"Kindle Cloud Reader を開いています: {KINDLE_URL}")
    page.goto(KINDLE_URL, timeout=60000)
    dismiss_library_popups(page)

    # ログイン済みの場合はライブラリが表示される
    # ライブラリの書籍タイル、またはログイン画面が現れるまで待機
    try:
        page.wait_for_selector('[role="listitem"]', timeout=30000)
    except Exception:
        print("  ライブラリ読み込みタイムアウト。ログインが必要な場合は手動でログインしてください。")
        print("  ログイン完了後 Enter を押してください: ", end="", flush=True)
        input()
        page.wait_for_timeout(3000)
    dismiss_library_popups(page)


def get_library_books(page) -> list[dict]:
    """ライブラリから全書籍タイトルとクリック要素を収集する"""
    print("書籍リストを収集中...")

    # 仮想スクロールで全タイルを読み込む
    prev_count = 0
    for _ in range(50):
        page.keyboard.press("End")
        page.wait_for_timeout(800)
        tiles = page.query_selector_all('[role="listitem"]')
        if len(tiles) == prev_count:
            break
        prev_count = len(tiles)

    # タイトル抽出
    books = []
    for tile in tiles:
        try:
            title = ""

            # 1. aria-label を最優先（書籍名が入っていることが多い）
            aria = tile.get_attribute("aria-label") or ""
            if aria.strip():
                title = aria.strip()

            # 2. data-asin がある要素のテキストから取得
            if not title:
                asin_el = tile.query_selector('[data-asin]')
                if asin_el:
                    title = (asin_el.get_attribute("aria-label") or "").strip()

            # 3. img の alt テキスト（書籍カバー画像の alt はタイトルのことが多い）
            if not title:
                img = tile.query_selector('img[alt]')
                if img:
                    title = (img.get_attribute("alt") or "").strip()

            # 4. フォールバック: tile のテキスト全体の1行目
            if not title:
                raw = tile.inner_text().strip()
                title = raw.split("\n")[0].strip()

            if title and title not in [b["title"] for b in books]:
                books.append({"title": title})
        except Exception:
            continue

    print(f"  {len(books)} 冊見つかりました")
    return books


def open_book(page, book: dict) -> dict:
    """書籍タイルをクリックしてリーダーを起動、メタデータを返す"""
    title = book["title"]
    print(f"\n書籍を開いています: {title}")
    dismiss_library_popups(page)

    # ライブラリ画面からタイトルで書籍タイルを再検索してクリック
    # （open_kindle_library後にDOMが再構築されるため毎回検索が必要）
    tile = None
    tiles = page.query_selector_all('[role="listitem"]')
    for t in tiles:
        try:
            aria = t.get_attribute("aria-label") or ""
            img = t.query_selector('img[alt]')
            img_alt = img.get_attribute("alt") if img else ""
            raw = t.inner_text().strip().split("\n")[0]
            if title in (aria, img_alt, raw):
                tile = t
                break
        except Exception:
            continue

    if tile is None:
        raise RuntimeError(f"書籍タイルが見つかりません: {title}")

    # Kindleリーダーは別タブで開くため、新しいページ（タブ）を待機する
    # まれに Kindle for PC が起動してしまうため、その場合はアプリを閉じてリトライする
    context = page.context
    reader_page = None
    for attempt in range(3):
        try:
            with context.expect_page(timeout=15000) as new_page_info:
                dismiss_library_popups(page)
                tile.click()
            reader_page = new_page_info.value
            break
        except Exception:
            if is_kindle_pc_running():
                print("  Kindle for PC が起動したため終了して再試行します...")
                close_kindle_pc()
                page.wait_for_timeout(1200)
                continue
            if attempt < 2:
                page.wait_for_timeout(800)
                continue
            raise RuntimeError("Webリーダーを開けませんでした（Kindle for PCが優先起動している可能性があります）")

    if reader_page is None:
        raise RuntimeError("Webリーダーを開けませんでした")

    print("  新しいタブでリーダーが開きました。読み込み待機中...")
    reader_page.wait_for_load_state("domcontentloaded", timeout=60000)

    # リーダー本体が表示されるまで待機
    print("  リーダー画面の表示を待機中...")
    for selector in ['#book-reader', '.book-reader', '[data-testid="reader-container"]', '.kr-page-turn-area']:
        try:
            reader_page.wait_for_selector(selector, timeout=30000)
            print(f"  リーダー確認: {selector}")
            break
        except Exception:
            continue
    reader_page.wait_for_timeout(3000)  # 描画安定待ち

    dismiss_popups(reader_page)  # ウェルカムポップアップを閉じる
    reader_page.wait_for_timeout(1000)

    return {"title": title, "author": "", "reader_page": reader_page}


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


def dismiss_popups(page) -> None:
    """リーダー上のポップアップ・モーダルを閉じる"""
    for selector in [
        '[data-testid="backdrop-welcome-popover"]',
        '[data-testid="welcome-popover-close"]',
        'button[aria-label="Close"]',
        '.a-popover-close',
    ]:
        try:
            el = page.query_selector(selector)
            if el and el.is_visible():
                el.click(timeout=2000)
                page.wait_for_timeout(500)
                break
        except Exception:
            continue
    # Escキーでも試みる
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
    except Exception:
        pass


def dismiss_library_popups(page) -> None:
    """ライブラリ画面の案内ダイアログ等を閉じる"""
    dismiss_popups(page)

    selectors = [
        '[role="dialog"] button:has-text("OK")',
        'button:has-text("OK")',
        '[role="dialog"] [aria-label="Close"]',
        '[role="dialog"] .a-icon-close',
        '[role="dialog"] .a-popover-close',
    ]
    for selector in selectors:
        try:
            el = page.query_selector(selector)
            if el and el.is_visible():
                el.click(timeout=2000)
                page.wait_for_timeout(400)
                break
        except Exception:
            continue

    # 最後にEscでも試す
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
    except Exception:
        pass


def go_to_beginning(page) -> bool:
    """Go to Page で先頭ページへ移動。成功したら True を返す。"""
    focus_reader(page)
    dismiss_popups(page)

    menu_selectors = [
        'button[aria-label="Menu"]',
        'button[aria-label="Open menu"]',
        'button[aria-label*="menu" i]',
        'button[aria-label*="more" i]',
        '[data-testid="reader-menu-button"]',
        '[data-testid*="menu"]',
        'button.kr-icon-button',
    ]
    goto_selectors = [
        'button:has-text("Go to Page")',
        '[role="menuitem"]:has-text("Go to Page")',
        'button:has-text("Go to page")',
        '[role="menuitem"]:has-text("Go to page")',
        'button:has-text("ページ")',
        '[role="menuitem"]:has-text("ページ")',
    ]
    input_selectors = [
        'input[type="number"]',
        'input[type="text"]',
        'input[placeholder*="page" i]',
        'input[placeholder*="ページ" i]',
        'input[aria-label*="page" i]',
        'input[aria-label*="ページ" i]',
        '[role="dialog"] input',
        '[role="menu"] input',
    ]

    def click_first_visible(selectors: list[str]) -> bool:
        for sel in selectors:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    el.click(timeout=2500)
                    page.wait_for_timeout(600)
                    return True
            except Exception:
                continue
        return False

    def type_page_one() -> bool:
        for sel in input_selectors:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    el.click(timeout=1500)
                    page.keyboard.press("Control+A")
                    page.keyboard.type("1")
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(1400)
                    return True
            except Exception:
                continue
        return False

    # メニュー経由
    if click_first_visible(menu_selectors) and click_first_visible(goto_selectors):
        if type_page_one():
            return True

    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
    except Exception:
        pass
    return False


def turn_page(page, key: str = "ArrowRight") -> None:
    """右矢印キーでページをめくり、アニメーション完了を待機"""
    dismiss_popups(page)
    page.keyboard.press(key)
    page.wait_for_timeout(500)


def focus_reader(page) -> None:
    """キー操作が効くようにリーダー領域へフォーカスを与える"""
    reader_el = (
        page.query_selector('#book-reader') or
        page.query_selector('.book-reader') or
        page.query_selector('[data-testid="reader-container"]') or
        page.query_selector('.kr-page-turn-area')
    )
    if reader_el:
        try:
            box = reader_el.bounding_box()
            if box:
                page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                page.wait_for_timeout(200)
        except Exception:
            pass


def extract_location_progress(page) -> tuple[int, int] | None:
    """画面テキストから (current, total) の位置情報を抽出する。"""
    try:
        text = page.evaluate("() => document.body ? document.body.innerText : ''")
    except Exception:
        return None

    patterns = [
        r"(?:Location|位置)\s*(?:No\.?)?\s*(\d+)\s*/\s*(\d+)",
        r"(?:Loc\.?)\s*(\d+)\s*/\s*(\d+)",
        r"(\d+)\s*/\s*(\d+)",
    ]
    candidates: list[tuple[int, int]] = []
    for pat in patterns:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            try:
                cur = int(m.group(1))
                total = int(m.group(2))
            except ValueError:
                continue
            if 0 < cur <= total and total >= 10:
                candidates.append((cur, total))

    if not candidates:
        return None
    return max(candidates, key=lambda x: x[1])


def seek_edge(page, tmpdir: Path, title: str, key: str, max_steps: int = 4000, stable_needed: int = 15) -> int:
    """指定キー方向の端まで移動し、実際に移動した回数を返す"""
    safe = sanitize_filename(title)
    prev_path = tmpdir / f"{safe}_seek_prev.png"
    curr_path = tmpdir / f"{safe}_seek_curr.png"
    moved = 0
    stable = 0

    screenshot_current_page(page, prev_path)
    for _ in range(max_steps):
        turn_page(page, key)
        screenshot_current_page(page, curr_path)

        if images_are_identical(prev_path, curr_path):
            stable += 1
            curr_path.unlink(missing_ok=True)
            if stable >= stable_needed:
                break
        else:
            moved += 1
            stable = 0
            prev_path.unlink(missing_ok=True)
            curr_path.replace(prev_path)

    prev_path.unlink(missing_ok=True)
    curr_path.unlink(missing_ok=True)
    return moved


def extract_location_no(page) -> int | None:
    """画面内テキストから位置番号を抽出する（取得できない場合はNone）"""
    progress = extract_location_progress(page)
    if progress:
        return progress[0]
    return None


def probe_page_turn(page, tmpdir: Path, title: str, key: str) -> dict:
    """1回だけページ送りを試し、差分情報を返して元ページへ戻す。"""
    safe = sanitize_filename(title)
    base = tmpdir / f"{safe}_probe_base_{key}.png"
    after = tmpdir / f"{safe}_probe_after_{key}.png"
    before_loc = extract_location_no(page)

    focus_reader(page)
    screenshot_current_page(page, base)
    turn_page(page, key)
    screenshot_current_page(page, after)

    changed = not images_are_identical(base, after)
    after_loc = extract_location_no(page)

    if changed:
        opposite = OPPOSITE_PAGE_KEY.get(key)
        if opposite:
            turn_page(page, opposite)
            page.wait_for_timeout(300)

    base.unlink(missing_ok=True)
    after.unlink(missing_ok=True)

    delta = None
    if before_loc is not None and after_loc is not None:
        delta = after_loc - before_loc

    return {"changed": changed, "delta": delta}


def detect_forward_page_key(page, tmpdir: Path, title: str, preferred: str = "ArrowRight") -> str:
    """ページが進むキーを推定する。"""
    opposite = OPPOSITE_PAGE_KEY.get(preferred, "ArrowLeft")
    keys = [preferred, opposite]
    probes = {k: probe_page_turn(page, tmpdir, title, k) for k in keys}

    # 位置番号が増えるキーを優先
    for key in keys:
        delta = probes[key]["delta"]
        if isinstance(delta, int) and delta > 0:
            return key

    # 位置情報が取れない場合は「画面が変わるキー」を優先
    movable = [k for k in keys if probes[k]["changed"]]
    if len(movable) == 1:
        return movable[0]

    return preferred


def ensure_first_page_and_direction(page, tmpdir: Path, title: str) -> str:
    """先頭ページ移動を試み、最終的なページ送りキーを返す。"""
    goto_succeeded = False
    for attempt in range(3):
        moved = go_to_beginning(page)
        if not moved:
            page.wait_for_timeout(600)
            continue
        goto_succeeded = True

        progress = extract_location_progress(page)
        if progress:
            cur, total = progress
            # 先頭移動失敗で末尾へ飛んだケースを弾く
            if total > 0 and (cur / total) > 0.7 and attempt < 2:
                continue

        break

    # Go to Page の成否にかかわらず、進行方向を判定して先頭側へ強制シークする
    forward = detect_forward_page_key(page, tmpdir, title, preferred="ArrowRight")
    backward = OPPOSITE_PAGE_KEY.get(forward, "ArrowLeft")
    moved_count = seek_edge(
        page,
        tmpdir,
        title,
        backward,
        max_steps=12000,
        stable_needed=10,
    )
    if goto_succeeded:
        print(f"  先頭固定のため端シーク実施: key={backward}, moved={moved_count}")
    else:
        print(f"  Go to Page失敗のため端シーク実施: key={backward}, moved={moved_count}")
    forward = detect_forward_page_key(page, tmpdir, title, preferred=forward)
    return forward


def close_book(book_meta: dict) -> None:
    """リーダータブを閉じてライブラリに戻る"""
    reader_page = book_meta.get("reader_page")
    if reader_page:
        try:
            reader_page.close()
        except Exception:
            pass


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
def process_book(page, book_meta: dict, client, log: dict, vault: Path, tmpdir: Path, resume: bool = False) -> None:
    title = book_meta["title"]
    reader_page = book_meta.get("reader_page", page)
    print(f"  OCR 処理開始: {title}")

    in_progress_info = log.get("in_progress", {}).get(title, {})
    start_page = in_progress_info.get("last_page", 0)
    partial_path = get_partial_path(vault, title)
    pages_text = []

    # 既定動作は先頭から再処理。--resume 指定時のみ中断地点から再開する
    if resume and start_page > 0:
        pages_text = read_partial(vault, title)
    else:
        start_page = 0
        if title in log.get("in_progress", {}):
            log["in_progress"].pop(title, None)
            save_log(vault, log)
        if partial_path.exists():
            partial_path.unlink()

    focus_reader(reader_page)
    next_page_key = in_progress_info.get("next_page_key", "ArrowRight")

    # 新規/再開を問わず先頭へ固定し、必要なら start_page まで進める。
    if start_page > 0:
        print(f"  前回の中断から再開: 先頭へ固定後、ページ {start_page} まで送り直します")
        next_page_key = ensure_first_page_and_direction(reader_page, tmpdir, title)
        print(f"  先頭固定と方向判定: next_page_key={next_page_key}")
        for _ in range(start_page):
            turn_page(reader_page, next_page_key)
    else:
        next_page_key = ensure_first_page_and_direction(reader_page, tmpdir, title)
        print(f"  先頭ページ移動と方向判定: next_page_key={next_page_key}")

    # 念のため現在位置で再判定し、逆走を防ぐ
    next_page_key = detect_forward_page_key(reader_page, tmpdir, title, preferred=next_page_key)
    print(f"  使用するページ送りキー: {next_page_key}")

    consecutive_dupes = 0
    prev_screenshot: Path | None = None
    prev_location_no: int | None = None
    n = start_page
    stop_reason = "unknown"

    while True:
        current_screenshot = tmpdir / f"{sanitize_filename(title)}_page_{n:04d}.png"
        screenshot_current_page(reader_page, current_screenshot)
        current_location_no = extract_location_no(reader_page)

        # 逆走を検知したら次回送り方向を切り替える
        if (
            prev_location_no is not None
            and current_location_no is not None
            and current_location_no < prev_location_no
        ):
            old_key = next_page_key
            next_page_key = OPPOSITE_PAGE_KEY.get(next_page_key, next_page_key)
            print(
                f"  WARNING: 逆走検知 (loc {prev_location_no} -> {current_location_no}) "
                f"key切替 {old_key} -> {next_page_key}"
            )

        # 重複ページ検知
        if prev_screenshot and prev_screenshot.exists():
            if images_are_identical(prev_screenshot, current_screenshot):
                consecutive_dupes += 1
                print(f"  ページ {n}: 同一画像 ({consecutive_dupes}/{DUPLICATE_THRESHOLD})")
                if consecutive_dupes >= DUPLICATE_THRESHOLD:
                    print("  読了を検出しました。")
                    current_screenshot.unlink(missing_ok=True)
                    stop_reason = "duplicate_end"
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
            pages_text.append(f"<!-- OCRエラー: ページ {n} -->")

        # 途中経過保存
        if "in_progress" not in log:
            log["in_progress"] = {}
        log["in_progress"][title] = {
            "last_page": n + 1,
            "title": title,
            "author": book_meta.get("author", ""),
            "next_page_key": next_page_key,
        }
        save_log(vault, log)
        write_partial(vault, title, pages_text)

        # 比較が終わった前回画像はここで削除し、今回画像を次回比較用として残す
        old_prev = prev_screenshot
        prev_screenshot = current_screenshot
        if old_prev and old_prev.exists():
            old_prev.unlink(missing_ok=True)

        turn_page(reader_page, next_page_key)
        time.sleep(RATE_LIMIT_SLEEP)
        prev_location_no = current_location_no
        n += 1

    if prev_screenshot and prev_screenshot.exists():
        prev_screenshot.unlink(missing_ok=True)

    # 読み込み不全の早期終了を完了扱いしない
    if stop_reason == "duplicate_end" and n < MIN_PAGES_FOR_COMPLETE:
        print(f"  WARNING: {n}ページで終了。読込失敗の可能性があるため処理済みにしません。")
        print("  ポップアップやリーダー未表示の影響がないか確認して再実行してください。")
        return

    write_ocr_output(vault, book_meta, pages_text)

    if title not in log.get("processed", []):
        log.setdefault("processed", []).append(title)
    log.get("in_progress", {}).pop(title, None)
    save_log(vault, log)

    print(f"  完了: {n} ページ処理")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Kindle Cloud Reader OCR Pipeline")
    parser.add_argument("--one", action="store_true", help="1冊だけ処理して終了する")
    parser.add_argument("--list", action="store_true", help="ライブラリの書籍一覧を表示してスキップリストを更新する")
    parser.add_argument("--resume", action="store_true", help="中断した本を続きから再開する（既定は先頭から再処理）")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key and not args.list:
        print("ERROR: 環境変数 GEMINI_API_KEY が設定されていません。")
        print("  Google AI Studio (https://aistudio.google.com) でAPIキーを取得し、")
        print("  環境変数 GEMINI_API_KEY に設定してください。")
        sys.exit(1)

    vault = get_vault_path()
    print(f"Vault: {vault}")

    ocr_dir = get_ocr_dir(vault)
    print(f"出力先: {ocr_dir}")

    log = load_log(vault)
    client = build_ocr_client(api_key) if not args.list else None

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

                if args.list:
                    # スキップリストに未登録の本を追記して終了
                    skip_path = vault / SKIP_LIST_PATH
                    existing = skip_path.read_text(encoding="utf-8") if skip_path.exists() else ""
                    existing_titles = [l.strip().lstrip("- [x]- [ ]").strip() for l in existing.splitlines() if l.strip().startswith("- [")]
                    new_lines = []
                    for b in books:
                        if b["title"] not in existing_titles:
                            new_lines.append(f"- [ ] {b['title']}")
                    if new_lines:
                        skip_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(skip_path, "a", encoding="utf-8") as f:
                            f.write("\n" + "\n".join(new_lines) + "\n")
                        print(f"\n{len(new_lines)} 冊をスキップリストに追加しました: {skip_path}")
                    else:
                        print("\nスキップリストはすでに最新です。")
                    print("\n--- ライブラリ全書籍 ---")
                    for b in books:
                        print(f"  {b['title']}")
                    return

                processed = log.get("processed", [])
                skipped = load_skip_list(vault)
                unprocessed = [b for b in books if b["title"] not in processed and b["title"] not in skipped]
                if args.one:
                    unprocessed = unprocessed[:1]
                print(f"\n未処理書籍: {len(unprocessed)} / {len(books)} 冊")

                for book in unprocessed:
                    book_meta = None
                    try:
                        open_kindle_library(page)
                        book_meta = open_book(page, book)
                        process_book(page, book_meta, client, log, vault, tmpdir, resume=args.resume)
                    except KeyboardInterrupt:
                        print("\n中断しました。次回は --resume を付けると続きから再開できます。")
                        raise
                    except Exception as e:
                        print(f"  ERROR 書籍処理失敗 ({book['title']}): {e}")
                    finally:
                        if book_meta:
                            close_book(book_meta)

                print("\n全書籍の処理が完了しました。")

            finally:
                try:
                    if browser.is_connected():
                        browser.close()
                except Exception:
                    pass

    except KeyboardInterrupt:
        pass
    finally:
        # 一時フォルダを削除
        shutil.rmtree(tmpdir, ignore_errors=True)
        print(f"一時フォルダを削除しました: {tmpdir}")


if __name__ == "__main__":
    main()
