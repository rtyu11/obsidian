param(
    [string]$VaultPath,
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($VaultPath)) {
    $VaultPath = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

$runner = Join-Path $VaultPath ".agents\scripts\run_keep_sync.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "run_keep_sync.ps1 not found: $runner"
}

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $runner -VaultPath $VaultPath -PythonExe $PythonExe -OpenObsidian
