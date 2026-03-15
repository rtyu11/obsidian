---
name: Scribe Inbox Processor
description: 「Scribeを処理して」または「手書きメモを処理して」がトリガーとなり、KindleInbox/内の未処理PDFをClaudeのビジョン機能で読み取り、コンテンツ種別を分類して適切なフォルダへ保存する。
---

# Scribe Inbox Processor Skill

## トリガー条件
- **「Scribeを処理して」**：`KindleInbox/` 内の未処理PDFをビジョン解析し、コンテンツ種別に応じたフォルダへ保存する
- **「手書きメモを処理して」**：同上

---

## フォルダ構成

```
KindleInbox/              ← Google Drive ScribePDF へのシンボリックリンク（削除・編集禁止）
  [ファイル名].pdf        ← Scribeで書き出した手書きPDF

Source/OCR/               ← コード・図変換結果の保存先（新規ファイル追加のみ・編集禁止）
Ideas/                    ← アイデア・気づきメモの保存先
Tasks/                    ← タスク・課題メモの保存先
Memo/                     ← 雑多メモの保存先
Notes/Books/              ← 本の読書メモの保存先
Insights/                 ← 深い考察・思考の保存先
```

---

## 実行手順

### 1. 前提確認

`KindleInbox/` フォルダが存在するか確認する。

- **存在しない場合**：以下を伝えて終了する。
  > 「KindleInboxフォルダが見つかりません。管理者権限の cmd.exe で以下を実行してください：
  > `mklink /D "C:\Users\111r9\OneDrive\ドキュメント\Obsidian Vault\obsidian\KindleInbox" "G:\マイドライブ\ScribePDF"`」

- **PDFファイルが0件の場合**：「KindleInboxに未処理のPDFが見つかりませんでした」と伝えて終了する。

### 2. 未処理PDFの検出

`KindleInbox/` 内のPDFファイルを一覧取得する。
処理済み判定は `.agents/scripts/scribe_processed_log.txt` に記録されたファイル名で行う（ファイル名リネームは使わない）。

処理済みログの確認方法：
```python
python -c "
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
log = os.path.join(os.environ['USERPROFILE'], 'OneDrive', 'ドキュメント', 'Obsidian Vault', 'obsidian', '.agents', 'scripts', 'scribe_processed_log.txt')
processed = set()
if os.path.exists(log):
    with open(log, encoding='utf-8') as f:
        processed = set(line.strip() for line in f if line.strip())
folder = os.path.join(os.environ['USERPROFILE'], 'OneDrive', 'ドキュメント', 'Obsidian Vault', 'obsidian', 'KindleInbox')
files = [f for f in os.listdir(folder) if f.endswith('.pdf') and f not in processed]
print('未処理PDF:', files)
"
```

ログに記録されていないPDFを処理対象とする。

### 3. ビジョン解析と種別分類

各PDFに対して以下を実施する。

#### 3-1. ビジョン解析（高速化版）

**ブラウザは使わない。** 以下のPythonコマンドでPDFを一時PNG画像に変換し、`Read`ツールで直接読み取る。

**注意：日本語パスをコマンドライン引数に渡すとエンコードエラーになる。** 必ず以下の方式（`os.listdir` でファイルを特定してPythonコード内でパスを組み立てる）を使うこと。

```python
python -c "
import fitz, os
log = os.path.join(os.environ['USERPROFILE'], 'OneDrive', 'ドキュメント', 'Obsidian Vault', 'obsidian', '.agents', 'scripts', 'scribe_processed_log.txt')
processed = set()
if os.path.exists(log):
    with open(log, encoding='utf-8') as lf:
        processed = set(line.strip() for line in lf if line.strip())
folder = os.path.join(os.environ['USERPROFILE'], 'OneDrive', 'ドキュメント', 'Obsidian Vault', 'obsidian', 'KindleInbox')
files = [f for f in os.listdir(folder) if f.endswith('.pdf') and f not in processed]
if files:
    pdf_path = os.path.join(folder, files[0])
    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=150)
        out = os.path.join(os.environ['TEMP'], f'scribe_page_{i}.png')
        pix.save(out)
        print(out)
    print(f'Total pages: {len(doc)}')
"
```

複数PDFがある場合は `files[0]` を `files[1]` 等に変えて繰り返す。
出力されたPNGパスを `Read` ツールで読み取り、手書き内容を解釈する。
複数ページがある場合は全ページ分繰り返す。
一時画像は処理後に削除不要（次回上書きされる）。

#### 3-1-b. 書き起こし・整形ルール

**原則：意味が通じる文章にすることを最優先とする。ただし著者の言い回し・文体は保持する。**

