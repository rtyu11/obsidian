param(
    [string]$TaskName = "ObsidianKeepSync",
    [string]$VaultPath,
    [int]$IntervalMinutes = 15
)

$ErrorActionPreference = "Stop"

if ($IntervalMinutes -lt 1) {
    throw "IntervalMinutes must be >= 1"
}

if ([string]::IsNullOrWhiteSpace($VaultPath)) {
    $VaultPath = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

$runScript = Join-Path $VaultPath ".agents\scripts\run_keep_sync.ps1"
if (-not (Test-Path -LiteralPath $runScript)) {
    throw "run_keep_sync.ps1 not found: $runScript"
}

$wrapperPath = Join-Path $env:USERPROFILE ".codex\memories\run_keep_sync_task_wrapper.ps1"
$wrapperDir = Split-Path -Parent $wrapperPath
if (-not (Test-Path -LiteralPath $wrapperDir)) {
    New-Item -ItemType Directory -Path $wrapperDir | Out-Null
}

$wrapperBody = @"
`$ErrorActionPreference = "Stop"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$runScript"
"@
Set-Content -LiteralPath $wrapperPath -Value $wrapperBody -Encoding UTF8

$taskLogon = "${TaskName}_Logon"
$taskRepeat = "${TaskName}_Every${IntervalMinutes}Min"
$taskRun = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$wrapperPath`""
$taskRunQuoted = "`"$taskRun`""

function Invoke-Schtasks {
    param([string[]]$TaskArgs)
    $result = Start-Process -FilePath "schtasks.exe" -ArgumentList $TaskArgs -Wait -NoNewWindow -PassThru
    if ($result.ExitCode -ne 0) {
        throw "schtasks failed (exit=$($result.ExitCode)): $($TaskArgs -join ' ')"
    }
}

Invoke-Schtasks -TaskArgs @("/Create", "/TN", $taskLogon, "/SC", "ONLOGON", "/TR", $taskRunQuoted, "/F")
Invoke-Schtasks -TaskArgs @("/Create", "/TN", $taskRepeat, "/SC", "MINUTE", "/MO", "$IntervalMinutes", "/TR", $taskRunQuoted, "/F")

Write-Host "Registered tasks:"
Write-Host "  - $taskLogon (on logon)"
Write-Host "  - $taskRepeat (every $IntervalMinutes minutes)"
