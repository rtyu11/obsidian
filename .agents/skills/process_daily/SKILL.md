---
name: Daily Processor
description: 「Inboxを整形して」がトリガーとなり、Daily/Inbox/の生メモ（md・JSONどちらも対応）を読んでIdeas・Tasks・Memoに振り分け、整形後にInboxファイルを削除する。
---

# Daily Processor Skill

## トリガー条件
- **「Inboxを整形して」**：Daily/Inbox/ の生メモを整形して各フォルダに振り分ける

---

## フォルダ構成

```
Daily/Inbox/      ← Google Keepからの生メモ（整形前・一時置き場）
                    ├── .md  形式（sync_keep.py 経由）
                    └── .json 形式（Google Takeout 経由）
Daily/Ideas/      ← 整形済みアイデア・気づき
  └── アイデアリスト.md
Daily/Tasks/      ← 整形済み課題
  └── 課題リスト.md
Daily/Memo/       ← 整形済み雑多メモ
  └── メモリスト.md
```

---

## 実行手順

### 1. Inbox の確認
- `Daily/Inbox/` 内のファイルを一覧取得する
- ファイルがなければ「Inboxにメモはありませんでした」と伝えて終了
- `.md` と `.json` の両方を対象にする

### 2. ファイル形式の判別と読み込み

#### .md ファイルの場合
ファイル名から分類する：
- `*-ideas*` → Ideas
- `*-tasks*` → Tasks
- `*-memo*` → Memo
- 判別できない場合はメモ内容から判断する

#### .json ファイルの場合（Google Takeout 形式）
各 JSON ファイルを Read ツールで読み込み、以下のフィールドを参照する：

```json
{
  "title": "メモのタイトル",
  "textContent": "メモ本文",
  "labels": [{"name": "ob-ideas"}],
  "isTrashed": false,
  "isArchived": false
}
```

- `isTrashed: true` または `isArchived: true` のノートはスキップする
- `labels` の `name` フィールドで分類する：
  - `ob-ideas` → Ideas
  - `ob-tasks` → Tasks
  - `ob-memo` → Memo
  - ラベルなし・判別不可 → メモ内容から判断する
- テキストは `textContent`（テキストノート）または `listContent`（チェックリスト）から取得する
- `listContent` の場合：`{"text": "項目", "isChecked": false}` の配列なので箇条書きに変換する

### 3. 各ノートへの追記

#### Ideas（Daily/Ideas/アイデアリスト.md）
```markdown
### [YYYY-MM-DD]
- [整形されたアイデア・気づき]
```

#### Tasks（Daily/Tasks/課題リスト.md）
```markdown
### [YYYY-MM-DD]
- [ ] [整形された課題]
```

#### Memo（Daily/Memo/メモリスト.md）
```markdown
### [YYYY-MM-DD]
- [整形された雑多メモ]
```

**整形ルール：**
- 音声入力の口語表現を自然な書き言葉に整える
- 意味は変えない。ユーザーの言葉を尊重する
- 箇条書きに整理する
- タグ（#）は付けない

### 4. Notes/Topics/ との照合（任意）
- Ideas や Tasks の内容が既存の `Notes/Topics/` のテーマと関連する場合は、会話の末尾で「〇〇のTopicsノートと関連しそうです」と提案する
- 自動で追記はしない。ユーザーが判断する

### 5. Inbox ファイルの削除
- 整形・追記が完了したら `Daily/Inbox/` のファイルを削除する
- 削除前に「整形完了しました。Inboxを削除します」と一言伝える

### 6. 完了報告
- 振り分けた件数を報告する
- 例：「アイデア3件、課題2件、メモ1件を整形しました」

---

## 禁止事項
- `Source/` 配下のファイルは編集・移動・削除すべて禁止
- ユーザーの意図を変えた整形をしない
- すべての返答・ノートは**日本語**で行う
