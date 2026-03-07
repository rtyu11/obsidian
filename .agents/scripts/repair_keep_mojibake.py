"""
repair_keep_mojibake.py

Best-effort mojibake repair for KeepSidian-imported markdown files.
Targets files in Daily/Inbox/*.md (excluding .gitkeep).

Usage:
    python ".agents/scripts/repair_keep_mojibake.py" --apply
    python ".agents/scripts/repair_keep_mojibake.py"          # dry run
"""

from __future__ import annotations

import argparse
from pathlib import Path

INBOX_DIR = Path("Daily/Inbox")


def score_japanese(text: str) -> int:
    score = 0
    for ch in text:
        code = ord(ch)
        # Hiragana, Katakana, CJK Unified Ideographs
        if 0x3040 <= code <= 0x309F or 0x30A0 <= code <= 0x30FF or 0x4E00 <= code <= 0x9FFF:
            score += 2
    # Typical mojibake glyph clusters often seen from encoding mismatch
    for marker in ("繧", "縺", "繝", "蜷", "莨", "隱", "驕", "謨", "髫"):
        score -= text.count(marker) * 3
    return score


def try_repair(text: str) -> str:
    candidates = [text]
    # Common reverse path: mojibake text interpreted as cp932 should have been utf-8
    try:
        candidates.append(text.encode("cp932").decode("utf-8"))
    except Exception:
        pass
    # Secondary fallback for some environments
    try:
        candidates.append(text.encode("latin1").decode("utf-8"))
    except Exception:
        pass
    return max(candidates, key=score_japanese)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write repaired text back to files.")
    args = parser.parse_args()

    if not INBOX_DIR.exists():
        print(f"Inbox not found: {INBOX_DIR}")
        return

    files = [p for p in INBOX_DIR.glob("*.md") if p.name != ".gitkeep"]
    if not files:
        print("No markdown files found in Daily/Inbox.")
        return

    changed = 0
    for path in files:
        original = path.read_text(encoding="utf-8", errors="replace")
        repaired = try_repair(original)
        if repaired != original:
            changed += 1
            print(f"repair candidate: {path}")
            if args.apply:
                path.write_text(repaired, encoding="utf-8")

    mode = "applied" if args.apply else "dry-run"
    print(f"{mode}: {changed} file(s) need/received repair out of {len(files)}")


if __name__ == "__main__":
    main()
