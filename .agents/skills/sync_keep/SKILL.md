---
name: Keep Syncer
description: 「Keepを同期して」がトリガーとなり、Google Keep の ob-* ラベルのメモを Daily/Inbox/ に書き出す。完了後に process_daily スキルで整形できる。
---

# Keep Syncer Skill

## トリガー条件
- **「Keepを同期して」**：Google Keep のメモを Daily/Inbox/ に書き出す
- **「Keepを同期してから整形して」**：同期 → Inbox整形 を連続実行する

---

## フォルダ構成

```
.agents/scripts/
  sync_keep.py            ← メイン同期スクリプト
  sync_keep_setup.py      ← 初回セットアップ用（トークン取得）

Daily/Inbox/              ← 同期結果の出力先
  YYYY-MM-DD-ideas.md
  YYYY-MM-DD-tasks.md
  YYYY-MM-DD-memo.md

C:\Users\111r9\.keep_token  ← 認証トークン（Vault外・git管理外）
```

---

## 実行手順

### 1. セットアップ確認

`C:\Users\111r9\.keep_token` が存在するか確認する。

存在しない場合は以下を伝えて終了：
> 「セットアップが必要です。以下の手順を実行してください：
> 1. pip install gkeepapi
> 2. python ".agents/scripts/sync_keep_setup.py"」

### 2. スクリプト実行

以下のコマンドを Bash ツールで実行する：

```bash
python ".agents/scripts/sync_keep.py"
```

作業ディレクトリ：`c:/Users/111r9/OneDrive/ドキュメント/Obsidian Vault/obsidian/`

### 3. 実行結果の確認

- `同期完了: YYYY-MM-DD-ideas.md (X件), ...` と表示されれば成功
- エラーが出た場合は日本語でユーザーに伝え、対処法を案内する

**よくあるエラーと対処：**

| エラー | 原因 | 対処 |
|---|---|---|
| `トークンファイルが見つかりません` | セットアップ未実施 | `sync_keep_setup.py` を実行 |
| `接続に失敗しました` | トークン期限切れ | `sync_keep_setup.py` を再実行 |
| `ModuleNotFoundError: gkeepapi` | ライブラリ未インストール | `pip install gkeepapi` を実行 |

### 4. 結果報告

書き出されたファイルの件数を簡潔に報告する。

例：「アイデア4件、タスク2件、メモ1件を Daily/Inbox/ に書き出しました」

### 5. 後続処理の案内

「Inboxを整形して」と続けることで process_daily スキルを呼び出せることを案内する。

ユーザーが「整形して」と言ったら process_daily スキルの手順に移る。

---

## 禁止事項

- `Source/` 配下のファイルは編集・移動・削除すべて禁止
- `.keep_token` の中身をチャットに表示しない（セキュリティ）
- すべての返答・ノートは**日本語**で行う

---

## 初回セットアップ手順

初回のみ以下を実行すること：

**ステップ1：Googleアプリパスワードの取得（2段階認証を使用している場合）**

1. `https://myaccount.google.com/apppasswords` を開く
2. アプリ名を任意で入力して作成
3. 表示された16文字のパスワードをメモする

**ステップ2：gkeepapi のインストール**

```bash
pip install gkeepapi
```

**ステップ3：トークン取得**

```bash
python ".agents/scripts/sync_keep_setup.py"
```

メールアドレスとアプリパスワードを入力すると `C:\Users\111r9\.keep_token` が生成される。

---

## 全体フロー

```
スマホ音声入力
    ↓
Google Keep（ob-ideas / ob-tasks / ob-memo ラベル）
    ↓
「Keepを同期して」（このスキル）
    ↓
sync_keep.py 実行 → Daily/Inbox/YYYY-MM-DD-*.md 生成
    ↓
「Inboxを整形して」（process_daily スキル）
    ↓
Daily/Ideas・Tasks・Memo に追記、Inbox 削除
```
