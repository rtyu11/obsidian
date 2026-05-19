param(
    [string]$VaultPath,
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

if ([string]::IsNullOrWhiteSpace($VaultPath)) {
    $VaultPath = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

Push-Location $VaultPath
try {
    & $PythonExe ".agents/scripts/repair_keep_mojibake.py" --apply
    & $PythonExe ".agents/scripts/process_keep_inbox.py"
}
finally {
    Pop-Location
}
