"""
kindle_debug.py
KindleライブラリのDOM構造を調べて、正しいセレクタを特定するデバッグ用スクリプト。
"""
import os
import sys
from pathlib import Path

KINDLE_URL = "https://read.amazon.co.jp"


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright が必要です: pip install playwright && playwright install chromium")
        sys.exit(1)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1280, "height": 800}, locale="ja-JP")
        page = context.new_page()

        print(f"Kindleを開いています: {KINDLE_URL}")
        page.goto(KINDLE_URL, timeout=60000)

        print("\nページが読み込まれるまで待機中...")
        print("ログインが必要な場合は手動でログインしてください。")
        print("ライブラリが表示されたら Enter を押してください: ", end="", flush=True)
        input()
        page.wait_for_timeout(2000)

        # 現在のURLとページタイトルを出力
        print(f"\n現在のURL: {page.url}")
        print(f"ページタイトル: {page.title()}")

        # ページのbody直下の主要要素を調べる
        print("\n--- body直下の主要要素 ---")
        result = page.evaluate("""() => {
            const elements = document.querySelectorAll('body > *');
            return Array.from(elements).slice(0, 20).map(el => ({
                tag: el.tagName,
                id: el.id,
                class: el.className.toString().slice(0, 100),
                children: el.children.length
            }));
        }""")
        for el in result:
            print(f"  <{el['tag']} id='{el['id']}' class='{el['class']}'> ({el['children']} children)")

        # 書籍っぽい要素を探す
        print("\n--- 書籍タイル候補を探す ---")
        candidates = page.evaluate("""() => {
            // よく使われる書籍コンテナのセレクタを試す
            const selectors = [
                '[data-asin]',
                '[data-book-id]',
                '.book-container',
                '.book-item',
                '.content-tile',
                '.library-item',
                '[class*="book"]',
                '[class*="Book"]',
                '[class*="tile"]',
                '[class*="Tile"]',
                '[class*="item"]',
                '[class*="Item"]',
                'li[role]',
                '[role="listitem"]',
            ];
            const results = {};
            for (const sel of selectors) {
                const els = document.querySelectorAll(sel);
                if (els.length > 0) {
                    results[sel] = {
                        count: els.length,
                        sample_class: els[0].className.toString().slice(0, 80),
                        sample_text: els[0].textContent.trim().slice(0, 60)
                    };
                }
            }
            return results;
        }""")
        for sel, info in candidates.items():
            print(f"  '{sel}': {info['count']}件 | class='{info['sample_class']}' | text='{info['sample_text']}'")

        if not candidates:
            print("  書籍要素が見つかりませんでした。")

        # 最も多く見つかったものの詳細
        print("\n--- data-asin 要素の詳細 ---")
        details = page.evaluate("""() => {
            const els = document.querySelectorAll('[data-asin]');
            return Array.from(els).slice(0, 5).map(el => ({
                asin: el.getAttribute('data-asin'),
                class: el.className.toString().slice(0, 100),
                aria_label: el.getAttribute('aria-label') || '',
                text: el.textContent.trim().slice(0, 100),
                tag: el.tagName
            }));
        }""")
        for d in details:
            print(f"  ASIN={d['asin']} tag={d['tag']}")
            print(f"    class: {d['class']}")
            print(f"    aria-label: {d['aria_label']}")
            print(f"    text: {d['text']}")

        # タイトルっぽいテキストを持つ要素
        print("\n--- テキストを持つ書籍タイトル要素の候補 ---")
        title_candidates = page.evaluate("""() => {
            const selectors = [
                '[class*="title"]',
                '[class*="Title"]',
                '[data-testid*="title"]',
                'h1, h2, h3',
            ];
            const results = {};
            for (const sel of selectors) {
                const els = document.querySelectorAll(sel);
                if (els.length > 0 && els.length < 100) {
                    results[sel] = Array.from(els).slice(0, 3).map(el => ({
                        text: el.textContent.trim().slice(0, 60),
                        class: el.className.toString().slice(0, 60)
                    }));
                }
            }
            return results;
        }""")
        for sel, items in title_candidates.items():
            print(f"  '{sel}':")
            for item in items:
                print(f"    '{item['text']}' (class: {item['class']})")

        print("\n--- 調査完了 ---")
        print("ブラウザを閉じるには Enter を押してください: ", end="", flush=True)
        input()
        browser.close()


if __name__ == "__main__":
    main()
