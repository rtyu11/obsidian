"""
sync_keep_setup.py - Google Keep 初回セットアップ

初回1回だけ実行してマスタートークンを取得・保存する。
以降は sync_keep.py がこのトークンを使って認証する。

実行方法:
    pip install gkeepapi
    python ".agents/scripts/sync_keep_setup.py"

事前準備（2段階認証が有効な場合）:
    https://myaccount.google.com/apppasswords でアプリパスワードを作成する
"""

import gkeepapi
import json
import os
import sys


TOKEN_PATH = os.path.join(os.path.expanduser("~"), ".keep_token")


def setup():
    print("=== Google Keep セットアップ ===\n")

    if os.path.exists(TOKEN_PATH):
        answer = input(f"既存のトークンが見つかりました ({TOKEN_PATH})。上書きしますか？ [y/N]: ")
        if answer.lower() != "y":
            print("キャンセルしました。")
            return

    email = input("Googleメールアドレス: ").strip()
    if not email:
        print("エラー: メールアドレスが入力されていません。")
        sys.exit(1)

    password = input("アプリパスワード（または通常パスワード）: ").strip()
    if not password:
        print("エラー: パスワードが入力されていません。")
        sys.exit(1)

    print("\nGoogle Keep に接続中...")

    try:
        keep = gkeepapi.Keep()
        keep.authenticate(email, password)
        token = keep.getMasterToken()
    except Exception as e:
        print(f"\nエラー: ログインに失敗しました。\n{e}")
        print("\nヒント:")
        print("  - 2段階認証が有効な場合はアプリパスワードを使用してください")
        print("  - アプリパスワードの取得: https://myaccount.google.com/apppasswords")
        sys.exit(1)

    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        json.dump({"email": email, "token": token}, f)

    print(f"\nセットアップ完了！トークンを保存しました: {TOKEN_PATH}")
    print("次は sync_keep.py を実行してメモを同期できます。")


if __name__ == "__main__":
    setup()
