# AI / Agent 共通指示

このVaultで作業するすべてのAI・Agent（Claude・Gemini・GPT等）は、作業開始前に必ずこのファイルを読むこと。

---

## 基本原則

- すべての返答・ノートは**日本語**で行う
- `Source/` 配下は**編集・移動・削除禁止**（原本扱い）
- 新規フォルダは作らない
- 既存ノートへの追記を優先する

---

## フォルダ構造と役割（変更禁止）

```
Source/Kindle/    ← Kindleハイライト原文（自動同期・編集禁止）
Source/OCR/       ← OCR文字起こし原文（手動追加・編集禁止）

Notes/Books/      ← 本1冊ごとのノート（ハイライト要約＋気づき）
Notes/Topics/     ← キーワード・テーマごとの横断ノート（複数の本にまたがる気づき）

Ideas/            ← アイデア・企画・着想（LINEから・会話中・本からを問わず集約）
Tasks/            ← 課題・やること（LINEから・会話中・本からを問わず集約）
Memo/             ← 雑多メモ・気づき・単発の考察（独立トピックとして残す価値があるもの）
Quotes/           ← 名言・格言（名言集.md に追記。出典・日付を付与）

Insights/         ← AIとの会話で生まれた統合的な思考の記録（日付-テーマ.md形式）
Journal/          ← 日記・エッセイ・日常の観察・空想・自分の考えや感情が入る文章（日付-タイトル.md形式）

LINE/             ← Make.comが同期するLINEテキストメモ
LINE/images/      ← Make.comが同期するLINE送付画像（book_highlighter / line_inbox用）
LINE/pdfs/        ← LINEから送付されたPDF（line_inbox用）
LINE/audio/       ← 音声ファイル（処理対象外・手動転記要）
KindleInbox/      ← ScribePDF へのシンボリックリンク（scribe_inbox用）
```

### 各フォルダの使い分け

| フォルダ | 入れるもの | 入れないもの |
|---------|-----------|------------|
| `Ideas/` | 新しいビジネスアイデア・企画・着想・「やってみたい」 | 既存タスクの細分化、単なるメモ |
| `Tasks/` | 解決したい課題・やること・TODO | アイデアの種、感想 |
| `Memo/` | 単発の考察・調べたこと・独立した知識メモ | 継続的なアイデア、タスク |
| `Quotes/` | 他者の言葉（名言・格言）。出典が他者のもの | 自分の気づき・考察（それはIdeasかMemo） |
| `Insights/` | AIとの会話を経て深まった統合的な思考 | 単発メモ、未消化の気づき |
| `Journal/` | 日記・エッセイ・観察・空想・自分の考えや感情が入る文章。「私」が主語になるもの。境界が曖昧な時は `Journal/` を優先 | 知識メモ、他者の言葉 |
| `Notes/Books/` | 本ごとの要約と自分の気づき | テーマ横断の考察 |
| `Notes/Topics/` | 複数の本にまたがるテーマ・概念の横断整理 | 1冊だけに関係する内容 |

---

## 作業開始プロトコル

トリガーワードを受け取ったら、**返答前に必ず対応するSKILL.mdを読み込んでから実行すること**。スキルファイルに書かれた手順に厳密に従う。

| トリガー | 読み込むファイル |
|---------|----------------|
| 「Scribeを処理して」「手書きメモを処理して」 | `.agents/skills/scribe_inbox/SKILL.md` |
| 「LINEを処理して」「LINEを整形して」 | `.agents/skills/line_inbox/SKILL.md` |
| 「更新分をまとめて」「〇〇について話したい」「Insightにまとめて」 | `.agents/skills/update_vault/SKILL.md` |
| 「OCR処理して」「LINE画像をOCRして」または本の表紙画像の添付 | `.agents/skills/book_highlighter/SKILL.md` |

---

## スキル一覧

タスクに応じて対応するスキルファイルを参照すること。

| トリガー | スキルファイル | 注意 |
|---------|-------------|------|
| 「LINEを処理して」「LINEを整形して」 | `.agents/skills/line_inbox/SKILL.md` | Claudeのビジョン機能が必要（画像処理時）。音声は事前に `python .agents/scripts/gemini_transcribe.py` が必要（GEMINI_API_KEY要設定） |
| 「OCR処理して」「LINE画像をOCRして」または本の表紙画像の添付 | `.agents/skills/book_highlighter/SKILL.md` | |
| 「更新分をまとめて」「〇〇について話したい」「Insightにまとめて」 | `.agents/skills/update_vault/SKILL.md` | |
| 「Scribeを処理して」「手書きメモを処理して」 | `.agents/skills/scribe_inbox/SKILL.md` | Claudeのビジョン機能が必要。Gemini等では動作しない場合あり |

---

## 運用ルール詳細

詳細なルール（LINEメモ運用・整形フロー・Git運用）は `VAULT_RULES.md` を参照すること。
