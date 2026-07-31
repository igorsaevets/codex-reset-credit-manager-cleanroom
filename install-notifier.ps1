[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Medium')]
param(
    [ValidateRange(1, 168)]
    [int] $LeadHours = 12,

    [ValidateSet('auto', 'en', 'ru')]
    [string] $Language = 'auto',

    [ValidatePattern('^\d{2}:\d{2}$')]
    [string] $DailyAt = '09:00',

    [string] $InstallRoot = (Join-Path $env:LOCALAPPDATA 'CodexResetCreditNotifier'),

    [string] $PythonPath,

    [string] $AccountCodexHome,

    [switch] $SkipInitialCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$TaskPrefix = 'CodexResetCreditNotifier'
$DailyTaskName = "$TaskPrefix-DailyCheck"
$PackageSource = Join-Path $PSScriptRoot 'src\codex_reset_credit_manager'

function Resolve-CanonicalFile {
    param(
        [Parameter(Mandatory)]
        [string] $Path,

        [Parameter(Mandatory)]
        [string] $Description
    )

    $resolved = Resolve-Path -LiteralPath $Path -ErrorAction Stop
    if (@($resolved).Count -ne 1) {
        throw "$Description did not resolve to exactly one path."
    }
    $item = Get-Item -LiteralPath $resolved.Path -Force
    if ($item.PSIsContainer) {
        throw "$Description must be a file."
    }
    return $item.FullName
}

function Resolve-CanonicalDirectory {
    param(
        [Parameter(Mandatory)]
        [string] $Path,

        [Parameter(Mandatory)]
        [string] $Description
    )

    $resolved = Resolve-Path -LiteralPath $Path -ErrorAction Stop
    if (@($resolved).Count -ne 1) {
        throw "$Description did not resolve to exactly one path."
    }
    $item = Get-Item -LiteralPath $resolved.Path -Force
    if (-not $item.PSIsContainer) {
        throw "$Description must be a directory."
    }
    return $item.FullName
}

function Resolve-Python {
    if (-not [string]::IsNullOrWhiteSpace($PythonPath)) {
        return Resolve-CanonicalFile -Path $PythonPath -Description 'PythonPath'
    }

    $candidate = Get-Command python.exe -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($null -eq $candidate) {
        throw 'Python 3.11 or later was not found. Re-run with -PythonPath C:\path\to\python.exe.'
    }
    return Resolve-CanonicalFile -Path $candidate.Source -Description 'Python executable'
}

function Quote-WindowsArgument {
    param([Parameter(Mandatory)][string] $Value)
    if ($Value.Contains('"')) {
        throw 'A scheduled-task argument unexpectedly contains a double quote.'
    }
    return '"' + $Value + '"'
}

function Get-PackageFingerprint {
    $lines = foreach ($file in Get-ChildItem -LiteralPath $PackageSource -File -Filter '*.py' -Recurse | Sort-Object FullName) {
        $relative = $file.FullName.Substring($PackageSource.Length).TrimStart('\')
        $digest = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        "$relative`0$digest"
    }
    $bytes = [Text.Encoding]::UTF8.GetBytes(($lines -join "`n"))
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        return ([Convert]::ToHexString($sha.ComputeHash($bytes))).ToLowerInvariant()
    }
    finally {
        $sha.Dispose()
    }
}

if ($env:OS -ne 'Windows_NT') {
    throw 'The persistent modal notifier installer supports Windows only.'
}
if (-not (Test-Path -LiteralPath $PackageSource -PathType Container)) {
    throw "Package source was not found: $PackageSource"
}

$python = Resolve-Python
$pythonInfoJson = & $python -c 'import json,platform,sys,tkinter; print(json.dumps({"implementation": platform.python_implementation(), "version": list(sys.version_info[:3]), "prefix": sys.prefix, "base_prefix": sys.base_prefix}))'
if ($LASTEXITCODE -ne 0) {
    throw 'The selected Python could not import tkinter.'
}
$pythonInfo = $pythonInfoJson | ConvertFrom-Json
if ([int] $pythonInfo.version[0] -ne 3 -or [int] $pythonInfo.version[1] -lt 11) {
    throw 'The notifier requires CPython 3.11 or later.'
}
if ([string] $pythonInfo.implementation -ne 'CPython') {
    throw 'The notifier requires CPython.'
}

$pythonItem = Get-Item -LiteralPath $python
$pythonw = Join-Path $pythonItem.DirectoryName 'pythonw.exe'
$pythonw = Resolve-CanonicalFile -Path $pythonw -Description 'Windowless Python executable'

if ([string]::IsNullOrWhiteSpace($AccountCodexHome)) {
    $AccountCodexHome = if ([string]::IsNullOrWhiteSpace($env:CODEX_HOME)) {
        Join-Path $env:USERPROFILE '.codex'
    } else {
        $env:CODEX_HOME
    }
}
$accountCodexHomeFull = Resolve-CanonicalDirectory -Path $AccountCodexHome -Description 'Signed-in Codex home'

$resolvedLanguage = if ($Language -eq 'auto') {
    if ([Globalization.CultureInfo]::CurrentUICulture.Name -match '^ru(?:-|$)') {
        'ru'
    } else {
        'en'
    }
} else { $Language }

$dailyTime = [TimeSpan]::ParseExact($DailyAt, 'hh\:mm', [Globalization.CultureInfo]::InvariantCulture)
$installRootFull = [IO.Path]::GetFullPath($InstallRoot)
$stateRoot = Join-Path $installRootFull 'state'
$fingerprint = Get-PackageFingerprint
$appRoot = Join-Path $installRootFull ("app-" + $fingerprint.Substring(0, 16))
$packageTarget = Join-Path $appRoot 'codex_reset_credit_manager'

$arguments = @(
    '-m',
    'codex_reset_credit_manager',
    '--root',
    $stateRoot,
    'notifier-sync',
    '--allow-live-read',
    '--lead-hours',
    [string] $LeadHours,
    '--language',
    $resolvedLanguage,
    '--task-prefix',
    $TaskPrefix,
    '--account-codex-home',
    $accountCodexHomeFull
)
$argumentLine = ($arguments | ForEach-Object { Quote-WindowsArgument -Value $_ }) -join ' '

$description = "Read-only Codex reset-expiry check once per day. Schedules a persistent T-$LeadHours-hour modal reminder; never redeems a reset."
$targetSummary = "$DailyTaskName at $DailyAt daily; reminder lead $LeadHours hours; language $resolvedLanguage (mode $Language)"

if (-not $PSCmdlet.ShouldProcess($targetSummary, 'Install and activate read-only notifier')) {
    [PSCustomObject]@{
        Mode = 'WhatIf'
        DailyTaskName = $DailyTaskName
        DailyAt = $DailyAt
        LeadHours = $LeadHours
        LanguageMode = $Language
        Language = $resolvedLanguage
        Python = $python
        Pythonw = $pythonw
        AppRoot = $appRoot
        StateRoot = $stateRoot
        AccountCodexHome = $accountCodexHomeFull
        InitialCheck = -not $SkipInitialCheck
    }
    return
}

$null = New-Item -ItemType Directory -Path $packageTarget -Force
foreach ($sourceFile in Get-ChildItem -LiteralPath $PackageSource -File -Filter '*.py' -Recurse) {
    $relative = $sourceFile.FullName.Substring($PackageSource.Length).TrimStart('\')
    $targetFile = Join-Path $packageTarget $relative
    $null = New-Item -ItemType Directory -Path (Split-Path -Parent $targetFile) -Force
    Copy-Item -LiteralPath $sourceFile.FullName -Destination $targetFile -Force
}
$null = New-Item -ItemType Directory -Path $stateRoot -Force

$probeArguments = @(
    '-m',
    'codex_reset_credit_manager',
    '--root',
    $stateRoot,
    'notifier-sync',
    '--allow-live-read',
    '--lead-hours',
    [string] $LeadHours,
    '--language',
    $resolvedLanguage,
    '--task-prefix',
    $TaskPrefix,
    '--account-codex-home',
    $accountCodexHomeFull,
    '--dry-run',
    '--json'
)
$previousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $appRoot
    $probeOutput = & $python @probeArguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Read-only notifier readiness probe failed: $($probeOutput -join ' ')"
    }
}
finally {
    if ($null -eq $previousPythonPath) {
        Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    }
    else {
        $env:PYTHONPATH = $previousPythonPath
    }
}

$manifest = [ordered]@{
    schemaVersion = 1
    installedAtUtc = [DateTimeOffset]::UtcNow.ToString('O')
    packageFingerprintSha256 = $fingerprint
    appRoot = $appRoot
    stateRoot = $stateRoot
    python = $python
    pythonw = $pythonw
    accountCodexHome = $accountCodexHomeFull
    dailyTaskName = $DailyTaskName
    dailyAtLocal = $DailyAt
    leadHours = $LeadHours
    languageMode = $Language
    language = $resolvedLanguage
    readOnly = $true
}
$manifest |
    ConvertTo-Json -Depth 10 |
    Set-Content -LiteralPath (Join-Path $installRootFull 'install-manifest.json') -Encoding utf8

$action = New-ScheduledTaskAction `
    -Execute $pythonw `
    -Argument $argumentLine `
    -WorkingDirectory $appRoot
$trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At ([DateTime]::Today.Add($dailyTime))
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -WakeToRun `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
$principal = New-ScheduledTaskPrincipal `
    -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) `
    -LogonType Interactive `
    -RunLevel Limited

$null = Register-ScheduledTask `
    -TaskName $DailyTaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description $description `
    -Force

[xml] $registeredXml = Export-ScheduledTask -TaskName $DailyTaskName
$registeredTask = Get-ScheduledTask -TaskName $DailyTaskName
$registeredAction = $registeredXml.Task.Actions.Exec
$registeredTrigger = $registeredXml.Task.Triggers.CalendarTrigger
if ([string] $registeredAction.Command -ne $pythonw) {
    throw 'Registered task command does not match the validated pythonw path.'
}
if (-not ([string] $registeredAction.Arguments).Contains('notifier-sync')) {
    throw 'Registered task does not run notifier-sync.'
}
if (-not ([string] $registeredAction.Arguments).Contains('--allow-live-read')) {
    throw 'Registered task is missing the explicit read-only opt-in.'
}
if (-not ([string] $registeredAction.Arguments).Contains('--account-codex-home')) {
    throw 'Registered task is missing the validated signed-in Codex home.'
}
if ([string] $registeredAction.Arguments -match 'consume|redeem') {
    throw 'Registered task unexpectedly contains a reset-use action.'
}
if ([string] $registeredTrigger.ScheduleByDay.DaysInterval -ne '1') {
    throw 'Registered notifier check is not configured for once per day.'
}
if ([string] $registeredTask.Principal.RunLevel -ne 'Limited') {
    throw 'Registered notifier task is not least privilege.'
}
if ([string] $registeredXml.Task.Settings.StartWhenAvailable -ne 'true') {
    throw 'Registered notifier task is missing StartWhenAvailable.'
}
if ([string] $registeredXml.Task.Settings.WakeToRun -ne 'true') {
    throw 'Registered notifier task is missing WakeToRun.'
}

if (-not $SkipInitialCheck) {
    Start-ScheduledTask -TaskName $DailyTaskName
}

[PSCustomObject]@{
    Mode = 'Installed'
    DailyTaskName = $DailyTaskName
    DailyAt = $DailyAt
    LeadHours = $LeadHours
    LanguageMode = $Language
    Language = $resolvedLanguage
    Pythonw = $pythonw
    AppRoot = $appRoot
    StateRoot = $stateRoot
    InitialCheckStarted = -not $SkipInitialCheck
}
