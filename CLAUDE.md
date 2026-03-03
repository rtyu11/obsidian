# Claude Code 向け指示書

このVaultで作業する際は、以下のルールを必ず守ること。

## フォルダ構造

```
Source/Kindle/    ← Kindleハイライト原文（編集禁止）
Source/OCR/       ← OCRハイライト原文（編集禁止）

Notes/Books/      ← 本1冊ごとのノート
Notes/Topics/     ← キーワード・ジャンルごとの横断ノート
```

## 禁止事項

- `/Source` 配下のファイルは**編集・移動・リネーム・削除すべて禁止**
- 新規フォルダの作成禁止（`Notes/Books` / `Notes/Topics` のみ使用）
- フォルダ構造の変更提案禁止

## 出力ルール

何かを出力・提案・保存する際は、必ず保存先フォルダを明示すること。

例：
- → 保存先：Notes/Books/
- → 保存先：Notes/Topics/

## 運用方針

- すべての返答・ノートは**日本語**で行う
- 読み書きの起点は常に `Notes/Books/` または `Notes/Topics/`
- `Source/` 配下は読み取り専用の参照元として扱う
