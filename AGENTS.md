# AI / Agent 共通指示

このVaultで作業するすべてのAI・Agent（Claude・Gemini・GPT等）は、作業開始前に必ずこのファイルを読むこと。

---

## 基本原則

- すべての返答・ノートは**日本語**で行う
- `Source/` 配下は**編集・移動・削除禁止**（原本扱い）
- 新規フォルダは作らない
- 既存ノートへの追記を優先する

---

## フォルダ構造（変更禁止）

```
Source/Kindle/    ← Kindleハイライト原文（自動同期・編集禁止）
Source/OCR/       ← OCR文字起こし原文（手動追加・編集禁止）

Notes/Books/      ← 本1冊ごとのノート（ハイライト要約＋気づき）
Notes/Topics/     ← キーワード・テーマごとの横断ノート

Daily/Inbox/      ← Google Keepからの生メモ（整形前・一時置き場）
Daily/Ideas/      ← 整形済みアイデア・気づき
Daily/Tasks/      ← 整形済み課題
Daily/Memo/       ← 整形済み雑多メモ
Daily/Quotes/     ← 名言・格言

Insights/         ← AIとの会話・課題解決で統合された思考の記録

LINE/images/      ← 本ページのLINE送付画像（book_highlighter用）
KindleInbox/      ← ScribePDF へのシンボリックリンク（scribe_inbox用）
```

---

## スキル一覧

タスクに応じて対応するスキルファイルを参照すること。

| トリガー | スキルファイル | 注意 |
|---------|-------------|------|
| 「OCR処理して」「LINE画像をOCRして」または本の表紙画像の添付 | `.agents/skills/book_highlighter/SKILL.md` | |
| 「更新分をまとめて」「〇〇について話したい」「Insightにまとめて」 | `.agents/skills/update_vault/SKILL.md` | |
| 「Inboxを整形して」 | `.agents/skills/process_inbox/SKILL.md` | |
| 「Scribeを処理して」「手書きメモを処理して」 | `.agents/skills/scribe_inbox/SKILL.md` | Claudeのビジョン機能が必要。Gemini等では動作しない場合あり |
| 「Keepを同期して」 | `.agents/scripts/sync_keep.py` | |

---

## 運用ルール詳細

詳細なルール（Google Keepラベル運用・Inbox整形フロー・KeepSidian/Git運用）は `VAULT_RULES.md` を参照すること。
