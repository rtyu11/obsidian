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
Source/KindleOCR/ ← Kindle OCR文字起こし原文（編集禁止）

Notes/Books/      ← 本1冊ごとのインデックスノート（タグ・著者リンク・Sourceリンクのみ。要約・気づきは書かない）

Memo/             ← 単発の考察・調べたこと・独立した知識メモ
Missions/Tasks/   ← 解決したい課題・やること・TODOを管理する拠点
Missions/Ideas/   ← 新しいビジネスアイデア・企画・着想を管理・育成する拠点
Quotes/           ← 名言・格言（名言集.md に追記。出典・日付を付与）

Insights/         ← AIとの会話で生まれた統合的な思考の記録・テーマ横断メモ（日付-テーマ.md形式または テーマ.md形式）
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
| `Missions/Tasks/` | 解決したい課題、システム構築、やること、TODO | アイデアの種、単なる感想 |
| `Missions/Ideas/` | 新しいビジネスアイデア・企画・着想・「やってみたい」 | 既存タスクの詳細化、単なるメモ |
| `Memo/` | 単発の考察・調べたこと・独立した知識メモ | 継続的なビジネスアイデア、タスク |
| `Quotes/` | 他者の言葉（名言・格言）。出典が他者のもの | 自分の気づき・考察（それはMemoかInsights） |
| `Insights/` | AIとの会話を経て深まった統合的な思考・複数の本にまたがるテーマ横断メモ | 単発メモ、未消化の気づき |
| `Journal/` | 日記・エッセイ・観察・空想・自分の考えや感情が入る文章。「私」が主語になるもの。境界が曖昧な時は `Journal/` を優先 | 知識メモ、他者の言葉 |
| `Notes/Books/` | タグ・著者リンク・Sourceリンク・関連Memo/Insightsへのリンクのみ（要約・気づきは書かない） | ハイライト要約・気づき・考察 |

### 知識の還流フロー（超重要）
このVaultの最終的な目的は、得られた知識を**「Missions（解決すべき実課題・新規ビジネス企画）」**に昇華させることである。
AIは、Source・Memo・Insightsの段階で思考を止めてはならない。会話のまとめや話題の提供を行う際は、常に以下のフローを意識し、**Missionsを最重要の出口として管理・参照**すること。
- **インプット**: Source (原本) / Memo (単発の調べ物)
- **抽象化・統合**: Insights (テーマ横断の考察)
- **アウトプット(出口)**: Tasks または Ideas (現在進行形の課題・育てたいアイデア)

---

## 作業開始プロトコル

トリガーワードを受け取ったら、**返答前に必ず対応するSKILL.mdを読み込んでから実行すること**。スキルファイルに書かれた手順に厳密に従う。

| トリガー | 読み込むファイル |
|---------|----------------|
| 「全部処理して」「一括処理して」 | `.agents/skills/all_inbox/SKILL.md` |
| 「Scribeを処理して」「手書きメモを処理して」 | `.agents/skills/scribe_inbox/SKILL.md` |
| 「LINEを処理して」「LINEを整形して」 | `.agents/skills/line_inbox/SKILL.md` |
| 「更新分をまとめて」「〇〇について話したい」「Insightにまとめて」 | `.agents/skills/update_vault/SKILL.md` |
| 「OCR処理して」「LINE画像をOCRして」または本の表紙画像の添付 | `.agents/skills/book_highlighter/SKILL.md` |
| 「Kindleをスキャンして」「Kindle OCRして」 | `.agents/skills/kindle_ocr/SKILL.md` |

---

## スキル一覧

タスクに応じて対応するスキルファイルを参照すること。

| トリガー | スキルファイル | 注意 |
|---------|-------------|------|
| 「全部処理して」「一括処理して」 | `.agents/skills/all_inbox/SKILL.md` | LINE→Scribe→更新分の順に一括処理。book_highlighterは含まない |
| 「LINEを処理して」「LINEを整形して」 | `.agents/skills/line_inbox/SKILL.md` | Claudeのビジョン機能が必要（画像処理時）。音声は事前に `python .agents/scripts/gemini_transcribe.py` が必要（GEMINI_API_KEY要設定） |
| 「OCR処理して」「LINE画像をOCRして」または本の表紙画像の添付 | `.agents/skills/book_highlighter/SKILL.md` | |
| 「更新分をまとめて」「〇〇について話したい」「Insightにまとめて」 | `.agents/skills/update_vault/SKILL.md` | |
| 「Scribeを処理して」「手書きメモを処理して」 | `.agents/skills/scribe_inbox/SKILL.md` | Claudeのビジョン機能が必要。Gemini等では動作しない場合あり |
| 「Kindleをスキャンして」「Kindle OCRして」 | `.agents/skills/kindle_ocr/SKILL.md` | GEMINI_API_KEY要設定。playwright・google-genai・pillowのインストールが必要 |

---

## 運用ルール詳細

詳細なルール（LINEメモ運用・整形フロー・Git運用）は `VAULT_RULES.md` を参照すること。

---

## 回答・会話のガイドライン

- **不必要な提案の禁止**：会話の末尾で毎回「ノートに記録しますか？」といった確認を投げかけないこと。記録が必要な場合はユーザーから指示がある。
- **ノートの勝手な更新の禁止**：ユーザーから明確な指示があるまで、AIが勝手にノートを作成・更新してはならない。
- **ユーザー主体のまとめ**：情報をまとめるときは、AIの意見主体ではなく、ユーザーの発言や「刺さった」と明示されたポイントを軸に構成すること。
- **簡潔な結び**：ユーザーからの問いに答えた後は、余計な追記や誘導をせず、簡潔に回答を終えること。
- **まとめ時の「出口」の意識**：ユーザーから「まとめて」と指示された際は、単にInsightsに保存するだけでなく、その内容が「Tasks（課題）」や「Ideas（企画）」に該当するかを判断し、優先的に `Missions/Tasks/` または `Missions/Ideas/` へ蓄積、あるいはリンク連携させること。
