---
name: All Inbox Processor
description: 「全部処理して」または「一括処理して」がトリガーとなり、LINE処理 → Scribe処理 → 更新分まとめ の順にすべてのInboxを一括処理する。各ステップで対象ファイルがなければスキップする。
---

# All Inbox Processor Skill

## トリガー条件
- **「全部処理して」** または **「一括処理して」**：LINE・Scribe・Kindleの全Inboxを順番に処理する

---

## 実行順序

以下の順番で各スキルを実行する。**必ず順番通りに実行すること（並列不可）。**

```
① LINE処理      → line_inbox SKILL.md に従い LINE/ を処理
② Scribe処理    → scribe_inbox SKILL.md に従い KindleInbox/ を処理
③ 更新分まとめ  → update_vault SKILL.md に従い Source/ を処理
```

---

## 手順

### ステップ①：LINE処理

**作業前確認：**
- `LINE/` 直下に未処理の `.md` ファイルがあるか
- `LINE/images/` に `_processed_` プレフィックスなしの画像ファイルがあるか
- `LINE/pdfs/` が存在し、未処理PDFがあるか
- `LINE/audio/` に未処理の音声ファイルがあるか

**対象ファイルが1件以上ある場合：** `.agents/skills/line_inbox/SKILL.md` の手順をすべて実行する。

**対象ファイルが0件の場合：** 「LINE/：未処理ファイルなし（スキップ）」と記録して次へ進む。

---

### ステップ②：Scribe処理

**作業前確認：**
- `KindleInbox/` フォルダが存在するか
- `KindleInbox/` 内に `_processed_` プレフィックスなしのPDFファイルがあるか

**PDFが1件以上ある場合：** `.agents/skills/scribe_inbox/SKILL.md` の手順をすべて実行する。

**KindleInboxが存在しない、またはPDFが0件の場合：** 「KindleInbox/：未処理PDFなし（スキップ）」と記録して次へ進む。

---

### ステップ③：更新分まとめ

**作業前確認：**
- `Source/Kindle/` または `Source/OCR/` に、対応するBooksノートがない、またはハイライト数が増えた本があるか

確認方法（スクリプトがある場合）：
```powershell
cd "c:\Users\111r9\OneDrive\ドキュメント\Obsidian Vault\obsidian"
.\.agents\scripts\detect_updates.ps1
```

**更新対象の本が1冊以上ある場合：** `.agents/skills/update_vault/SKILL.md` の「更新分をまとめて」手順をすべて実行する。

**更新対象なしの場合：** 「Source/：新しい更新なし（スキップ）」と記録して完了報告へ進む。

---

## 完了報告フォーマット

```
【一括処理完了】

① LINE処理
  [line_inbox の完了報告をそのまま記載 / スキップの場合は「未処理ファイルなし」]

② Scribe処理
  [scribe_inbox の完了報告をそのまま記載 / スキップの場合は「未処理PDFなし」]

③ 更新分まとめ
  [update_vault の完了報告をそのまま記載 / スキップの場合は「新しい更新なし」]
```

---

## 注意事項
- `book_highlighter` は画像の直接添付が必要なため、このスキルには含まない
- 各スキルの禁止事項はそれぞれのSKILL.mdに従う
- すべての返答・ノートは**日本語**で行う
