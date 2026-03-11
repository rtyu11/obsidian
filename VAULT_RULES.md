# Vault 運用ルール

## 目的

KindleハイライトやOCRハイライトを素材に、AIとの会話を通じて自分の気づきを蓄積していくための知識データベースを構築・維持する。

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

Insights/         ← AIとの会話・課題解決で統合された思考の記録
```

---

## 絶対ルール

### 1. /Source 配下は原本扱い
- **編集しない**
- **移動しない**
- **リネームしない**
- **削除しない**

### 2. ノートの保存先
- 本についてのノート → `Notes/Books/[本のタイトル].md`
- テーマ・タグ横断ノート → `Notes/Topics/[テーマ名].md`
- アイデア・気づき → `Daily/Ideas/アイデアリスト.md` に追記
- 課題・やること → `Daily/Tasks/課題リスト.md` に追記
- 雑多メモ → `Daily/Memo/メモリスト.md` に追記
- 会話・深掘り成果 → `Insights/[日付-テーマ].md`

### 3. 新規フォルダは作らない
上記フォルダのみ使用。それ以外のフォルダ作成・変更提案は禁止。

### 4. 出力時は保存先を明示する
AIが何かを出力・提案する際は、必ず保存先を明示すること。

例：
- → 保存先：Notes/Books/
- → 保存先：Daily/Tasks/
- → 保存先：Insights/

### 5. すべての返答・ノートは日本語で行う

### 6. メモは増やしすぎない
既存ノートへの追記を優先する。

---

## Google Keep ラベル運用

スマホでの音声入力メモは Google Keep を使い、以下のラベルで分類する：

| ラベル名 | 用途 | 整形後の行き先 |
|---|---|---|
| `ob-ideas` | 気づき・発見・本の感想すべて | `Daily/Ideas/アイデアリスト.md` |
| `ob-tasks` | 解決したい課題・やること | `Daily/Tasks/課題リスト.md` |
| `ob-memo` | 雑多・どれでもない | `Daily/Memo/メモリスト.md` |

---

## Inbox 整形フロー

1. KeepSidianが起動時に自動で `Daily/Inbox/` へメモを取り込む
2. 「Inboxを整形して」と指示する
3. AIがラベルに従い各Dailyフォルダへ振り分け・追記する
4. `Daily/Inbox/` の元ファイルは整形後に削除する

---

## 運用フロー（読書ノート）

| 段階 | 内容 | 保存先 |
|------|------|--------|
| 段階1 | Kindle/OCRハイライトを素材として蓄積 | Source/（自動・手動） |
| 段階2 | 「更新分をまとめて」でBooksノート作成・更新 | Notes/Books/ |
| 段階3 | 「〇〇について話したい」でAIと対話し気づきを追記 | Notes/Books/ または Notes/Topics/ |
| 段階4 | 共通テーマが2冊以上になったらTopicsノートで横断整理 | Notes/Topics/ |

---

## Insights フロー

- AIと会話して課題を深掘りした成果を `Insights/` に保存する
- ファイル名例：`2026-03-07-集中力の課題.md`
- Notes/Topics/ や Daily/Tasks/ の内容と紐づけて記録する

---

## 会話スタイル

- AIは自分の意見・解釈を積極的に述べてよい
- 会話の末尾に毎回質問を投げかける必要はない
- ユーザーが「まとめて」「ノートに残して」と言ったら気づきをノートに追記する

---

## KeepSidian / Git 運用ルール（2026-03-07更新）

### 前提
- Google Keep連携はKeepSidianを使う。
- KeepSidian設定: `Save location = Daily/Inbox`。
- 同期タイミング: `Sync on startup = ON`、`Auto sync = OFF`。必要な時だけ手動同期。

### Gitで管理しないもの
- `Daily/Inbox/`（取り込み用の一時領域）
- `Daily/Inbox/media/`（添付ファイル）
- `Daily/Inbox/_KeepSidianLogs/`（ログ）
- `.obsidian/plugins/keepsidian/`（端末依存設定・トークン）
- Gitで同期するのは、整形後ノートと運用ルール・スクリプトのみ。

### 端末別運用
- メインPC・自宅PC: KeepSidianをそれぞれ設定し、必要時に手動同期。
- スマホ: Vaultは閲覧中心で編集しない。

### コンフリクト回避
- Keepの生データはGitで配らない。
- 整形後のノートだけをGitで同期する。
- 競合が出たらInbox側ではなく、整形後ノート側で解消する。