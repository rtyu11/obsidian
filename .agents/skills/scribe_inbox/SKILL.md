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
  [ファイル名].pdf        ← Scribeで書き出した手書きPDF（未処理）
  _processed_[名前].pdf  ← 処理済みPDF（スキップ対象）

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
ファイル名が `_processed_` で始まるものは処理済みとしてスキップする。

### 3. ビジョン解析と種別分類

各PDFに対して以下を実施する。

#### 3-1. ビジョン解析（高速化版）

**ブラウザは使わない。** 以下のPythonコマンドでPDFを一時PNG画像に変換し、`view_file`ツールで直接読み取る。

```powershell
python -c "
import fitz, sys, os
doc = fitz.open(sys.argv[1])
for i, page in enumerate(doc):
    pix = page.get_pixmap(dpi=150)
    out = os.path.join(os.environ['TEMP'], f'scribe_page_{i}.png')
    pix.save(out)
    print(out)
" "[PDFの絶対パス]"
```

出力されたPNGパスに対して `view_file` ツールで画像を読み取り、手書き内容を解釈する。
複数ページがある場合は全ページ分繰り返す。
一時画像は処理後に削除不要（次回上書きされる）。

#### 3-2. コンテンツ種別の分類

以下の基準で**1つの種別**に分類する。判断が難しい場合は最も近いものを選ぶ。

| 種別 | 判断基準 | 保存先 |
|---|---|---|
| **UIワイヤーフレーム** | 画面レイアウト・ボタン・入力フォーム・ナビゲーションの手書き設計図 | `Source/OCR/` |
| **フロー図・マインドマップ** | 矢印でつながれたフロー図、ノード構造のマインドマップ、分岐ツリー | `Source/OCR/` |
| **アイデアメモ** | 新しいビジネスアイデア・企画・着想・発見 | `Ideas/` |
| **タスクメモ** | やること・課題・解決したい問題のリスト | `Tasks/` |
| **読書メモ** | 本のタイトルや著者名が明記、または本の内容についての気づき | `Notes/Books/` |
| **思考・考察ノート** | 深い分析・問いの探求・複数テーマにまたがる考察 | `Insights/` |
| **雑多メモ** | 上記いずれにも当てはまらないメモ | `Memo/` |

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
---

# [タイトル]

[手書き内容を構造化したMarkdown]
```

タグ：`ideas` / `tasks` / `memo` ＋ 内容キーワード2〜4個

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
# [テーマ・課題名]

日付: YYYY-MM-DD
source: scribe
関連: [[関連するノートがあれば]]

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

---

### 5. 処理済みマーカーの付与

各PDFの処理が完了したら、ファイル名の先頭に `_processed_` を付けてリネームする。

例：`sketch-2026-03-12.pdf` → `_processed_sketch-2026-03-12.pdf`

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
- `KindleInbox/` 内のPDFを削除しない（`_processed_` プレフィックスを付けるのみ）
- `Source/` 配下の既存ファイルの内容を編集しない（新規ファイル追加のみ可）
- 新規フォルダを作成しない
- コード変換時にAIの主観的解釈を加えない。手書きの意図を忠実に変換する
- すべての返答・ノートは**日本語**で行う（コードブロック内のコード自体は除く）
