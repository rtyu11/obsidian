"""
kindle_vocab_anki.py
Source/Kindle/*.md のハイライトから単語（短いフレーズ含む）を抽出し、
Gemini API でリッチなカード情報を生成して AnkiConnect 経由で追加する。

使い方:
  python .agents/scripts/kindle_vocab_anki.py [--dry-run] [--reset]

オプション:
  --dry-run   カードを追加せず、対象単語を一覧表示するだけ
  --reset     処理済みリストをリセットして全ハイライトを再取り込む

環境変数:
  GEMINI_API_KEY   Google AI Studio で取得したAPIキー（必須）
  VAULT_PATH       Vault のルートパス（省略時はスクリプトの2階層上）
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

import requests

# ---------- 設定 ----------
ANKI_CONNECT_URL = "http://localhost:8765"
DECK_NAME = "KindleVocab"
MODEL_NAME = "KindleVocab"
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

SCRIPT_DIR = Path(__file__).parent
STATE_FILE = SCRIPT_DIR / "kindle_vocab_anki_state.json"

# 単語・短いフレーズとして扱う最大単語数（3単語まで = "come across" "run out of" 等）
MAX_WORDS_IN_HIGHLIGHT = 3


# ---------- パス ----------

def get_vault_path() -> Path:
    env = os.environ.get("VAULT_PATH")
    if env:
        return Path(env)
    return SCRIPT_DIR.parent.parent


def get_kindle_source_dir() -> Path:
    return get_vault_path() / "Source" / "Kindle"


# ---------- 状態管理 ----------

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"processed_refs": []}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------- ハイライト解析 ----------

HIGHLIGHT_RE = re.compile(
    r"^>\s*(.+?)\s*—\s*location:\s*\[[\d\-]+\]\(.*?\)\s*\^(ref-\d+)",
    re.MULTILINE,
)


def is_english_word(text: str) -> bool:
    """英語の単語またはフレーズかどうか判定する。"""
    words = text.strip().split()
    if not words or len(words) > MAX_WORDS_IN_HIGHLIGHT:
        return False
    # ASCII文字・ハイフン・アポストロフィのみで構成されているか
    return all(re.match(r"^[a-zA-Z\-']+$", w) for w in words)


def extract_highlights_from_file(md_path: Path) -> list[dict]:
    """Source/Kindle/*.md から英単語ハイライトを抽出する。"""
    text = md_path.read_text(encoding="utf-8")

    # 書籍タイトルを取得（frontmatterから）
    title_match = re.search(r"kindle-title:\s*['\"]?(.+?)['\"]?\s*$", text, re.MULTILINE)
    book_title = title_match.group(1).strip() if title_match else md_path.stem

    results = []
    for m in HIGHLIGHT_RE.finditer(text):
        highlight_text = m.group(1).strip()
        ref = m.group(2)
        if is_english_word(highlight_text):
            results.append({
                "word": highlight_text.lower(),
                "ref": ref,
                "book": book_title,
            })
    return results


def collect_all_highlights(source_dir: Path) -> list[dict]:
    """全Kindleハイライトファイルから英単語を収集する。"""
    all_words = []
    for md_file in sorted(source_dir.glob("*.md")):
        try:
            words = extract_highlights_from_file(md_file)
            all_words.extend(words)
        except Exception as e:
            print(f"  ⚠️  {md_file.name} の読み込みに失敗: {e}")
    return all_words


# ---------- Gemini API ----------

GEMINI_PROMPT_TEMPLATE = """\
あなたは英語学習カードを作るアシスタントです。
以下の英単語（またはフレーズ）について、学習に最適なAnkiカード情報をJSON形式で返してください。

単語: {word}
出典の本: {book}

返答は必ず以下のJSON形式のみ（コードブロック不要、説明文不要）:
{{
  "definition": "英語での定義（平易な英語で1〜2文、辞書的すぎず自然な説明）",
  "example": "この単語を使った自然な英語例文（できれば本のトーンに合わせて）",
  "japanese": "日本語訳（簡潔に、1〜3語）",
  "japanese_note": "日本語での補足説明（ニュアンス・使い方・類語）",
  "memory_tip": "記憶に残る覚え方（語源・イメージ・他の単語との連想など、1文）",
  "level": "CEFR推定レベル（A1/A2/B1/B2/C1/C2のいずれか）"
}}"""


def generate_card_content(word: str, book: str, api_key: str) -> dict | None:
    """Gemini API でカード内容を生成する。失敗時は None を返す。"""
    prompt = GEMINI_PROMPT_TEMPLATE.format(word=word, book=book)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 512},
    }
    try:
        resp = requests.post(
            f"{GEMINI_URL}?key={api_key}",
            json=payload,
            timeout=20,
        )
        if resp.status_code != 200:
            print(f"Gemini APIエラー {resp.status_code}: {resp.text[:200]}")
            return None
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        # JSONのみ抽出（コードブロックが付いていても除去）
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
        return json.loads(text)
    except Exception as e:
        print(f"Gemini解析エラー: {e}")
        return None


# ---------- AnkiConnect ----------

def anki_request(action: str, **params) -> dict:
    payload = {"action": action, "version": 6, "params": params}
    resp = requests.post(ANKI_CONNECT_URL, json=payload, timeout=10)
    return resp.json()


def ensure_deck_and_model():
    """デッキとカードモデルが存在しなければ作成する。"""
    anki_request("createDeck", deck=DECK_NAME)

    result = anki_request("modelNames")
    if MODEL_NAME in (result.get("result") or []):
        return

    anki_request(
        "createModel",
        modelName=MODEL_NAME,
        inOrderFields=["Word", "Definition", "Example", "Japanese", "JapaneseNote", "MemoryTip", "Level", "Book"],
        css="""
.card {
  font-family: 'Helvetica Neue', 'Hiragino Sans', sans-serif;
  font-size: 17px; color: #2c2c2c; background: #fafafa;
  max-width: 560px; margin: 0 auto; padding: 24px 20px;
}
.word { font-size: 32px; font-weight: bold; letter-spacing: 0.02em; margin-bottom: 4px; }
.level { display: inline-block; font-size: 11px; color: #fff; background: #6c8ebf;
         border-radius: 3px; padding: 1px 6px; margin-left: 8px; vertical-align: middle; }
.definition { font-size: 15px; color: #444; margin: 14px 0 6px; }
.example { font-size: 14px; color: #555; font-style: italic;
           border-left: 3px solid #ccc; padding-left: 10px; margin: 8px 0; }
.ja-section { margin-top: 14px; }
.japanese { font-size: 20px; color: #1a5c3a; font-weight: bold; }
.ja-note { font-size: 13px; color: #555; margin-top: 4px; }
.memory { font-size: 13px; color: #7a5c00; background: #fffbe6;
          border-radius: 4px; padding: 6px 10px; margin-top: 12px; }
.memory::before { content: "💡 "; }
.book { font-size: 11px; color: #aaa; margin-top: 14px; text-align: right; }
.toggle-btn {
  cursor: pointer; color: #0070c0; font-size: 12px;
  border: 1px solid #0070c0; border-radius: 4px;
  padding: 2px 8px; margin-top: 10px; display: inline-block;
  user-select: none;
}
        """,
        cardTemplates=[
            {
                "Name": "KindleVocab",
                "Front": """<div class="card">
  <div class="word">{{Word}}
    {{#Level}}<span class="level">{{Level}}</span>{{/Level}}
  </div>
</div>""",
                "Back": """<div class="card">
  <div class="word">{{Word}}
    {{#Level}}<span class="level">{{Level}}</span>{{/Level}}
  </div>
  <div class="definition">{{Definition}}</div>
  {{#Example}}<div class="example">{{Example}}</div>{{/Example}}
  <div class="ja-section">
    <span class="toggle-btn" onclick="
      var s=document.getElementById('ja-block');
      var open=s.style.display!=='none';
      s.style.display=open?'none':'block';
      this.textContent=open?'▶ 日本語を見る':'▲ 閉じる';
    ">▶ 日本語を見る</span>
    <div id="ja-block" style="display:none">
      <div class="japanese">{{Japanese}}</div>
      {{#JapaneseNote}}<div class="ja-note">{{JapaneseNote}}</div>{{/JapaneseNote}}
    </div>
  </div>
  {{#MemoryTip}}<div class="memory">{{MemoryTip}}</div>{{/MemoryTip}}
  {{#Book}}<div class="book">📖 {{Book}}</div>{{/Book}}
</div>""",
            }
        ],
    )


def card_exists(word: str) -> bool:
    result = anki_request("findNotes", query=f'deck:{DECK_NAME} Word:"{word}"')
    return bool(result.get("result"))


def add_card(word: str, content: dict, book: str) -> bool:
    result = anki_request(
        "addNote",
        note={
            "deckName": DECK_NAME,
            "modelName": MODEL_NAME,
            "fields": {
                "Word": word,
                "Definition": content.get("definition", ""),
                "Example": content.get("example", ""),
                "Japanese": content.get("japanese", ""),
                "JapaneseNote": content.get("japanese_note", ""),
                "MemoryTip": content.get("memory_tip", ""),
                "Level": content.get("level", ""),
                "Book": book,
            },
            "options": {"allowDuplicate": False},
            "tags": ["kindle", "vocabulary"],
        },
    )
    return result.get("error") is None


# ---------- メイン ----------

def main():
    parser = argparse.ArgumentParser(description="Kindle ハイライト → Anki カード自動追加")
    parser.add_argument("--dry-run", action="store_true", help="カードを追加せず対象単語を一覧表示")
    parser.add_argument("--reset", action="store_true", help="処理済みリストをリセットして全単語を再取り込む")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key and not args.dry_run:
        print("❌ GEMINI_API_KEY が設定されていません。")
        sys.exit(1)

    source_dir = get_kindle_source_dir()
    if not source_dir.exists():
        print(f"❌ Source/Kindle/ が見つかりません: {source_dir}")
        sys.exit(1)

    # 状態読み込み
    state = load_state()
    if args.reset:
        state["processed_refs"] = []
        print("🔄 処理済みリストをリセットしました。")
    processed_refs = set(state.get("processed_refs", []))

    # ハイライト収集
    print(f"📂 {source_dir} を検索中...")
    all_highlights = collect_all_highlights(source_dir)
    new_highlights = [h for h in all_highlights if h["ref"] not in processed_refs]

    # 同じ単語の重複を除去（最初の出現を優先）
    seen_words: set[str] = set()
    unique_highlights = []
    for h in new_highlights:
        if h["word"] not in seen_words:
            seen_words.add(h["word"])
            unique_highlights.append(h)

    print(f"📝 新規単語: {len(unique_highlights)} 件（全ハイライト {len(all_highlights)} 件中）")

    if not unique_highlights:
        print("✅ 新規単語はありません。")
        return

    if args.dry_run:
        print("\n--- dry-run: 対象単語一覧 ---")
        for h in unique_highlights:
            print(f"  {h['word']:20s}  ({h['book'][:40]})")
        return

    # AnkiConnect 接続確認
    try:
        result = anki_request("version")
        if result.get("error"):
            raise ConnectionError
    except Exception:
        print("❌ AnkiConnect に接続できません。")
        print("   Ankiを起動し、AnkiConnectアドオン（コード: 2055492159）が有効か確認してください。")
        sys.exit(1)

    ensure_deck_and_model()

    added = 0
    skipped = 0
    failed = 0

    for i, h in enumerate(unique_highlights, 1):
        word = h["word"]
        book = h["book"]
        ref = h["ref"]

        print(f"[{i}/{len(unique_highlights)}] {word} ...", end=" ", flush=True)

        if card_exists(word):
            print("スキップ（既存）")
            skipped += 1
        else:
            content = generate_card_content(word, book, api_key)
            if content is None:
                print("失敗（Gemini APIエラー）✗")
                failed += 1
                time.sleep(1)
                continue

            success = add_card(word, content, book)
            if success:
                ja = content.get("japanese", "")
                level = content.get("level", "")
                print(f"追加済み ✓  [{level}] {ja}")
                added += 1
            else:
                print("失敗（Anki追加エラー）✗")
                failed += 1

        processed_refs.add(ref)
        # Gemini API レート制限対策（無料枠: 15 req/min）
        time.sleep(4)

    # 状態保存
    state["processed_refs"] = list(processed_refs)
    save_state(state)

    print(f"\n✅ 完了: 追加 {added}件 / スキップ {skipped}件 / 失敗 {failed}件")


if __name__ == "__main__":
    main()
