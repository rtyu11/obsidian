---
name: Kindle OCR Pipeline
description: Playwright でKindle Cloud Reader を自動操作し、全書籍をGeminiでOCR変換してSource/KindleOCR/に保存する。Source/Kindle/のハイライトノートへfrontmatterリンク付き。
---

# Kindle OCR Pipeline

## トリガー条件
- 「Kindleをスキャンして」
- 「Kindle OCRして」

## 実行方法

```bash
python .agents/scripts/kindle_ocr.py
```

## 前提条件

1. **GEMINI_API_KEY** 環境変数が設定済みであること
2. 以下のライブラリがインストール済みであること:
   ```bash
   pip install playwright google-genai pillow
   playwright install chromium
   ```
3. Kindle Cloud Reader（https://read.amazon.co.jp）にAmazon Japanアカウントでログイン済みであること（初回のみ手動ログインが必要）

## 処理の流れ

1. Playwright（ヘッドフルモード）でKindleライブラリを開く
2. 未処理の書籍を自動検出
3. 書籍を1冊ずつ開き、ページ単位でスクリーンショット撮影
4. Gemini APIでMarkdown変換（OCR）
5. スクリーンショットをその場で削除（ディスク節約）
6. `Source/KindleOCR/[書籍タイトル].md` として保存

## 出力ファイル形式

```markdown
---
title: "書籍タイトル"
author: "著者名"
processed_date: 2026-03-19
source: kindle_ocr
pages: 247
kindle_highlights: "[[Source/Kindle/著者名-書籍タイトル.md]]"
---

（本文Markdown）
```

## ログ・再開機能

- **処理ログ**: `.agents/logs/kindle_ocr_log.json`
  - 処理済み書籍リスト・中断時の再開情報を記録
- **再開方法**: スクリプトを再実行するだけで中断ページから自動再開

## 出力先

`Source/KindleOCR/` — フルテキスト原本（編集禁止）
`Source/Kindle/` との関係: frontmatterの `kindle_highlights` フィールドでリンク

## 注意事項

- 処理中はブラウザウィンドウが開いたままになる（ヘッドフルモード）
- レート制限により1ページあたり約1.5秒かかる
- Amazon の DOM 変更でセレクタが壊れた場合はスクリプトを要修正
