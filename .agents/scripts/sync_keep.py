"""
sync_keep.py - Google Keep → Obsidian Daily/Inbox 同期スクリプト

ob-ideas / ob-tasks / ob-memo ラベルのメモを Daily/Inbox/ に書き出す。

実行方法:
    python ".agents/scripts/sync_keep.py"

依存:
    pip install gkeepapi

事前条件:
    sync_keep_setup.py を実行してトークンを取得済みであること
"""

import gkeepapi
import json
import os
import sys
from datetime import datetime


# ---- 設定 ----
VAULT_PATH = r"C:\Users\111r9\OneDrive\ドキュメント\Obsidian Vault\obsidian"
TOKEN_PATH = os.path.join(os.path.expanduser("~"), ".keep_token")
LABEL_MAP = {
    "ob-ideas": "ideas",
    "ob-tasks": "tasks",
    "ob-memo":  "memo",
}
# ---- 設定ここまで ----


def load_credentials():
    if not os.path.exists(TOKEN_PATH):
        print(f"エラー: トークンファイルが見つかりません ({TOKEN_PATH})")
        print("先に sync_keep_setup.py を実行してセットアップを完了してください。")
        sys.exit(1)
    with open(TOKEN_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def sync():
    creds = load_credentials()

    print("Google Keep に接続中...")
    try:
        keep = gkeepapi.Keep()
        keep.resume(creds["email"], creds["token"])
    except Exception as e:
        print(f"エラー: 接続に失敗しました。\n{e}")
        print("トークンが期限切れの可能性があります。sync_keep_setup.py を再実行してください。")
        sys.exit(1)

    today = datetime.now().strftime("%Y-%m-%d")
    inbox_dir = os.path.join(VAULT_PATH, "Daily", "Inbox")
    os.makedirs(inbox_dir, exist_ok=True)

    collected = {suffix: [] for suffix in LABEL_MAP.values()}

    for note in keep.all():
        if note.trashed or note.archived:
            continue
        for label_name, suffix in LABEL_MAP.items():
            label = keep.findLabel(label_name)
            if label and note.labels.get(label):
                parts = []
                if note.title:
                    parts.append(note.title)
                if note.text:
                    parts.append(note.text)
                text = "\n".join(parts).strip()
                if text:
                    collected[suffix].append(text)
                    # Archive the note after collecting its content
                    note.archived = True

    written = []
    for suffix, notes in collected.items():
        if not notes:
            continue
        filepath = os.path.join(inbox_dir, f"{today}-{suffix}.md")
        mode = "a" if os.path.exists(filepath) else "w"
        with open(filepath, mode, encoding="utf-8") as f:
            if mode == "w":
                f.write(f"# {today} {suffix}\n\n")
            for text in notes:
                # 複数行のメモは最初の行を箇条書き、残りはインデント
                lines = text.splitlines()
                f.write(f"- {lines[0]}\n")
                for line in lines[1:]:
                    if line.strip():
                        f.write(f"  {line}\n")
        written.append(f"{today}-{suffix}.md ({len(notes)}件)")

    if written:
        print(f"同期完了: {', '.join(written)}")
        # Sync the archive status back to Google Keep
        try:
            keep.sync()
            print("Keep上のメモをアーカイブしました。")
        except Exception as e:
            print(f"警告: メモのアーカイブ(同期)に失敗しました: {e}")
    else:
        print("同期するメモはありませんでした（ob-* ラベルのメモが0件）")


if __name__ == "__main__":
    sync()
