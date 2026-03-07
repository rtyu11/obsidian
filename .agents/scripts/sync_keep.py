"""
sync_keep.py - Sync labeled Google Keep notes to Obsidian Daily/Inbox

Behavior:
- Pull notes with labels: ob-ideas / ob-tasks / ob-memo
- Append notes to Daily/Inbox/YYYY-MM-DD-<suffix>.md
- Archive notes in Keep only after local write succeeds
- Prevent duplicates across runs using a local state file

Usage:
    python ".agents/scripts/sync_keep.py"
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/keep"]
TOKEN_PATH = Path.home() / ".keep_oauth_token.json"
STATE_PATH = Path.home() / ".keep_sync_state.json"
VAULT_PATH = Path(r"C:\Users\111r9\OneDrive\ドキュメント\Obsidian Vault\obsidian")
LABEL_MAP = {
    "ob-ideas": "ideas",
    "ob-tasks": "tasks",
    "ob-memo": "memo",
}


def load_credentials() -> Credentials:
    if not TOKEN_PATH.exists():
        print(f"Error: OAuth token not found: {TOKEN_PATH}")
        print("Run sync_keep_setup.py first.")
        sys.exit(1)

    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")

    if not creds.valid:
        print("Error: OAuth token is invalid. Re-run sync_keep_setup.py")
        sys.exit(1)
    return creds


def load_state() -> Dict[str, str]:
    if not STATE_PATH.exists():
        return {}
    try:
        raw = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return {str(k): str(v) for k, v in raw.items()}
    except Exception:
        pass
    return {}


def save_state(state: Dict[str, str]) -> None:
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def extract_note_text(note: dict) -> str:
    title = (note.get("title") or "").strip()
    body = note.get("body") or {}
    text_parts: List[str] = []

    body_text = (
        (((body.get("text") or {}).get("textContent") or {}).get("text"))
        or ((body.get("text") or {}).get("content"))
        or body.get("textContent")
        or body.get("content")
    )
    if isinstance(body_text, str) and body_text.strip():
        text_parts.append(body_text.strip())

    list_items = ((body.get("list") or {}).get("listItems")) or body.get("listItems") or []
    if isinstance(list_items, list):
        for item in list_items:
            text = (
                (((item.get("text") or {}).get("textContent") or {}).get("text"))
                or ((item.get("text") or {}).get("content"))
                or item.get("textContent")
                or item.get("content")
            )
            if isinstance(text, str) and text.strip():
                text_parts.append(text.strip())

    if not text_parts:
        for key in ("textContent", "content"):
            value = note.get(key)
            if isinstance(value, str) and value.strip():
                text_parts.append(value.strip())

    combined: List[str] = []
    if title:
        combined.append(title)
    if text_parts:
        combined.extend(text_parts)
    return "\n".join(combined).strip()


def list_all_notes(service) -> Iterable[dict]:
    page_token = None
    while True:
        req = service.notes().list(pageToken=page_token, pageSize=100)
        res = req.execute()
        for note in res.get("notes", []):
            yield note
        page_token = res.get("nextPageToken")
        if not page_token:
            break


def get_label_lookup(service) -> Dict[str, str]:
    lookup: Dict[str, str] = {}
    page_token = None
    while True:
        res = service.labels().list(pageToken=page_token, pageSize=100).execute()
        for label in res.get("labels", []):
            display = label.get("displayName")
            name = label.get("name")
            if display and name:
                lookup[display] = name
        page_token = res.get("nextPageToken")
        if not page_token:
            break
    return lookup


def note_is_archived_or_trashed(note: dict) -> bool:
    archived = bool(note.get("archived")) or bool(note.get("archiveTime"))
    trashed = bool(note.get("trashed")) or bool(note.get("trashTime"))
    return archived or trashed


def note_fingerprint(note: dict, text: str) -> str:
    updated = str(note.get("updateTime") or note.get("updated") or "")
    return f"{updated}|{text}"


def write_notes(collected: Dict[str, List[str]]) -> List[str]:
    today = datetime.now().strftime("%Y-%m-%d")
    inbox_dir = VAULT_PATH / "Daily" / "Inbox"
    inbox_dir.mkdir(parents=True, exist_ok=True)

    written: List[str] = []
    for suffix, notes in collected.items():
        if not notes:
            continue
        path = inbox_dir / f"{today}-{suffix}.md"
        mode = "a" if path.exists() else "w"
        with path.open(mode, encoding="utf-8") as f:
            if mode == "w":
                f.write(f"# {today} {suffix}\n\n")
            for text in notes:
                lines = text.splitlines()
                if not lines:
                    continue
                f.write(f"- {lines[0]}\n")
                for line in lines[1:]:
                    if line.strip():
                        f.write(f"  {line}\n")
        written.append(f"{path.name} ({len(notes)} notes)")
    return written


def archive_note(service, note_name: str) -> None:
    service.notes().patch(name=note_name, updateMask="archived", body={"archived": True}).execute()


def sync() -> None:
    creds = load_credentials()
    service = build("keep", "v1", credentials=creds, cache_discovery=False)

    label_lookup = get_label_lookup(service)
    target_label_ids = {label_lookup[k]: v for k, v in LABEL_MAP.items() if k in label_lookup}
    if not target_label_ids:
        print("No target labels found (ob-ideas / ob-tasks / ob-memo).")
        return

    state = load_state()
    collected: Dict[str, List[str]] = {suffix: [] for suffix in LABEL_MAP.values()}
    to_archive: List[str] = []
    processed_updates: Dict[str, str] = {}

    for note in list_all_notes(service):
        if note_is_archived_or_trashed(note):
            continue

        label_refs = [x.get("name") for x in note.get("labels", []) if isinstance(x, dict)]
        matched_suffix = None
        for label_id, suffix in target_label_ids.items():
            if label_id in label_refs:
                matched_suffix = suffix
                break
        if not matched_suffix:
            continue

        note_name = note.get("name")
        if not note_name:
            continue

        text = extract_note_text(note)
        if not text:
            continue

        fp = note_fingerprint(note, text)
        if state.get(note_name) == fp:
            continue

        collected[matched_suffix].append(text)
        to_archive.append(note_name)
        processed_updates[note_name] = fp

    if not any(collected.values()):
        print("No new labeled notes found.")
        return

    written = write_notes(collected)
    print(f"Written: {', '.join(written)}")

    archived_count = 0
    for note_name in to_archive:
        try:
            archive_note(service, note_name)
            archived_count += 1
            state[note_name] = processed_updates[note_name]
        except Exception as exc:
            print(f"Warning: failed to archive {note_name}: {exc}")

    save_state(state)
    print(f"Archived in Keep: {archived_count}/{len(to_archive)}")


if __name__ == "__main__":
    sync()
