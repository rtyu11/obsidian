"""
kindle_vocab_anki.py
Source/Kindle/*.md のハイライトから英単語・熟語を抽出し、
Gemini API でリッチなカード情報を生成して Anki に追加する。

Ankiの起動状態に応じて自動切り替え：
  ・Anki起動中  → AnkiConnect 経由でリアルタイム追加
  ・Anki未起動  → .apkg ファイルを生成（あとでダブルクリックしてインポート）

ハイライトの種類：
  ・1〜3語 → 辞書形に正規化してカード化
  ・4語以上（文）→ Geminiが重要語彙・熟語を抽出してカード化

使い方:
  python .agents/scripts/kindle_vocab_anki.py [--dry-run] [--reset]

オプション:
  --dry-run   カードを追加せず対象単語を一覧表示するだけ
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

import requests

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# ---------- 設定 ----------
ANKI_CONNECT_URL = "http://localhost:8765"
DECK_NAME = "KindleVocab"
MODEL_NAME = "KindleVocab"
GEMINI_MODEL = "gemini-3.1-flash-lite-preview"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

SCRIPT_DIR = Path(__file__).parent
STATE_FILE = SCRIPT_DIR / "kindle_vocab_anki_state.json"
APKG_OUTPUT = SCRIPT_DIR / "kindle_vocab_new.apkg"

WORD_HIGHLIGHT_MAX = 3

# genanki モデルID（固定値 - 変えると既存デッキと別物になる）
GENANKI_MODEL_ID = 1825854800
GENANKI_DECK_ID = 1825854801

CARD_CSS = """
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
"""

FRONT_TMPL = """<div class="card">
  <div class="word">{{Word}}
    {{#Level}}<span class="level">{{Level}}</span>{{/Level}}
  </div>
</div>"""

BACK_TMPL = """<div class="card">
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
</div>"""


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
    return {"processed_refs": [], "added_words": []}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------- ハイライト解析 ----------

HIGHLIGHT_RE = re.compile(
    r"^>?\s*(.+?)\s*[—–-]+\s*location:\s*\[[\d\-]+\]\(.*?\)\s*\^(ref-\d+)",
    re.MULTILINE,
)

STRIP_PUNCT_RE = re.compile(r'[.,;:!?\'""\'\'""「」。、…]+$')


def classify_highlight(text: str) -> str:
    cleaned = STRIP_PUNCT_RE.sub("", text.strip()).strip()

    cjk_count = len(re.findall(r"[　-鿿豈-￯]", cleaned))
    latin_count = len(re.findall(r"[a-zA-Z]", cleaned))
    if cjk_count > latin_count:
        return "ignore"

    words = cleaned.split()
    if not words:
        return "ignore"

    if len(words) <= WORD_HIGHLIGHT_MAX and all(re.match(r"^[a-zA-Z\-']+$", w) for w in words):
        return "word"

    if latin_count > 3:
        return "sentence"

    return "ignore"


def extract_highlights_from_file(md_path: Path) -> list[dict]:
    text = md_path.read_text(encoding="utf-8")
    title_match = re.search(r"kindle-title:\s*['\"]?(.+?)['\"]?\s*$", text, re.MULTILINE)
    book_title = title_match.group(1).strip() if title_match else md_path.stem

    results = []
    for m in HIGHLIGHT_RE.finditer(text):
        highlight_text = m.group(1).strip()
        ref = m.group(2)
        kind = classify_highlight(highlight_text)
        if kind != "ignore":
            results.append({"text": highlight_text, "ref": ref, "book": book_title, "kind": kind})
    return results


def collect_all_highlights(source_dir: Path) -> list[dict]:
    all_highlights = []
    for md_file in sorted(source_dir.glob("*.md")):
        try:
            all_highlights.extend(extract_highlights_from_file(md_file))
        except Exception as e:
            print(f"  ⚠️  {md_file.name} の読み込みに失敗: {e}")
    return all_highlights


# ---------- Gemini API ----------

def _call_gemini(prompt: str, api_key: str) -> str | None:
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 1024},
    }
    try:
        resp = requests.post(f"{GEMINI_URL}?key={api_key}", json=payload, timeout=30)
        if resp.status_code != 200:
            print(f"Gemini APIエラー {resp.status_code}: {resp.text[:300]}")
            return None
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        return re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    except Exception as e:
        print(f"Gemini呼び出しエラー: {e}")
        return None


# 単語1件: 辞書形 + カード内容を一括生成
CARD_PROMPT = """\
英語学習カードを作るアシスタントです。

単語/熟語（ハイライトのまま）: {word}
出典: {book}

この単語の辞書形（base form）を特定し、その辞書形でAnkiカード情報を生成してください。
例: dissecting→dissect, envoys→envoy, peered→peer, averting→avert, comprises→comprise

以下のJSON形式のみ（コードブロック不要）:
{{
  "base_word": "辞書形（不明な場合はそのまま）",
  "definition": "平易な英語での定義（1〜2文）",
  "example": "自然な英語例文",
  "japanese": "日本語訳（1〜3語）",
  "japanese_note": "ニュアンス・使い方の補足（1文）",
  "memory_tip": "覚え方ヒント（語源・イメージ・連想など1文）",
  "level": "CEFR推定レベル（A1/A2/B1/B2/C1/C2）"
}}"""

# 文: 重要語彙を抽出 + 各辞書形 + カード内容を一括生成
SENTENCE_EXTRACT_PROMPT = """\
英語学習アシスタントです。以下のハイライト英文から学習価値の高い語彙・熟語を1〜4件抽出し、各々の辞書形とAnkiカード情報をまとめて返してください。

ハイライト文: {sentence}
出典: {book}

抽出ルール:
- 非自明・高度・慣用的な語句を優先する
- 熟語・句動詞はまとめて1エントリにする（例: "come across"）
- 一般的すぎる単語（the, is, very等）・固有名詞は除外する
- base_word は必ず辞書形（原形/単数形）にする

以下のJSON形式のみ（コードブロック不要）:
[
  {{
    "base_word": "辞書形",
    "definition": "平易な英語での定義（1〜2文）",
    "example": "この文を活かした例文またはAI生成例文",
    "japanese": "日本語訳（1〜3語）",
    "japanese_note": "ニュアンス・使い方の補足（1文）",
    "memory_tip": "覚え方ヒント（語源・イメージ・連想など1文）",
    "level": "CEFR推定レベル（A1/A2/B1/B2/C1/C2）"
  }}
]"""


def generate_card_for_word(word: str, book: str, api_key: str) -> dict | None:
    raw = _call_gemini(CARD_PROMPT.format(word=word, book=book), api_key)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def extract_vocab_from_sentence(sentence: str, book: str, api_key: str) -> list[dict] | None:
    raw = _call_gemini(SENTENCE_EXTRACT_PROMPT.format(sentence=sentence, book=book), api_key)
    if not raw:
        return None
    try:
        result = json.loads(raw)
        return result if isinstance(result, list) else None
    except Exception:
        return None


# ---------- AnkiConnect ----------

def anki_connect_available() -> bool:
    try:
        r = requests.post(ANKI_CONNECT_URL, json={"action": "version", "version": 6}, timeout=3)
        return r.json().get("error") is None
    except Exception:
        return False


def anki_request(action: str, **params) -> dict:
    payload = {"action": action, "version": 6, "params": params}
    return requests.post(ANKI_CONNECT_URL, json=payload, timeout=10).json()


def ensure_deck_and_model_connect():
    anki_request("createDeck", deck=DECK_NAME)
    if MODEL_NAME in (anki_request("modelNames").get("result") or []):
        return
    anki_request(
        "createModel",
        modelName=MODEL_NAME,
        inOrderFields=["Word", "Definition", "Example", "Japanese", "JapaneseNote", "MemoryTip", "Level", "Book"],
        css=CARD_CSS,
        cardTemplates=[{"Name": "KindleVocab", "Front": FRONT_TMPL, "Back": BACK_TMPL}],
    )


def add_card_connect(word: str, content: dict, book: str) -> bool:
    result = anki_request(
        "addNote",
        note={
            "deckName": DECK_NAME,
            "modelName": MODEL_NAME,
            "fields": _build_fields(word, content, book),
            "options": {"allowDuplicate": False},
            "tags": ["kindle", "vocabulary"],
        },
    )
    return result.get("error") is None


def card_exists_connect(word: str) -> bool:
    result = anki_request("findNotes", query=f'deck:{DECK_NAME} Word:"{word}"')
    return bool(result.get("result"))


# ---------- genanki (.apkg) ----------

def build_apkg(cards: list[dict], output_path: Path):
    import genanki

    model = genanki.Model(
        GENANKI_MODEL_ID,
        MODEL_NAME,
        fields=[
            {"name": "Word"}, {"name": "Definition"}, {"name": "Example"},
            {"name": "Japanese"}, {"name": "JapaneseNote"}, {"name": "MemoryTip"},
            {"name": "Level"}, {"name": "Book"},
        ],
        templates=[{"name": "KindleVocab", "qfmt": FRONT_TMPL, "afmt": BACK_TMPL}],
        css=CARD_CSS,
    )
    deck = genanki.Deck(GENANKI_DECK_ID, DECK_NAME)

    for c in cards:
        note = genanki.Note(model=model, fields=[
            c.get("Word", ""), c.get("Definition", ""), c.get("Example", ""),
            c.get("Japanese", ""), c.get("JapaneseNote", ""), c.get("MemoryTip", ""),
            c.get("Level", ""), c.get("Book", ""),
        ], tags=["kindle", "vocabulary"])
        deck.add_note(note)

    genanki.Package(deck).write_to_file(str(output_path))


# ---------- ユーティリティ ----------

def _build_fields(word: str, content: dict, book: str) -> dict:
    return {
        "Word": word,
        "Definition": content.get("definition", ""),
        "Example": content.get("example", ""),
        "Japanese": content.get("japanese", ""),
        "JapaneseNote": content.get("japanese_note", ""),
        "MemoryTip": content.get("memory_tip", ""),
        "Level": content.get("level", ""),
        "Book": book,
    }


# ---------- メイン ----------

def main():
    parser = argparse.ArgumentParser(description="Kindle ハイライト → Anki カード自動追加")
    parser.add_argument("--dry-run", action="store_true", help="カードを追加せず対象を一覧表示")
    parser.add_argument("--reset", action="store_true", help="処理済みリストをリセットして全ハイライトを再取り込む")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key and not args.dry_run:
        print("❌ GEMINI_API_KEY が設定されていません。")
        sys.exit(1)

    source_dir = get_kindle_source_dir()
    if not source_dir.exists():
        print(f"❌ Source/Kindle/ が見つかりません: {source_dir}")
        sys.exit(1)

    state = load_state()
    if args.reset:
        state["processed_refs"] = []
        state["added_words"] = []
        print("🔄 処理済みリストをリセットしました。")
    processed_refs = set(state.get("processed_refs", []))
    added_words: set[str] = set(state.get("added_words", []))

    print(f"📂 {source_dir} を検索中...")
    all_highlights = collect_all_highlights(source_dir)
    new_highlights = [h for h in all_highlights if h["ref"] not in processed_refs]

    words_count = sum(1 for h in new_highlights if h["kind"] == "word")
    sentences_count = sum(1 for h in new_highlights if h["kind"] == "sentence")
    print(f"📝 新規ハイライト: {len(new_highlights)} 件（単語/熟語: {words_count}件 / 文: {sentences_count}件）")

    if not new_highlights:
        print("✅ 新規ハイライトはありません。")
        return

    if args.dry_run:
        print("\n--- dry-run: 対象ハイライト一覧 ---")
        for h in new_highlights:
            label = "単語/熟語" if h["kind"] == "word" else "文→抽出"
            print(f"  [{label}] {h['text'][:60]}")
        return

    # AnkiConnect の有無を確認
    use_connect = anki_connect_available()
    if use_connect:
        print("🔗 AnkiConnect: 接続OK → リアルタイムで追加します")
        ensure_deck_and_model_connect()
    else:
        print(f"📦 Anki未起動 → .apkg ファイルを生成します: {APKG_OUTPUT.name}")

    added = 0
    skipped = 0
    failed = 0
    pending_cards: list[dict] = []  # apkg用バッファ

    for i, h in enumerate(new_highlights, 1):
        kind = h["kind"]
        ref = h["ref"]
        book = h["book"]

        if kind == "word":
            raw_word = STRIP_PUNCT_RE.sub("", h["text"]).strip().lower()
            print(f"[{i}/{len(new_highlights)}] {raw_word} ...", end=" ", flush=True)

            content = generate_card_for_word(raw_word, book, api_key)
            if content is None:
                print("失敗（Gemini APIエラー）✗")
                failed += 1
                processed_refs.add(ref)
                time.sleep(3)
                continue

            word = content.get("base_word", raw_word).lower().strip()

            if word in added_words or (use_connect and card_exists_connect(word)):
                print(f"スキップ（既存: {word}）")
                skipped += 1
            else:
                fields = _build_fields(word, content, book)
                if use_connect:
                    if add_card_connect(word, content, book):
                        print(f"追加済み ✓  {word} [{content.get('level','')}] {content.get('japanese','')}")
                        added += 1
                        added_words.add(word)
                    else:
                        print(f"失敗（Anki追加エラー）✗")
                        failed += 1
                else:
                    pending_cards.append(fields)
                    print(f"→ .apkg に追加 ✓  {word} [{content.get('level','')}] {content.get('japanese','')}")
                    added += 1
                    added_words.add(word)

            processed_refs.add(ref)
            time.sleep(3)

        elif kind == "sentence":
            print(f"[{i}/{len(new_highlights)}] 文→抽出: {h['text'][:50]}...", flush=True)
            items = extract_vocab_from_sentence(h["text"], book, api_key)

            if items is None:
                print("  → 失敗（Gemini APIエラー）✗")
                failed += 1
            elif not items:
                print("  → 抽出語なし（スキップ）")
                skipped += 1
            else:
                for item in items:
                    word = item.get("base_word", "").lower().strip()
                    if not word:
                        continue
                    if word in added_words or (use_connect and card_exists_connect(word)):
                        print(f"  → {word}: スキップ（既存）")
                        skipped += 1
                    else:
                        fields = _build_fields(word, item, book)
                        if use_connect:
                            if add_card_connect(word, item, book):
                                print(f"  → {word}: 追加済み ✓  [{item.get('level','')}] {item.get('japanese','')}")
                                added += 1
                                added_words.add(word)
                            else:
                                print(f"  → {word}: 失敗（Anki追加エラー）✗")
                                failed += 1
                        else:
                            pending_cards.append(fields)
                            print(f"  → {word}: .apkg に追加 ✓  [{item.get('level','')}] {item.get('japanese','')}")
                            added += 1
                            added_words.add(word)

            processed_refs.add(ref)
            time.sleep(4)

    # apkg モードの場合はファイル生成
    if not use_connect and pending_cards:
        build_apkg(pending_cards, APKG_OUTPUT)
        print(f"\n📦 .apkg ファイルを生成しました: {APKG_OUTPUT}")
        print(f"   → Ankiを起動してダブルクリック（またはファイル→インポート）でインポートできます")

    state["processed_refs"] = list(processed_refs)
    state["added_words"] = list(added_words)
    save_state(state)

    print(f"\n✅ 完了: 追加 {added}件 / スキップ {skipped}件 / 失敗 {failed}件")


if __name__ == "__main__":
    main()
