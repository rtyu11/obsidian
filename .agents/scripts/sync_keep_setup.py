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
        import gpsoauth
        import uuid
        import platform
        import socket
        
        # gpsoauthを使用してマスタートークンを取得
        # 有効な形式の Android device ID を生成 (ランダムな16桁の16進数)
        import random
        android_id = "".join(random.choice("0123456789abcdef") for _ in range(16))
            
        print(f"Android ID '{android_id}' で認証を試みます...")
        
        master_response = gpsoauth.perform_master_login(email, password, android_id)
        
        if "Token" not in master_response:
            print(f"\nエラー: ログインに失敗しました。")
            if "Error" in master_response:
                if master_response["Error"] == "BadAuthentication":
                    print("パスワードが間違っているか、アプリパスワードが無効です。")
                else:
                    print(f"詳細: {master_response['Error']}")
            print("\nヒント:")
            print("  - 2段階認証が有効な場合はアプリパスワードを使用してください")
            print("  - アプリパスワード中のスペースは入れずに入力してください")
            sys.exit(1)
            
        token = master_response["Token"]
        
        # 取得したマスタートークンがgkeepapiで使えるかテスト
        keep = gkeepapi.Keep()
        keep.resume(email, token)
        
    except ImportError:
        print("\nエラー: gpsoauth パッケージが見つかりません。")
        print("以下を実行してインストールしてください: pip install gpsoauth")
        sys.exit(1)
    except Exception as e:
        print(f"\nエラー: 接続中に問題が発生しました。\n{e}")
        sys.exit(1)

    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        json.dump({"email": email, "token": token}, f)

    print(f"\nセットアップ完了！トークンを保存しました: {TOKEN_PATH}")
    print("次は sync_keep.py を実行してメモを同期できます。")


if __name__ == "__main__":
    setup()
