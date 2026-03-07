"""
Process KeepSidian inbox notes into Daily lists with deduplication.

Features:
- Classify notes by tag: #ob-ideas, #ob-tasks, #ob-memo, #ob-diary
- De-duplicate repeated title/body text
- Skip already-processed Keep note IDs across runs
- Append only new entries to destination files
- Delete Inbox files/folders after processing

Usage:
    python ".agents/scripts/process_keep_inbox.py"
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


ROOT = Path(".")
INBOX_DIR = ROOT / "Daily" / "Inbox"
STATE_PATH = ROOT / ".agents" / "state" / "keep_processed_ids.json"

TAG_PATTERNS = [
    (re.compile(r"(?im)^\s*#ob-ideas?\s*$"), "ideas"),
    (re.compile(r"(?im)^\s*#ob-tasks?\s*$"), "tasks"),
    (re.compile(r"(?im)^\s*#ob-memo\s*$"), "memo"),
    (re.compile(r"(?im)^\s*#ob-diary\s*$"), "diary"),
]


@dataclass
class InboxNote:
    path: Path
    keep_id: str
    keep_url: str
    title: str
    bucket: str
    entry: str


def load_state() -> Set[str]:
    if not STATE_PATH.exists():
        return set()
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return set()
    values = data.get("processed_ids", [])
    return {str(v) for v in values if v}


def save_state(processed_ids: Set[str]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"processed_ids": sorted(processed_ids)}
    STATE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def save_archive_queue(items: List[Tuple[str, str]]) -> Optional[Path]:
    clean = [(t, u) for (t, u) in items if u]
    if not clean:
        return None
    today = datetime.now().strftime("%Y-%m-%d")

    queue_state = ROOT / ".agents" / "state" / "keep_archive_queue.md"
    queue_state.parent.mkdir(parents=True, exist_ok=True)
    state_lines = ["# Keep Manual Archive Queue", "", "Processed notes to archive in Google Keep:", ""]
    for title, url in clean:
        state_lines.append(f"- [{title}]({url})")
    state_lines.append("")
    queue_state.write_text("\n".join(state_lines), encoding="utf-8")

    mobile_note = ROOT / "Daily" / "Tasks" / "Keepアーカイブ候補.md"
    if mobile_note.exists():
        existing = mobile_note.read_text(encoding="utf-8", errors="replace").rstrip()
    else:
        existing = "# Keepアーカイブ候補"
    block = [f"", f"## {today}", ""]
    for title, url in clean:
        block.append(f"- [ ] [{title}]({url})")
    mobile_note.write_text(existing + "\n" + "\n".join(block) + "\n", encoding="utf-8")

    return queue_state


def parse_frontmatter(raw: str) -> Tuple[Dict[str, str], str]:
    if not raw.startswith("---"):
        return {}, raw.strip()
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}, raw.strip()
    meta_block = parts[1]
    body = parts[2].strip()
    meta: Dict[str, str] = {}
    for line in meta_block.splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        meta[k.strip()] = v.strip()
    return meta, body


def extract_keep_id(meta: Dict[str, str], path: Path, body: str) -> str:
    url = meta.get("GoogleKeepUrl", "")
    m = re.search(r"/#NOTE/([A-Za-z0-9_-]+)", url)
    if m:
        return m.group(1)
    digest = hashlib.sha1(f"{path.stem}\n{body}".encode("utf-8", errors="replace")).hexdigest()
    return f"fallback:{digest}"


def classify_bucket(body: str) -> str:
    for pattern, bucket in TAG_PATTERNS:
        if pattern.search(body):
            return bucket
    return "memo"


def normalize_entry(path: Path, body: str) -> str:
    cleaned = body
    for pattern, _ in TAG_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    lines = [ln.strip() for ln in cleaned.splitlines() if ln.strip()]

    title = path.stem.strip()
    if not lines:
        return f"- {title}"

    first = lines[0]
    rest = lines[1:]

    # Avoid "title: title" repetition for short voice notes.
    if first == title:
        if not rest:
            return f"- {title}"
        merged = " / ".join(rest)
        return f"- {title}: {merged}"

    merged = " / ".join(lines)
    if merged == title:
        return f"- {title}"
    return f"- {title}: {merged}"


def pick_destination_file(bucket: str) -> Path:
    if bucket == "ideas":
        folder = ROOT / "Daily" / "Ideas"
        fallback = "list.md"
    elif bucket == "tasks":
        folder = ROOT / "Daily" / "Tasks"
        fallback = "list.md"
    elif bucket == "diary":
        folder = ROOT / "Daily" / "Diary"
        fallback = "diary_list.md"
    else:
        folder = ROOT / "Daily" / "Memo"
        fallback = "list.md"

    folder.mkdir(parents=True, exist_ok=True)
    files = sorted(folder.glob("*.md"))
    if files:
        return files[0]
    return folder / fallback


def append_entries(path: Path, entries: List[str], date_key: str) -> int:
    if not entries:
        return 0

    if path.exists():
        text = path.read_text(encoding="utf-8", errors="replace")
    else:
        text = f"# {path.stem}\n"

    existing = {ln.strip() for ln in text.splitlines() if ln.strip().startswith("- ")}
    new_entries = [e for e in entries if e.strip() not in existing]
    if not new_entries:
        return 0

    heading = f"### [{date_key}]"
    if heading not in text:
        text = text.rstrip() + f"\n\n{heading}\n"
    else:
        text = text.rstrip() + "\n"

    text += "\n".join(new_entries) + "\n"
    path.write_text(text, encoding="utf-8")
    return len(new_entries)


def delete_path_force(path: Path) -> None:
    p = str(path.resolve())
    long_path = p if p.startswith("\\\\?\\") else f"\\\\?\\{p}"
    if path.is_dir():
        subprocess.run(["cmd", "/c", "rd", "/s", "/q", long_path], check=False)
    else:
        subprocess.run(["cmd", "/c", "del", "/f", "/q", long_path], check=False)


def cleanup_inbox() -> int:
    if not INBOX_DIR.exists():
        return 0
    targets = [p for p in INBOX_DIR.iterdir() if p.name != ".gitkeep"]
    for p in targets:
        delete_path_force(p)
    return len(targets)


def collect_notes() -> List[InboxNote]:
    if not INBOX_DIR.exists():
        return []
    notes: List[InboxNote] = []
    for path in sorted(INBOX_DIR.glob("*.md")):
        if path.name == ".gitkeep":
            continue
        raw = path.read_text(encoding="utf-8", errors="replace")
        meta, body = parse_frontmatter(raw)
        keep_id = extract_keep_id(meta, path, body)
        keep_url = meta.get("GoogleKeepUrl", "").strip()
        title = path.stem.strip()
        bucket = classify_bucket(body)
        entry = normalize_entry(path, body)
        notes.append(InboxNote(path=path, keep_id=keep_id, keep_url=keep_url, title=title, bucket=bucket, entry=entry))
    return notes


def main() -> None:
    processed_ids = load_state()
    notes = collect_notes()
    if not notes:
        print("No inbox markdown files found.")
        return

    grouped: Dict[str, List[str]] = {"ideas": [], "tasks": [], "memo": [], "diary": []}
    to_mark_processed: Set[str] = set()
    archive_items: List[Tuple[str, str]] = []

    for note in notes:
        if note.keep_id in processed_ids:
            continue
        grouped[note.bucket].append(note.entry)
        to_mark_processed.add(note.keep_id)
        if note.keep_url:
            archive_items.append((note.title, note.keep_url))

    today = datetime.now().strftime("%Y-%m-%d")
    appended_total = 0
    for bucket, entries in grouped.items():
        if not entries:
            continue
        path = pick_destination_file(bucket)
        appended_total += append_entries(path, entries, today)

    processed_ids.update(to_mark_processed)
    save_state(processed_ids)
    queue_path = save_archive_queue(archive_items)

    removed = cleanup_inbox()
    print(f"processed notes: {len(to_mark_processed)}")
    print(f"appended entries: {appended_total}")
    print(f"cleaned inbox items: {removed}")
    if queue_path is not None:
        print(f"archive queue: {queue_path}")


if __name__ == "__main__":
    main()
