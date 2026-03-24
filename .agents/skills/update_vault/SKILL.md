---
name: Vault Updater
description: 「更新分をまとめて」がトリガーとなり、新規本のインデックスノートを作成しタグ・リンクを自動付与する。「〇〇について話したい」がトリガーとなり、Vault全体（本・Memo・Insights・Topics）を横断して文脈を把握したうえで会話モードに入る。「Insightにまとめて」がトリガーとなり会話の気づきをInsightsフォルダに保存する。
---

# Vault Updater Skill

## トリガー条件
- **「更新分をまとめて」**：新規ハイライトを検出し、インデックスノートを作成・タグ・リンクを自動付与する
- **「〇〇について話したい」**：Vault全体を横断検索し、文脈を把握したうえで会話モードに入る
- **「Insightにまとめて」**：会話から得た気づきを `Insights/` フォルダに保存する

---

## フォルダ構成

```
Source/Kindle/    ← Kindleハイライト原文（編集禁止）
Source/KindleOCR/ ← OCRハイライト原文（編集禁止）

Notes/Books/      ← 本1冊ごとのインデックスノート（タグ・リンクのみ。要約・気づきは書かない）
Notes/Topics/     ← キーワード・ジャンルごとの横断ノート

Memo/             ← 雑多メモ・調べたこと・単発の考察
Ideas/            ← アイデア・企画・着想
Insights/         ← 会話から生まれた統合的な思考の記録（日付付き）
```

---

## 【トリガー1】「更新分をまとめて」

### 1. 処理対象ファイルの検出

- `Source/Kindle/` と `Source/KindleOCR/` 内のファイルを一覧取得する
- `Notes/Books/` 内の既存ノートを一覧取得する
- 以下を処理対象とする：
  - **新規**：Booksノートがまだ存在しない本
  - **追記あり**：ハイライト数（`highlightsCount`）がBooksノートの記録より増えている本
- 該当なしの場合は「新しい更新はありませんでした」と伝えて終了する

### 2. タグの自動付与

#### ジャンルタグ（NDC日本十進分類法・2階層）

| 大分類タグ | 小分類タグの例 |
|---|---|
| `#genre/哲学` | `#genre/哲学/心理学` `#genre/哲学/倫理学` `#genre/哲学/思想` |
| `#genre/歴史` | `#genre/歴史/日本史` `#genre/歴史/世界史` `#genre/歴史/伝記` |
| `#genre/社会科学` | `#genre/社会科学/経営` `#genre/社会科学/経済` `#genre/社会科学/教育` |
| `#genre/自然科学` | `#genre/自然科学/医学` `#genre/自然科学/脳科学` `#genre/自然科学/生物学` |
| `#genre/技術` | `#genre/技術/情報工学` `#genre/技術/建築` |
| `#genre/文学` | `#genre/文学/日本文学` `#genre/文学/海外文学` `#genre/文学/エッセイ` |
| `#genre/芸術` | `#genre/芸術/デザイン` `#genre/芸術/音楽` |

#### キーワードタグ（内容から自動抽出）
ハイライト内容を読み取り、主要テーマ・概念を3〜6個タグとして付与する。

### 3. Booksノートの作成・更新

#### 保存先
`Notes/Books/[本のタイトル].md`

#### ノートフォーマット（新規作成）

```markdown
# [本のタイトル]

著者: [[著者名]]
#genre/大分類/小分類 #キーワード1 #キーワード2 #キーワード3

ソース: [[Source/Kindle/ファイル名]] または [[Source/KindleOCR/ファイル名]]

---

## 関連ノート

- [[関連するBooksノート]]
- [[Notes/Topics/関連トピック]]
- [[Memo/関連するメモ]]

## 関連Insights

<!-- 「〇〇について話したい」で会話後に追記される -->

<!-- highlightsCount: [件数] -->
```

**重要**：
- `## ハイライト要約` は書かない（Sourceに原文がある）
- `## 気づき` は書かない（気づきはInsights/に保存する）
- AIによる分析・考察・まとめは一切書かない

#### 追記ありの場合
- `highlightsCount` を最新の件数に更新する
- タグ・リンクに変化がある場合のみ更新する
- その他のセクションは編集しない

### 4. 双方向リンクの確実な付与

新規ノート作成後、以下を**必ず全件実行**する。

#### A. 著者リンク
- 同じ `[[著者名]]` を持つ既存Booksノートを全件検索する
- 各ノートの `## 関連ノート` に今回のノートが含まれていなければ追記する
- 今回のノートの `## 関連ノート` にも既存ノートを追記する

#### B. キーワードタグ（Books横断）
- 同じキーワードタグを持つ既存Booksノートを全件検索する
- 共通タグが**2個以上**ある場合のみ `## 関連ノート` に相互追記する（ノイズ防止）

#### C. Memoとの関連付け
- `Memo/` 全ファイルのタグを確認する
- 今回の本のキーワードタグと共通するMemoファイルを検索する
- 共通タグがあれば：
  - 今回のBooksノートの `## 関連ノート` にMemoファイルを追記する
  - MemoファイルにもBooksノートへのリンクを追記する（双方向）

#### D. Topicsノートへのリンク
- `Notes/Topics/` 内の全ファイルのタグと照合する
- 対応するTopicsが存在する → 双方向追記する
- 対応するTopicsが存在しない → 同一タグが2冊以上あれば新規Topicsノートを作成する

### 5. KindleOCRリンクの更新

`Source/KindleOCR/` 内の `kindle_highlights: null` になっているファイルに対し、対応する `Source/Kindle/` ファイルとのリンクを付与する。

