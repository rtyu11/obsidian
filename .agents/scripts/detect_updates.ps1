<#
.SYNOPSIS
  Vault Updater - 差分検出スクリプト
  Source/ のハイライト数と Notes/Books/ の highlightsCount を比較し、
  新しいハイライトのみを update_report.md に書き出す。

.USAGE
  PowerShell から実行:
    cd "c:\Users\111r9\OneDrive\ドキュメント\Obsidian Vault\obsidian"
    .\.agents\scripts\detect_updates.ps1

  または右クリック → PowerShell で実行

.OUTPUT
  .agents\scripts\update_report.md  ← AIに渡すレポート
#>

# ── エンコード設定（日本語対応） ──────────────────────────
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# ── パス設定 ──────────────────────────────────────────────
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$VaultRoot  = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$KindleDir  = Join-Path $VaultRoot "Source\Kindle"
$OCRDir     = Join-Path $VaultRoot "Source\OCR"
$BooksDir   = Join-Path $VaultRoot "Notes\Books"
$ReportPath = Join-Path $ScriptDir "update_report.md"

# ══════════════════════════════════════════════════════════
# 手動マッピング（自動マッチングが外れる場合にここへ追記）
#
# 書き方:
#   "SourceフォルダのファイルBaseName" = "Booksノートのファイル名（拡張子なし）"
#
# 例:
#   "コウタロウ-珍夜特急1―インド・パキスタン―" = "珍夜特急1"
# ══════════════════════════════════════════════════════════
$ManualMap = @{
    # ここに追加
}

# ── ヘルパー関数 ───────────────────────────────────────────

# ファイル内のハイライトブロック（--- 区切り）を配列で返す
function Get-HighlightBlocks {
    param([string]$FilePath)
    $raw = Get-Content $FilePath -Raw -Encoding UTF8
    if (-not $raw) { return @() }
    $blocks = $raw -split '\r?\n---\r?\n'
    # 空ブロック・短すぎるブロック（目次など）を除外
    return @($blocks | Where-Object { $_.Trim().Length -gt 15 })
}

# Notes/Books ノートに記録されている highlightsCount を取得
function Get-StoredCount {
    param([string]$FilePath)
    $raw = Get-Content $FilePath -Raw -Encoding UTF8
    if ($raw -match '<!--\s*highlightsCount:\s*(\d+)\s*-->') {
        return [int]$Matches[1]
    }
    return -1  # コメントなし = 未管理ノート
}

# BookTitle に対応する Source ファイルを探す
function Find-SourceFile {
    param([string]$BookTitle)

    # 1. 手動マッピング優先
    foreach ($key in $ManualMap.Keys) {
        if ($ManualMap[$key] -eq $BookTitle) {
            foreach ($dir in @($KindleDir, $OCRDir)) {
                $p = Join-Path $dir "$key.md"
                if (Test-Path $p) { return $p }
            }
        }
    }

    # 2. 自動マッチング: Source ファイル名に BookTitle が含まれるか
    $allSources = @()
    if (Test-Path $KindleDir) { $allSources += Get-ChildItem $KindleDir -Filter "*.md" }
    if (Test-Path $OCRDir)    { $allSources += Get-ChildItem $OCRDir    -Filter "*.md" }

    foreach ($src in $allSources) {
        if ($src.Name -eq ".gitkeep") { continue }
        if ($src.BaseName -like "*$BookTitle*") {
            return $src.FullName
        }
    }

    return $null
}

# ── メイン処理 ─────────────────────────────────────────────

$report      = [System.Collections.Generic.List[string]]::new()
$hasUpdates  = $false
$noSource    = @()
$upToDate    = @()
$updated     = @()

$report.Add("# Vault Update Report")
$report.Add("")
$report.Add("生成日時: $(Get-Date -Format 'yyyy-MM-dd HH:mm')")
$report.Add("")
$report.Add("---")
$report.Add("")

$notes = Get-ChildItem $BooksDir -Filter "*.md" |
         Where-Object { $_.Name -ne ".gitkeep" }

foreach ($note in $notes) {
    $title       = $note.BaseName
    $storedCount = Get-StoredCount $note.FullName

    # highlightsCount 未記録のノートはスキップ
    if ($storedCount -eq -1) { continue }

    $srcPath = Find-SourceFile $title
    if (-not $srcPath) {
        $noSource += $title
        continue
    }

    $blocks      = Get-HighlightBlocks $srcPath
    $srcCount    = $blocks.Count

    if ($srcCount -le $storedCount) {
        $upToDate += $title
        continue
    }

    # ─── 更新あり ───
    $hasUpdates = $true
    $newCount   = $srcCount - $storedCount
    $updated   += "$title ($storedCount → $srcCount)"

    $report.Add("## 📚 $title")
    $report.Add("")
    $report.Add("> **更新**: ${storedCount}件 → ${srcCount}件　（新規 **${newCount}件**）")
    $report.Add("> ソース: ``$(Split-Path $srcPath -Leaf)``")
    $report.Add("")
    $report.Add("### 新規ハイライト")
    $report.Add("")

    for ($i = $storedCount; $i -lt $srcCount; $i++) {
        $report.Add("#### [ハイライト $($i + 1)]")
        $report.Add("")
        $report.Add($blocks[$i].Trim())
        $report.Add("")
    }

    $report.Add("---")
    $report.Add("")
}

# ─── サマリー ───
$report.Add("## 📋 実行サマリー")
$report.Add("")

if ($updated.Count -gt 0) {
    $report.Add("### ✏️ 更新が必要な本 ($($updated.Count)冊)")
    foreach ($u in $updated) { $report.Add("- $u") }
    $report.Add("")
}

if ($upToDate.Count -gt 0) {
    $report.Add("### ✅ 最新の本 ($($upToDate.Count)冊)")
    foreach ($u in $upToDate) { $report.Add("- $u") }
    $report.Add("")
}

if ($noSource.Count -gt 0) {
    $report.Add("### ⚠️ ソースファイルが見つからなかった本")
    $report.Add("（手動マッピング追加を検討してください）")
    foreach ($u in $noSource) { $report.Add("- $u") }
    $report.Add("")
}

if (-not $hasUpdates) {
    $report.Add("**すべての本は最新状態です 🎉**")
}

# ─── ファイル出力 ───
$report | Out-File -FilePath $ReportPath -Encoding UTF8 -Force

Write-Host ""
Write-Host "═══════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Vault Update Report 生成完了" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
if ($hasUpdates) {
    Write-Host "  📝 更新が必要な本が $($updated.Count) 冊あります" -ForegroundColor Yellow
    foreach ($u in $updated) { Write-Host "     - $u" -ForegroundColor Yellow }
    Write-Host ""
    Write-Host "  → AIに「更新分をまとめて」と話しかけてください" -ForegroundColor Green
} else {
    Write-Host "  ✅ すべての本は最新状態です" -ForegroundColor Green
}

if ($noSource.Count -gt 0) {
    Write-Host ""
    Write-Host "  ⚠️ ソース未検出: $($noSource -join ', ')" -ForegroundColor DarkYellow
    Write-Host "     スクリプト内の ManualMap に追記してください" -ForegroundColor DarkYellow
}

Write-Host ""
Write-Host "  レポート: $ReportPath" -ForegroundColor Gray
Write-Host ""
