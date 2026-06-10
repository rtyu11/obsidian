---
name: Kindle Vocab → Anki
description: Source/Kindle/*.md の英語ハイライトを解析し、Gemini APIで定義・例文・日本語訳・覚え方を生成してAnkiのKindleVocabデッキにカードを追加する。単語/熟語は直接カード化、一文ハイライトはGeminiが重要語彙を自動抽出する。
---

# Kindle Vocab → Anki

## トリガー条件
- 「洋書の単語をAnkiに取り込んで」
- 「KindleVocabを更新して」
- 「英単語をAnkiに追加して」
- 「Kindle英単語を登録して」

## 前提条件

1. **GEMINI_API_KEY** 環境変数が設定済みであること
2. **Anki**（ankiweb.net版）が起動していること
3. **AnkiConnect** アドオンがインストールされていること（コード: `2055492159`）
4. `pip install requests` が実行済みであること
5. KindleプラグインでSource/Kindle/に英語本のハイライトが同期済みであること

## 実行方法

```bash
# 通常実行（新規ハイライトのみ差分追加）
python .agents/scripts/kindle_vocab_anki.py

# 確認のみ（カードを追加しない）
python .agents/scripts/kindle_vocab_anki.py --dry-run

# 全ハイライトを最初から再取り込み
python .agents/scripts/kindle_vocab_anki.py --reset
```

## ハイライトの取り込みルール

| ハイライトの種類 | 処理 |
|----------------|------|
| 1〜3語（単語・熟語） | そのままカード化 |
| 4語以上（文・フレーズ） | GeminiがキーとなるR語彙・熟語を1〜4件抽出してカード化 |
| 同じ単語が既にAnkiにある | スキップ（重複追加しない） |
| 日本語のみのハイライト | 無視 |

## 生成されるAnkiカードの内容

```
[表] verbatim  [C1]
─────────────────────────────
[裏] in exactly the same words as were used originally

     "She quoted him verbatim."

     ▶ 日本語を見る
     → 逐語的に
     → 言葉を変えずにそのまま伝えること

     💡 "verb" (word) + "-atim" (ラテン語) = 単語そのまま

     📖 Ascendance of a Bookworm: Part 5
```

## 処理の流れ

1. `Source/Kindle/*.md` を全件スキャン
2. 前回処理済みのハイライト（`kindle_vocab_anki_state.json`で管理）を除外
3. 単語/熟語: Gemini API でカード内容を生成（定義・例文・日本語訳・覚え方・CEFRレベル）
4. 文ハイライト: Gemini API で語彙・熟語を抽出 → 各々のカード内容を生成
5. AnkiConnect 経由で `KindleVocab` デッキにカードを追加
6. 処理済みrefを state.json に保存（次回は差分のみ処理）

## 出力先

- **Anki デッキ**: `KindleVocab`
- **タグ**: `kindle`, `vocabulary`
- **ステートファイル**: `.agents/scripts/kindle_vocab_anki_state.json`

## 注意事項

- Gemini API の無料枠レート制限のため、1単語あたり約3〜4秒かかる
- AnkiはスクリプT実行中も起動したままにしておくこと
- `--reset` を使うと全単語を再処理するため、既存Ankiカードとの重複チェックは行われる（同じカードが2枚になることはない）
