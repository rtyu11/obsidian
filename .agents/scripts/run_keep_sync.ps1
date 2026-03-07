param(
    [string]$VaultPath,
    [string]$PythonExe = "python",
    [switch]$OpenObsidian
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($VaultPath)) {
    $VaultPath = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

$syncScript = Join-Path $VaultPath ".agents\scripts\sync_keep.py"
$logDir = Join-Path $VaultPath ".agents\logs"
$logFile = Join-Path $logDir "keep_sync.log"

if (-not (Test-Path -LiteralPath $syncScript)) {
    throw "sync_keep.py not found: $syncScript"
}

if (-not (Test-Path -LiteralPath $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $logFile -Value "[$timestamp] START keep sync"

Push-Location $VaultPath
try {
    $output = & $PythonExe $syncScript 2>&1
    $exitCode = $LASTEXITCODE
    if ($output) {
        $output | ForEach-Object { Add-Content -Path $logFile -Value $_ }
    }
    Add-Content -Path $logFile -Value "[$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")] END keep sync (exit=$exitCode)"
}
finally {
    Pop-Location
}

if ($OpenObsidian) {
    Start-Process "obsidian://open?vault=obsidian" | Out-Null
}