- **単なる文字起こしをしてはいけない**。前後の文脈・思考の流れ・メモ全体のテーマを読み取り、意味が通じる文章に整形する
- 手書きが崩れていて読み取りが難しい箇所は、文脈・前後の内容・テーマから推測して自然な日本語に補正する
- 著者独自の言い回し・文体・口語表現はそのまま保持する（整形しすぎない）
- 記号・強調（丸囲み・矢印・下線・囲み枠など）は Markdown で忠実に再現する（例：丸囲み → `○〇`、強調 → `**太字**`、矢印 → `→`）
- ハイライト・強調されている箇所は `**太字**` で反映する
- メモの意図（思考整理なのか、観察なのか、空想なのか）を読み取り、それが伝わるよう構造化する
- 意味が明確に通じている文は一切触らない
- 補正・推測した箇所が多い場合は、ノート末尾に「※読み取りが難しい箇所は文脈から補正しています」と注記する

#### 3-2. コンテンツ種別の分類

以下の基準で**1つの種別**に分類する。判断が難しい場合は最も近いものを選ぶ。

| 種別 | 判断基準 | 保存先 |
|---|---|---|
| **UIワイヤーフレーム** | 画面レイアウト・ボタン・入力フォーム・ナビゲーションの手書き設計図（デジタル実装を前提とした図） | `Source/OCR/` |
| **フロー図・マインドマップ** | 実装・設計目的の矢印フロー図・分岐ツリー（デジタル実装を前提としたもののみ） | `Source/OCR/` |
| **アイデアメモ** | 新しいビジネスアイデア・企画・着想・発見 | `Ideas/` |
| **タスクメモ** | やること・課題・解決したい問題のリスト | `Tasks/` |
| **読書メモ** | 本のタイトルや著者名が明記、または本の内容についての気づき | `Notes/Books/` |
| **思考・考察ノート** | 深い分析・問いの探求・複数テーマにまたがる考察。手書きのマインドマップ・思考整理図も含む | `Insights/` |
| **日記・エッセイ・観察文** | 日常の観察・体験・空想・感情・自分の考えが入る文章。「私」が主語になるもの。事実と創作が混在していてもよい | `Journal/` |
| **雑多メモ** | 上記いずれにも当てはまらないメモ | `Memo/` |

> **注意**：`Source/OCR/` に入るのはデジタルコード（React/Mermaid等）への変換が目的の図のみ。手書きの思考マップ・マインドマップは `Insights/` へ。日記・エッセイ・観察文は `Journal/` へ。境界が曖昧な時は `Journal/` を優先。

### 4. 種別ごとの変換・保存

#### 【UIワイヤーフレーム】→ React + Tailwind CSS コンポーネント

保存先：`Source/OCR/[ファイル名ベース]-[YYYY-MM-DD].md`

```markdown
# [コンポーネント名または用途]

作成日: YYYY-MM-DD
種別: UIワイヤーフレーム

## 手書きメモ（原文）

[手書きの内容をテキストで描写する]

## 変換コード（React + Tailwind CSS）

```tsx
[変換したReactコンポーネントコード]
```
```

---

#### 【フロー図・マインドマップ】→ Mermaid コード

保存先：`Source/OCR/[ファイル名ベース]-[YYYY-MM-DD].md`

```markdown
# [図の内容を表すタイトル]

作成日: YYYY-MM-DD
種別: フロー図 / マインドマップ

## 手書きメモ（原文）

[手書きの内容をテキストで描写する]

## Mermaidコード

```mermaid
[変換したMermaidコード]
```
```

---

#### 【アイデア / タスク / 雑多メモ】→ Markdown テキスト

**判定基準**（process_inbox スキルと同じ基準を適用）：
- **3行以下かつ箇条書き** → 既存リストファイルに追記
- **4行以上または構造化あり** → 独立ファイルを作成

**追記フォーマット**（`Ideas/アイデアリスト.md` / `Tasks/課題リスト.md` / `Memo/メモリスト.md` の末尾）：
```markdown
### YYYY-MM-DD
- [メモの内容]
```

**独立ファイルフォーマット**（`Ideas/` / `Tasks/` / `Memo/` に保存）：
```markdown
---
date: YYYY-MM-DD
tags: [カテゴリタグ, トピックタグ1, トピックタグ2]
source: scribe
原文PDF: [[ファイル名.pdf]]
---

# [タイトル]

[手書き内容を構造化したMarkdown]
```

タグ：`ideas` / `tasks` / `memo` ＋ 内容キーワード2〜4個

> **原文PDFリンク**：独立ファイルには必ず `原文PDF:` フィールドを付与し、処理元PDFを `[[ファイル名.pdf]]` 形式で記載する。意味が分からなくなった時に原文を参照できるようにするため。

---

#### 【読書メモ】→ Books ノートへの追記

本のタイトルを特定し、`Notes/Books/[本のタイトル].md` の `## 気づき` セクションに追記する。

