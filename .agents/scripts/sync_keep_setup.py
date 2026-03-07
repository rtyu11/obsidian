"""
sync_keep_setup.py - OAuth setup for Google Keep sync

This script performs one-time OAuth authorization and stores a refreshable token
for unattended runs of sync_keep.py.

Usage:
    pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
    python ".agents/scripts/sync_keep_setup.py" --client-secrets "C:/path/to/client_secret.json"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/keep"]
DEFAULT_TOKEN_PATH = Path.home() / ".keep_oauth_token.json"
DEFAULT_CLIENT_SECRETS = Path.home() / ".keep_client_secret.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Google Keep OAuth setup")
    parser.add_argument(
        "--client-secrets",
        default=str(DEFAULT_CLIENT_SECRETS),
        help="Path to OAuth client secret JSON downloaded from Google Cloud.",
    )
    parser.add_argument(
        "--token-path",
        default=str(DEFAULT_TOKEN_PATH),
        help="Where to save OAuth token JSON.",
    )
    parser.add_argument(
        "--no-local-server",
        action="store_true",
        help="Use console flow instead of opening a local callback server.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client_secrets_path = Path(args.client_secrets).expanduser()
    token_path = Path(args.token_path).expanduser()

    if not client_secrets_path.exists():
        print(f"Error: client secret file not found: {client_secrets_path}")
        print("Create OAuth client credentials in Google Cloud and download JSON first.")
        sys.exit(1)

    if token_path.exists():
        overwrite = input(f"Token already exists at {token_path}. Overwrite? [y/N]: ").strip().lower()
        if overwrite != "y":
            print("Canceled.")
            return

    flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_path), SCOPES)
    if args.no_local_server:
        creds = flow.run_console()
    else:
        creds = flow.run_local_server(port=0)

    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")

    print("OAuth setup completed.")
    print(f"Token saved: {token_path}")
    print("You can now run: python .agents/scripts/sync_keep.py")


if __name__ == "__main__":
    main()
