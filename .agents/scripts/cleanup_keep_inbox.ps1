param(
    [string]$VaultPath
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($VaultPath)) {
    $VaultPath = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

$inboxPath = Join-Path $VaultPath "Daily\Inbox"
if (-not (Test-Path -LiteralPath $inboxPath)) {
    Write-Host "Inbox not found: $inboxPath"
    exit 0
}

$targets = Get-ChildItem -LiteralPath $inboxPath -Force | Where-Object { $_.Name -ne ".gitkeep" }
if (-not $targets) {
    Write-Host "Nothing to clean in $inboxPath"
    exit 0
}

$count = 0
foreach ($item in $targets) {
    $literal = $item.FullName
    $longPath = if ($literal.StartsWith("\\?\")) { $literal } else { "\\?\$literal" }
    if ($item.PSIsContainer) {
        cmd /c rd /s /q "$longPath" | Out-Null
    } else {
        cmd /c del /f /q "$longPath" | Out-Null
    }
    $count += 1
}

Write-Host "Cleaned Keep inbox items: $count"