- **対応するBooksノートが存在しない場合**：`Daily/Ideas/アイデアリスト.md` に追記し、「Booksノートが未作成のためIdeasに保存しました」と報告する。

追記フォーマット：
```markdown
### YYYY-MM-DD（手書きメモより）
[手書きの気づき内容]
```

---

#### 【思考・考察ノート】→ Insights

保存先：`Insights/[YYYY-MM-DD]-[テーマ].md`

```markdown
---
date: YYYY-MM-DD
tags: [キーワードタグ1, キーワードタグ2, キーワードタグ3]
source: scribe
原文PDF: [[ファイル名.pdf]]
関連: [[関連するノートがあれば]]
---

# [テーマ・課題名]

#キーワードタグ1 #キーワードタグ2

---

## 課題・問い
[手書きの問いや課題]

---

## 気づき・考察
[手書きの内容を構造化したMarkdown]

---

## 次のアクション
- [ ] [手書きに含まれるアクションがあれば]
```

**原文PDFリンクルール（Insights）**：
- frontmatterの `原文PDF:` に、処理元のPDFファイル名を `[[ファイル名.pdf]]` 形式で必ず記載する
- 整形後の文章が読み取り誤りを含む可能性があるため、原文PDFに立ち返れるようにすることが目的
- PDFはKindleInbox/にそのまま残るため、いつでも参照できる

**タグ付けルール（Insights）**：
- frontmatterの `tags:` に内容キーワード2〜4個をリスト形式で記載
- 本文冒頭にも `#タグ名` 形式で同じタグを記載（Obsidianのタグ検索に対応）
- 既存の `Notes/Topics/` や `Notes/Books/` に関連するノートがあれば `関連:` フィールドに `[[ノート名]]` で記載する
- 既存タグ一覧（AGENTS.md / MEMORY.md参照）から近いものを優先して使う

---

#### 【日記・エッセイ・観察文】→ Journal

保存先：`Journal/[YYYY-MM-DD]-[タイトル].md`

```markdown
---
date: YYYY-MM-DD
tags: [キーワードタグ1, キーワードタグ2]
source: scribe
原文PDF: [[ファイル名.pdf]]
---

# [タイトル]

#キーワードタグ1 #キーワードタグ2

[手書き内容を整形したMarkdown（セクション分けは内容に応じて）]
```

**原文PDFリンクルール（Journal）**：
- frontmatterの `原文PDF:` に、処理元のPDFファイル名を `[[ファイル名.pdf]]` 形式で必ず記載する
- 整形後の文章が意味不明に見える箇所があっても、原文PDFで確認できるようにすることが目的
- PDFはKindleInbox/にそのまま残るため、いつでも参照できる

**タグ付けルール（Journal）**：
- frontmatterの `tags:` に内容キーワード2〜4個を記載
- 本文冒頭にも `#タグ名` 形式で同じタグを記載
- 観察・空想・日記など文章のトーンを表すタグも付与する（例：#観察 #空想 #日常）

---

### 5. 処理済みマーカーの付与

各PDFの処理が完了したら、ファイル名を `.agents/scripts/scribe_processed_log.txt` に追記する。
KindleInbox内のファイルはリネームしない（Google Driveシンボリックリンク経由では二重ファイルが生じるため）。

```python
python -c "
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
log = os.path.join(os.environ['USERPROFILE'], 'OneDrive', 'ドキュメント', 'Obsidian Vault', 'obsidian', '.agents', 'scripts', 'scribe_processed_log.txt')
filename = '[処理したPDFファイル名をここに入れる]'
with open(log, 'a', encoding='utf-8') as f:
    f.write(filename + '\n')
print('Logged:', filename)
"
```

これにより次回実行時に再処理されない。

### 6. 完了報告

```
【Scribe処理完了】
処理したPDF: N件

【UIワイヤーフレーム → Reactコード変換】N件
  - ファイル名 → Source/OCR/ファイル名.md

【フロー図 → Mermaid変換】N件
  - ファイル名 → Source/OCR/ファイル名.md

【リスト型追記】N件
  - ファイル名 → Daily/Ideas/アイデアリスト.md など

【独立ファイル作成】N件
  - ファイル名 → Daily/Ideas/ファイル名.md など

【読書メモ追記】N件
  - ファイル名 → Notes/Books/本のタイトル.md

【Insights保存】N件
  - ファイル名 → Insights/YYYY-MM-DD-テーマ.md
```

---

## 禁止事項
- `KindleInbox/` 内のPDFを削除・リネームしない（ログファイルへの記録のみ行う）
- `Source/` 配下の既存ファイルの内容を編集しない（新規ファイル追加のみ可）
- 新規フォルダを作成しない
- コード変換時にAIの主観的解釈を加えない。手書きの意図を忠実に変換する
- すべての返答・ノートは**日本語**で行う（コードブロック内のコード自体は除く）