```python
import re, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

vault = Path('c:/Users/111r9/OneDrive/ドキュメント/obsidian')
ocr_dir = vault / 'Source' / 'KindleOCR'
kindle_dir = vault / 'Source' / 'Kindle'

def jp_only(s):
    return re.sub(r'[^\u3040-\u9FFF\u30A0-\u30FF\u4E00-\u9FFF]', '', s)

def find_highlight(title):
    title_jp = jp_only(title)
    for f in kindle_dir.iterdir():
        if f.suffix == '.md':
            fname_jp = jp_only(f.stem)
            if title_jp and fname_jp:
                if title_jp in fname_jp or fname_jp in title_jp:
                    return f'[[Source/Kindle/{f.name}]]'
    return None

for f in ocr_dir.glob('*.md'):
    if f.name == 'kindle_skip_list.md':
        continue
    content = f.read_text(encoding='utf-8')
    if 'kindle_highlights: null' not in content:
        continue
    title_match = re.search(r'^title: \"(.+)\"', content, re.MULTILINE)
    if not title_match:
        continue
    link = find_highlight(title_match.group(1))
    if link:
        f.write_text(content.replace('kindle_highlights: null', f'kindle_highlights: "{link}"'), encoding='utf-8')
        print(f'リンク付与: {f.name}')
```

### 6. 完了報告
- 作成・更新したBooksノート一覧とタグ
- 双方向リンクを追加した既存ノート一覧（どのノートにどのリンクを追記したか）
- 作成・更新したTopicsノート一覧
- 「〇〇について話したい」で会話を始められる旨の案内

---

## 【トリガー2】「〇〇について話したい」

### 1. Vault横断検索

会話開始前に以下を**必ず全件収集**する。

#### 本について話す場合
1. `Notes/Books/[タイトル].md` を読む（タグ・ソースリンク・関連リンク把握）
2. `ソース:` フィールドのリンクから `Source/Kindle/` または `Source/KindleOCR/` のファイルを直接読む（ハイライト全文）
3. 以下を横断検索する：
   - `Insights/` — この本・関連タグに言及しているファイルを全件確認
   - `Memo/` — 共通タグを持つファイルを全件確認
   - `Notes/Topics/` — 関連するTopicsノートを確認
   - `Ideas/` — 関連タグを持つアイデアを確認

#### テーマ・タグについて話す場合
1. 対応する `Notes/Topics/[テーマ名].md` を読む
2. Topicsノートに紐づく各Booksノートの `ソース:` から Sourceファイルを読む
3. 上記と同様に `Insights/`・`Memo/`・`Ideas/` を横断検索する

### 2. 会話冒頭での提示

収集した関連情報を冒頭で提示する：
- 関連する既存Insights（タイトルと一行要約）
- 関連するMemo（タイトルと概要）
- Topicsノートに未解決の問いがあれば提示
- 前回の会話からの継続点があれば提示

### 3. 会話の進め方
- ハイライト内容・Memo・Insightsを把握したうえで会話を開始する
- AIは自分の意見・解釈を積極的に述べてよい
- まとめを急かさない。ユーザーからの指示があるまで自然な会話として継続する
- 会話のまとめやノートへの追記は、ユーザーから明確な依頼があった場合のみ行う

### 4. 会話終了後の追記

ユーザーが「まとめて」「ノートに残して」などと言ったら：

**追記ルール（重要）**：
1. ユーザーが自分で語った言葉はそのまま含める
2. AIが提案・整理した内容はユーザーが明示的に同意した場合のみ含める
3. AIが補足・解釈・言い換えをして水増ししない

**保存手順：**
1. `Insights/YYYY-MM-DD-テーマ.md` を新規作成する（関連度の高い既存Insightがあれば追記も確認する）
2. 該当Booksノートの `## 関連Insights` に作成したファイルへのリンクを追記する
3. 関連するMemoノートにも `## 関連Insights` セクションがあれば追記する

---

## 【トリガー3】「Insightにまとめて」

会話の終わりにユーザーが「Insightにまとめて」と言ったら：

### 保存先
`Insights/[YYYY-MM-DD]-[テーマ].md`

### フォーマット

```markdown
# [テーマ・課題名]

日付: YYYY-MM-DD
起点: [[起点となったBooksノートまたは会話のきっかけ]]
関連本: [[Booksノート1]] [[Booksノート2]]
関連Memo: [[Memo/関連メモ]]
関連Topics: [[Notes/Topics/関連トピック]]
#テーマタグ1 #テーマタグ2

---

## 課題・問い

[会話の起点となった課題やアイデア]

---

## 会話から得た気づき

[ユーザーが自分で語った言葉・AIに同意した内容のみ]

---

## 次のアクション

- [ ] [会話から生まれたやること]
```

**追記ルール：**
- ユーザーが自分で語った言葉はそのまま含める
- AIが提案した内容はユーザーが同意した場合のみ含める
- タグは必ず付与する（省略禁止）
- 関連本・関連Memoが存在する場合はリンクを必ず記載する

**保存後：**
- 関連するBooksノートの `## 関連Insights` にリンクを追記する
- 関連するMemoノートにも追記する

---

## 禁止事項（Important Rules）
- `/Source` 配下のファイルは**編集・移動・削除すべて禁止**
- BooksノートにAIによるハイライト要約・考察・分析を**書かない**
- BooksノートにAIが自動で「気づき」を**書かない**（気づきはInsights/のみ）
- ユーザーが同意していない内容をノートに書かない
- 上記フォルダ以外の新規フォルダ作成禁止
- すべての返答・ノートは**日本語**で行う
