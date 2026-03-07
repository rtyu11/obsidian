---
name: Inbox Processor
description: 「INBOXを整形して」がトリガーとなり、Daily/Inbox/内のKeepメモをラベルに従ってDailyフォルダへ振り分け、Inbox原本を削除する。
---

# Inbox Processor Skill

## トリガー条件
- **「INBOXを整形して」**：`Daily/Inbox/` 内のKeepメモをラベルに従ってDailyフォルダへ振り分け、Inbox原本を削除する

---

## フォルダ構成

```
Daily/Inbox/               ← KeepSidian同期後の一時置き場（整形前）
  _KeepSidianLogs/         ← KeepSidianのログ（削除禁止）
  media/                   ← 添付ファイル（削除禁止）
  [Keepのタイトル].md      ← KeepSidianが生成（ファイル名＝Keepのタイトルそのまま）

Daily/Ideas/          ← 整形済みアイデア・企画
  アイデアリスト.md
Daily/Tasks/          ← 整形済みタスク・課題
  課題リスト.md
Daily/Memo/           ← 整形済み雑多メモ
  メモリスト.md
```

---

## 実行手順

### 1. 文字化け修復（振り分けの前に必ず実行）

`Daily/Inbox/*.md` の本文が `繧/縺/繝` などの崩れた文字になることがある（KeepSidian経由の取り込みで発生しやすい）。
振り分けの前に次を実行して修復する：

```bash
python ".agents/scripts/repair_keep_mojibake.py" --apply
```

- 対象：`Daily/Inbox/*.md`（`.gitkeep` を除く）
- スクリプトが存在しない場合はスキップしてよい

### 2. 対象ファイルの検出
- `Daily/Inbox/` 内の `.md` ファイルを一覧取得する（`_KeepSidianLogs/`・`media/` フォルダは除外）
- ファイルがなければ「Inboxは空でした」と伝えて終了する

### 3. 各ファイルの振り分けルール

frontmatterの `labels` フィールドを確認し、なければファイルのタイトルと本文の内容から判断する。

| Keepラベル | 振り分け先ファイル | 内容の性質 |
|---|---|---|
| `ob-ideas` | `Daily/Ideas/アイデアリスト.md` | ビジネスアイデア・企画・着想 |
| `ob-tasks` | `Daily/Tasks/課題リスト.md` | やること・課題・タスク |
| `ob-memo` | `Daily/Memo/メモリスト.md` | 雑多なメモ・記録・気づき |
| ラベルなし（判断不能） | `Daily/Memo/メモリスト.md` | デフォルトはメモ扱い |

**本文が空のファイルは振り分けせずそのまま削除する。**

### 4. 振り分け先への追記フォーマット

振り分け先ファイルの末尾に以下の形式で追記する。
日付はfrontmatterの `GoogleKeepCreatedDate` から取得する（なければ今日の日付）。

```markdown
### [YYYY-MM-DD]
- [メモのタイトルまたは1行目]: [本文内容]
```

本文が複数行の場合は箇条書きで展開する：
```markdown
### [YYYY-MM-DD]
- [1行目の内容]
- [2行目の内容]
- [3行目の内容]
```

**整形ルール：**
- 箇条書き入力は適切な書き言葉に直す（ただし意味は変えない）
- 語順は変えない。ユーザーの表現を尊重する
- タグ（`#`）はつけない

### 5. Inbox原本の削除
- 振り分け完了後、`Daily/Inbox/` の元ファイルを削除する
- **`_KeepSidianLogs/` フォルダは削除しない**

### 6. 完了報告
- 処理したファイル数と振り分け先を一覧で報告する
- 本文空で削除したファイルがあれば合わせて報告する

---

## 禁止事項
- `Source/` 配下のファイルは編集・移動・削除すべて禁止
- タグを勝手につけない
- すべての返答は**日本語**で行う
