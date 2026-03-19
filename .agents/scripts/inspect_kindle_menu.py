"""
inspect_kindle_menu.py
Kindle Cloud Reader の⋮ボタン周辺のDOM構造を調査するスクリプト。
headful=True で起動し、既存のブラウザセッションは使わず新規起動する。
Kindle Cloud Reader は ASINを直接URLに渡すと別タブでリーダーが開くことがある。
"""

import sys
import time

ASIN = "B007TT5LH2"
URL = f"https://read.amazon.co.jp/?asin={ASIN}"


def wait_for_reader(page, timeout_ms=60000):
    """リーダー確認セレクタ一覧で待機。見つかったセレクタを返す"""
    reader_selectors = [
        '#book-reader',
        '.book-reader',
        '[data-testid="reader-container"]',
        '.kr-page-turn-area',
        '#KindleReaderIFrame',
        'iframe',
    ]
    for sel in reader_selectors:
        try:
            page.wait_for_selector(sel, timeout=timeout_ms)
            return sel
        except Exception:
            continue
    return None


def dump_buttons(page, label=""):
    if label:
        print(f"\n--- ボタン一覧: {label} ---")
    buttons = page.query_selector_all("button")
    for btn in buttons:
        try:
            aria_label = btn.get_attribute("aria-label") or ""
            aria_expanded = btn.get_attribute("aria-expanded") or ""
            data_testid = btn.get_attribute("data-testid") or ""
            class_name = (btn.get_attribute("class") or "")[:80]
            text = btn.inner_text().strip()[:50]
            visible = btn.is_visible()
            if visible or aria_label:
                print(f"  aria-label={aria_label!r:45s} text={text!r:25s} "
                      f"expanded={aria_expanded!r} testid={data_testid!r} visible={visible}")
        except Exception:
            pass


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: playwright がインストールされていません。")
        print("  pip install playwright && playwright install chromium")
        sys.exit(1)

    with sync_playwright() as pw:
        print("ブラウザを起動中（headful）...")
        browser = pw.chromium.launch(
            headless=False,
            args=["--start-maximized"],
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            locale="ja-JP",
        )
        page = context.new_page()

        print(f"URL を開いています: {URL}")

        # Kindle Cloud Readerはリーダーを別タブで開くことがあるため
        # expect_page で新規タブを捕捉する
        reader_page = None
        try:
            with context.expect_page(timeout=15000) as new_page_info:
                page.goto(URL, timeout=60000)
            reader_page = new_page_info.value
            print("  新しいタブが開きました（リーダータブ）")
        except Exception:
            # 別タブが開かなかった場合は元のページで処理
            reader_page = page
            print("  同じタブでリーダーが表示されます")

        # ログイン確認
        print("リーダー画面を待機中（最大60秒）...")
        print("  ※ ログイン画面が表示された場合は手動でログインしてください。")
        print("  ※ リーダーが表示されたら自動で処理が続きます。")

        # まずログイン画面チェック（サインインフォームがあれば停止）
        try:
            reader_page.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception:
            pass

        current_url = reader_page.url
        print(f"  現在のURL: {current_url}")

        # ログイン画面判定
        if "signin" in current_url or "ap/signin" in current_url or "login" in current_url.lower():
            print("\nログイン画面が表示されています。")
            print("手動でログインしてください。ログイン後 Enter を押してください: ", end="", flush=True)
            input()

        # リーダー待機
        found_sel = wait_for_reader(reader_page, timeout_ms=60000)
        if found_sel is None:
            print("リーダーが表示されませんでした。")
            print("現在のURL:", reader_page.url)
            # それでも続けて調査する
        else:
            print(f"リーダー確認: {found_sel}")

        reader_page.wait_for_timeout(4000)

        # =============================================================
        # 【1】全ボタン一覧
        # =============================================================
        print("\n" + "="*60)
        print("【1】ページ上のすべての可視button要素")
        print("="*60)
        dump_buttons(reader_page, "リーダー読み込み後")

        # =============================================================
        # 【2】⋮ボタン候補を特定してクリック
        # =============================================================
        print("\n" + "="*60)
        print("【2】⋮（More/Menu）ボタンを探してクリック")
        print("="*60)

        menu_candidates = [
            'button[aria-label="Menu"]',
            'button[aria-label="Open menu"]',
            'button[aria-label="More options"]',
            'button[aria-label="More"]',
            'button[aria-label*="menu" i]',
            'button[aria-label*="more" i]',
            'button[aria-label*="option" i]',
            'button[aria-label*="オプション"]',
            'button[aria-label*="メニュー"]',
            '[data-testid="reader-menu-button"]',
            '[data-testid*="menu"]',
            'button.kr-icon-button',
            # ⋮ (vertical ellipsis) のUnicode
            'button:has-text("⋮")',
            'button:has-text("...")',
            'button:has-text("…")',
        ]

        clicked_sel = None
        clicked_aria = None
        for sel in menu_candidates:
            try:
                el = reader_page.query_selector(sel)
                if el and el.is_visible():
                    aria = el.get_attribute("aria-label") or ""
                    text = el.inner_text().strip()
                    class_name = el.get_attribute("class") or ""
                    data_testid = el.get_attribute("data-testid") or ""
                    print(f"  候補を発見: {sel}")
                    print(f"    aria-label   = {aria!r}")
                    print(f"    inner text   = {text!r}")
                    print(f"    class        = {class_name[:80]!r}")
                    print(f"    data-testid  = {data_testid!r}")
                    el.click(timeout=3000)
                    reader_page.wait_for_timeout(1200)
                    clicked_sel = sel
                    clicked_aria = aria
                    print(f"  -> クリックしました")
                    break
            except Exception as e:
                print(f"  {sel}: スキップ ({e})")

        if not clicked_sel:
            print("\n  ⋮ボタンが見つかりませんでした。")
            print("  ページ上の全要素のaria-label:")
            all_els = reader_page.query_selector_all("[aria-label]")
            for el in all_els:
                try:
                    aria = el.get_attribute("aria-label") or ""
                    tag = reader_page.evaluate("el => el.tagName", el)
                    visible = el.is_visible()
                    print(f"    {tag} aria-label={aria!r} visible={visible}")
                except Exception:
                    pass
            time.sleep(5)
            browser.close()
            return

        # =============================================================
        # 【3】メニュー内の全要素
        # =============================================================
        print("\n" + "="*60)
        print("【3】メニュー内の全要素")
        print("="*60)

        reader_page.wait_for_timeout(800)

        # メニューパネルの候補
        menu_panel_selectors = [
            '[role="menu"]',
            '[role="dialog"]',
            '[role="listbox"]',
            '.kr-menu',
            '[data-testid*="menu"]',
            '[class*="menu"]',
            '[class*="Menu"]',
            '[class*="dropdown"]',
            '[class*="Dropdown"]',
            '[class*="popover"]',
            '[class*="Popover"]',
        ]

        menu_panel = None
        for sel in menu_panel_selectors:
            try:
                el = reader_page.query_selector(sel)
                if el and el.is_visible():
                    menu_panel = el
                    print(f"  メニューパネル発見: {sel}")
                    break
            except Exception:
                continue

        if menu_panel:
            items = menu_panel.query_selector_all('button, [role="menuitem"], [role="option"], a, li')
            print(f"  メニュー内要素数: {len(items)}")
            for i, item in enumerate(items):
                try:
                    aria = item.get_attribute("aria-label") or ""
                    role = item.get_attribute("role") or ""
                    data_testid = item.get_attribute("data-testid") or ""
                    text = item.inner_text().strip()[:80]
                    tag = reader_page.evaluate("el => el.tagName", item)
                    class_name = (item.get_attribute("class") or "")[:80]
                    visible = item.is_visible()
                    print(f"  [{i}] tag={tag} role={role!r} aria={aria!r} "
                          f"testid={data_testid!r} text={text!r} visible={visible}")
                    print(f"       class={class_name!r}")
                except Exception as e:
                    print(f"  [{i}] エラー: {e}")
        else:
            print("  メニューパネル（role=menu等）が見つかりません。")
            print("  role=menuitem / option の要素を探します:")
            all_items = reader_page.query_selector_all('[role="menuitem"], [role="option"], [role="listitem"]')
            print(f"  件数: {len(all_items)}")
            for i, item in enumerate(all_items):
                try:
                    text = item.inner_text().strip()[:80]
                    aria = item.get_attribute("aria-label") or ""
                    visible = item.is_visible()
                    tag = reader_page.evaluate("el => el.tagName", item)
                    print(f"  [{i}] tag={tag} text={text!r} aria={aria!r} visible={visible}")
                except Exception as e:
                    print(f"  [{i}] エラー: {e}")

        # メニュー全体のテキストをdump
        print("\n  メニュー後のページ可視テキスト（上位50行）:")
        try:
            body_text = reader_page.evaluate("() => document.body.innerText")
            lines = [l.strip() for l in body_text.split('\n') if l.strip()]
            for line in lines[:50]:
                print(f"    {line!r}")
        except Exception as e:
            print(f"  テキスト取得エラー: {e}")

        # =============================================================
        # 【4】「Go to Page」を探してクリック
        # =============================================================
        print("\n" + "="*60)
        print("【4】「Go to Page」ボタンを探してクリック")
        print("="*60)

        goto_candidates = [
            'button:has-text("Go to Page")',
            '[role="menuitem"]:has-text("Go to Page")',
            'button:has-text("Go to page")',
            '[role="menuitem"]:has-text("Go to page")',
            'button:has-text("ページへ移動")',
            '[role="menuitem"]:has-text("ページへ移動")',
            '[role="listitem"]:has-text("Go to Page")',
            'li:has-text("Go to Page")',
        ]

        goto_clicked_sel = None
        for sel in goto_candidates:
            try:
                el = reader_page.query_selector(sel)
                if el and el.is_visible():
                    aria = el.get_attribute("aria-label") or ""
                    role = el.get_attribute("role") or ""
                    tag = reader_page.evaluate("el => el.tagName", el)
                    text = el.inner_text().strip()
                    class_name = (el.get_attribute("class") or "")[:80]
                    data_testid = el.get_attribute("data-testid") or ""
                    print(f"  「Go to Page」発見: {sel}")
                    print(f"    tag          = {tag!r}")
                    print(f"    role         = {role!r}")
                    print(f"    aria-label   = {aria!r}")
                    print(f"    data-testid  = {data_testid!r}")
                    print(f"    inner text   = {text!r}")
                    print(f"    class        = {class_name!r}")
                    el.click(timeout=3000)
                    reader_page.wait_for_timeout(1200)
                    goto_clicked_sel = sel
                    print(f"  -> クリックしました")
                    break
            except Exception as e:
                print(f"  {sel}: スキップ ({e})")

        if not goto_clicked_sel:
            print("  「Go to Page」が見つかりませんでした。")
            print("  現在の可視要素（全テキスト付き）:")
            try:
                all_vis = reader_page.query_selector_all("button, [role='menuitem'], li, a")
                for el in all_vis:
                    try:
                        if el.is_visible():
                            text = el.inner_text().strip()[:60]
                            aria = el.get_attribute("aria-label") or ""
                            tag = reader_page.evaluate("el => el.tagName", el)
                            if text or aria:
                                print(f"    {tag} text={text!r} aria={aria!r}")
                    except Exception:
                        pass
            except Exception as e:
                print(f"  エラー: {e}")

        # =============================================================
        # 【5】入力フィールドの構造
        # =============================================================
        print("\n" + "="*60)
        print("【5】入力フィールドのHTML構造")
        print("="*60)

        reader_page.wait_for_timeout(800)

        found_input = False
        input_selectors = [
            'input[type="number"]',
            'input[type="text"]',
            'input[placeholder*="page" i]',
            'input[placeholder*="ページ" i]',
            'input[aria-label*="page" i]',
            'input[aria-label*="ページ" i]',
            'input',
        ]

        for sel in input_selectors:
            try:
                elements = reader_page.query_selector_all(sel)
                for el in elements:
                    if el.is_visible():
                        found_input = True
                        aria = el.get_attribute("aria-label") or ""
                        placeholder = el.get_attribute("placeholder") or ""
                        type_ = el.get_attribute("type") or ""
                        name = el.get_attribute("name") or ""
                        data_testid = el.get_attribute("data-testid") or ""
                        class_name = (el.get_attribute("class") or "")[:80]
                        # 親要素のHTML
                        parent_html = reader_page.evaluate(
                            "el => el.parentElement ? el.parentElement.outerHTML.substring(0, 800) : ''",
                            el
                        )
                        # 自身のouterHTML
                        self_html = reader_page.evaluate(
                            "el => el.outerHTML.substring(0, 400)",
                            el
                        )
                        print(f"  input発見 ({sel}):")
                        print(f"    type         = {type_!r}")
                        print(f"    aria-label   = {aria!r}")
                        print(f"    placeholder  = {placeholder!r}")
                        print(f"    name         = {name!r}")
                        print(f"    data-testid  = {data_testid!r}")
                        print(f"    class        = {class_name!r}")
                        print(f"    outerHTML    = {self_html!r}")
                        print(f"    親HTML       = {parent_html!r}")
                        print()
            except Exception as e:
                print(f"  {sel}: {e}")

        if not found_input:
            print("  可視のinput要素が見つかりませんでした。")

        # =============================================================
        # 【6】Go to Page周辺のDOM構造をJS評価でdump
        # =============================================================
        print("\n" + "="*60)
        print("【6】「Go to Page」関連DOM（JS評価）")
        print("="*60)
        try:
            relevant = reader_page.evaluate("""() => {
                const results = [];
                const walk = (el, depth) => {
                    if (depth > 15) return;
                    const text = (el.textContent || '').trim();
                    const aria = el.getAttribute ? (el.getAttribute('aria-label') || '') : '';
                    if (
                        text.toLowerCase().includes('go to page') ||
                        text.toLowerCase().includes('ページへ移動') ||
                        aria.toLowerCase().includes('go to page')
                    ) {
                        results.push({
                            html: el.outerHTML.substring(0, 1200),
                            tag: el.tagName,
                            depth: depth,
                            role: el.getAttribute ? (el.getAttribute('role') || '') : '',
                        });
                    }
                    for (const child of el.children) {
                        walk(child, depth + 1);
                    }
                };
                walk(document.body, 0);
                return results.slice(0, 10);
            }""")
            if relevant:
                for item in relevant:
                    print(f"\n  tag={item['tag']} depth={item['depth']} role={item['role']!r}")
                    print(f"  HTML:\n{item['html'][:800]}")
            else:
                print("  「Go to Page」関連要素が見つかりませんでした。")
        except Exception as e:
            print(f"  JS評価エラー: {e}")

        print("\n" + "="*60)
        print("調査完了。ブラウザを15秒後に閉じます...")
        print("="*60)
        time.sleep(15)
        try:
            browser.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
