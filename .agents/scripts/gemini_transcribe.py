"""
gemini_transcribe.py
LINE/audio/ 内の未処理音声ファイルを Gemini API で文字起こし・整形し、
LINE/*.md として出力する。

使い方:
  python .agents/scripts/gemini_transcribe.py

環境変数:
  GEMINI_API_KEY  Google AI Studio で取得したAPIキー
  VAULT_PATH      Vault のルートパス（省略時はスクリプトの2階層上）
"""

import os
import sys
import re
from datetime import datetime
from pathlib import Path

# ---------- 設定 ----------
AUDIO_EXTENSIONS = {".m4a", ".mp3", ".ogg", ".aac", ".wav", ".flac", ".opus"}
PROCESSED_PREFIX = "_processed_"

TRANSCRIBE_PROMPT = """
この音声メモを文字起こしし、話し言葉を自然な書き言葉（日本語）に整形してください。

ルール:
- 「えー」「あの」などのフィラーは除去する
- 「これは名言です」「アイデアです」など種別を示す発言は内容の分類に使い、本文には含めない
- 内容の末尾に種別タグを1つ付ける:
    #quotes  → 他者の言葉・名言・格言（出典が他者のもの）
    #ideas   → アイデア・企画・やってみたい
    #tasks   → 課題・やること・TODO
    #memo    → それ以外の雑多なメモ・気づき

出力形式（Markdownのみ、frontmatterなし）:
---
整形されたテキスト本文

#タグ
---

余分な説明文は不要。本文とタグだけを出力してください。
""".strip()


def get_vault_path() -> Path:
    env = os.environ.get("VAULT_PATH")
    if env:
        return Path(env)
    return Path(__file__).parent.parent.parent


def transcribe_audio(audio_path: Path, api_key: str) -> str:
    """Gemini API で音声ファイルを文字起こし・整形する"""
    try:
        from google import genai
    except ImportError:
        print("ERROR: google-genai がインストールされていません。")
        print("  pip install google-genai")
        sys.exit(1)

    import time
    client = genai.Client(api_key=api_key)

    print(f"  アップロード中: {audio_path.name}")
    from google.genai import types as genai_types
    audio_file = client.files.upload(
        file=str(audio_path),
        config=genai_types.UploadFileConfig(mime_type=_guess_mime(audio_path))
    )

    # アップロード完了を待機
    while audio_file.state.name == "PROCESSING":
        time.sleep(2)
        audio_file = client.files.get(name=audio_file.name)

    if audio_file.state.name == "FAILED":
        raise RuntimeError(f"Gemini へのアップロードに失敗しました: {audio_path.name}")

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-preview",
        contents=[TRANSCRIBE_PROMPT, audio_file]
    )
    return response.text.strip()


def _guess_mime(path: Path) -> str:
    mapping = {
        ".m4a": "audio/mp4",
        ".mp3": "audio/mpeg",
        ".ogg": "audio/ogg",
        ".aac": "audio/aac",
        ".wav": "audio/wav",
        ".flac": "audio/flac",
        ".opus": "audio/opus",
    }
    return mapping.get(path.suffix.lower(), "audio/mpeg")


def build_md(text: str, date_str: str, source_filename: str) -> str:
    """文字起こし結果を LINE/*.md 形式に整形する"""
    # タグ行を抽出（末尾の #xxx）
    tag_match = re.search(r"(#(?:quotes|ideas|tasks|memo))\s*$", text, re.MULTILINE)
    tag_line = tag_match.group(1) if tag_match else "#memo"
    body = text[:tag_match.start()].strip() if tag_match else text.strip()

    content = f"""---
date: {date_str}
source: line-audio
original: {source_filename}
---

{body}

{tag_line}
"""
    return content


def process_audio_folder(vault: Path, api_key: str):
    audio_dir = vault / "LINE" / "audio"
    line_dir = vault / "LINE"

    if not audio_dir.exists():
        print("LINE/audio/ フォルダが存在しません。スキップします。")
        return

    targets = [
        f for f in audio_dir.iterdir()
        if f.is_file()
        and f.suffix.lower() in AUDIO_EXTENSIONS
        and not f.name.startswith(PROCESSED_PREFIX)
    ]

    if not targets:
        print("LINE/audio/ に未処理の音声ファイルはありません。")
        return

    print(f"対象ファイル: {len(targets)} 件")
    ok, ng = 0, 0

    for audio_path in targets:
        print(f"\n処理中: {audio_path.name}")
        try:
            transcribed = transcribe_audio(audio_path, api_key)
            date_str = datetime.now().strftime("%Y-%m-%d")
            md_content = build_md(transcribed, date_str, audio_path.name)

            # 出力ファイル名（重複回避）
            base_name = f"{date_str}_audio_{audio_path.stem}"
            out_path = line_dir / f"{base_name}.md"
            counter = 1
            while out_path.exists():
                out_path = line_dir / f"{base_name}_{counter}.md"
                counter += 1

            out_path.write_text(md_content, encoding="utf-8")
            print(f"  → 保存: {out_path.relative_to(vault)}")

            # 処理済みリネーム
            processed_path = audio_dir / f"{PROCESSED_PREFIX}{audio_path.name}"
            audio_path.rename(processed_path)
            print(f"  → リネーム: {processed_path.name}")
            ok += 1

        except Exception as e:
            print(f"  ERROR: {e}")
            ng += 1

    print(f"\n完了: 成功 {ok} 件 / 失敗 {ng} 件")
    if ok > 0:
        print("次に「LINEを処理して」と指示すると、テキストとして整形・分類されます。")


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: 環境変数 GEMINI_API_KEY が設定されていません。")
        print("  Google AI Studio (https://aistudio.google.com) でAPIキーを取得し、")
        print("  環境変数 GEMINI_API_KEY に設定してください。")
        sys.exit(1)

    vault = get_vault_path()
    print(f"Vault: {vault}")
    process_audio_folder(vault, api_key)


if __name__ == "__main__":
    main()
