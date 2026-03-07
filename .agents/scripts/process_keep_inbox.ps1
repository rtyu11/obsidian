param(
    [string]$VaultPath,
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

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
