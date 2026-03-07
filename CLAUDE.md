# Claude Code 向け指示書

このVaultで作業する際は、以下のルールを必ず守ること。

## フォルダ構造

```
Source/Kindle/    ← Kindleハイライト原文（編集禁止）
Source/OCR/       ← OCRハイライト原文（編集禁止）

Notes/Books/      ← 本1冊ごとのノート
Notes/Topics/     ← キーワード・ジャンルごとの横断ノート

Daily/Inbox/      ← Google Keepからの生メモ（整形前・一時置き場）
Daily/Ideas/      ← 整形済みアイデア・気づき
Daily/Tasks/      ← 整形済み課題
Daily/Memo/       ← 整形済み雑多メモ

Insights/         ← AIとの会話・課題解決で統合された思考の記録
```

## Google Keep ラベル運用

スマホでの音声入力メモは Google Keep を使い、以下のラベルで分類する：

| ラベル名 | 用途 | 整形後の行き先 |
|---|---|---|
| `ob-ideas` | 気づき・発見・本の感想すべて | Daily/Ideas/ |
| `ob-tasks` | 解決したい課題・やること | Daily/Tasks/ |
| `ob-memo` | 雑多・どれでもない | Daily/Memo/ |

## Inbox 整形フロー

1. PC の keep.google.com からラベル別にメモをコピー
2. `Daily/Inbox/` に貼り付け（ファイル名例：`2026-03-07-ideas.md`）
3. Claude Code に「Inboxを整形して」と指示
4. Claude が各フォルダに振り分け・追記
5. `Daily/Inbox/` のファイルは整形後に削除

## Insights フロー

- AIと会話して課題を深掘りした成果を `Insights/` に保存
- ファイル名例：`2026-03-07-集中力の課題.md`
- Notes/Topics/ や Daily/Tasks/ の内容と紐づけて記録する

## 禁止事項

- `/Source` 配下のファイルは**編集・移動・リネーム・削除すべて禁止**
- 上記フォルダ以外の新規フォルダ作成禁止
- フォルダ構造の変更提案禁止

## 出力ルール

何かを出力・提案・保存する際は、必ず保存先フォルダを明示すること。

例：
- → 保存先：Notes/Books/
- → 保存先：Daily/Tasks/
- → 保存先：Insights/

## 運用方針

- すべての返答・ノートは**日本語**で行う
- `Source/` 配下は読み取り専用の参照元として扱う
- メモは増やしすぎない。既存ノートへの追記を優先する
