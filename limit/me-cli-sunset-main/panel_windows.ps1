param(
    [ValidateSet("Menu", "AutoUpdate", "StartBot", "StopBot", "StartCli", "StopCli", "Status")]
    [string]$Action = "Menu"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RunDir = Join-Path $RootDir "run"
$LogDir = Join-Path $RootDir "logs"
$BotPidPath = Join-Path $RunDir "telegram_bot.pid"
$CliPidPath = Join-Path $RunDir "cli.pid"
$BotLogPath = Join-Path $LogDir "telegram_bot.log"
$CliLogPath = Join-Path $LogDir "cli.log"
$VenvPython = Join-Path $RootDir ".venv\Scripts\python.exe"
$BotScript = Join-Path $RootDir "telegram_main.py"
$CliScript = Join-Path $RootDir "main.py"
$AutoUpdateTask = "PaneldorAutoUpdate"
$AutoStartTask = "PaneldorBotAutoStart"

if (-not (Test-Path $RunDir)) { New-Item -ItemType Directory -Path $RunDir | Out-Null }
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

function Ensure-VenvPython {
    if (-not (Test-Path $VenvPython)) {
        throw "Python venv tidak ditemukan: $VenvPython. Jalankan setup.ps1 terlebih dahulu."
    }
}

function Get-PidValue {
    param([string]$PidPath)
    if (-not (Test-Path $PidPath)) { return $null }
    $raw = (Get-Content $PidPath -ErrorAction SilentlyContinue | Select-Object -First 1)
    if (-not $raw) { return $null }
    $id = 0
    if ([int]::TryParse($raw.Trim(), [ref]$id)) { return $id }
    return $null
}

function Test-IsRunning {
    param([string]$PidPath)
    $id = Get-PidValue -PidPath $PidPath
    if (-not $id) { return $false }
    $proc = Get-Process -Id $id -ErrorAction SilentlyContinue
    if (-not $proc) {
        Remove-Item $PidPath -ErrorAction SilentlyContinue
        return $false
    }
    return $true
}

function Get-ScriptProcessIds {
    param([string]$ScriptName)

    $procs = Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -eq 'python.exe' -and
            $_.CommandLine -and
            $_.CommandLine -match [Regex]::Escape($ScriptName) -and
            $_.CommandLine -match [Regex]::Escape($RootDir)
        }

    return @($procs | Select-Object -ExpandProperty ProcessId)
}

function Stop-AllScriptProcesses {
    param([string]$ScriptName)

    $ids = Get-ScriptProcessIds -ScriptName $ScriptName
    foreach ($id in @($ids)) {
        Stop-Process -Id $id -Force -ErrorAction SilentlyContinue
    }
    return @($ids).Count
}

function Start-ManagedProcess {
    param(
        [string]$Name,
        [string]$ScriptPath,
        [string]$PidPath,
        [string]$LogPath
    )

    Ensure-VenvPython

    # Avoid duplicate polling/update conflicts by cleaning stale/manual instances first.
    [void](Stop-AllScriptProcesses -ScriptName (Split-Path -Leaf $ScriptPath))

    if (Test-IsRunning -PidPath $PidPath) {
        $id = Get-PidValue -PidPath $PidPath
        Write-Host "$Name sudah berjalan (PID: $id)"
        return
    }

    $psCommand = "& `"$VenvPython`" `"$ScriptPath`" *>> `"$LogPath`""
    $argList = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-Command", $psCommand)
    $proc = Start-Process -FilePath "powershell.exe" -ArgumentList $argList -WorkingDirectory $RootDir -WindowStyle Hidden -PassThru
    Set-Content -Path $PidPath -Value $proc.Id
    Write-Host "$Name started. PID: $($proc.Id)"
}

function Stop-ManagedProcess {
    param(
        [string]$Name,
        [string]$PidPath,
        [string]$ScriptPath
    )

    $id = Get-PidValue -PidPath $PidPath
    if (-not $id) {
        Write-Host "$Name tidak berjalan."
        return
    }

    $proc = Get-Process -Id $id -ErrorAction SilentlyContinue
    if ($proc) {
        Stop-Process -Id $id -Force -ErrorAction SilentlyContinue
    }

    if ($ScriptPath) {
        [void](Stop-AllScriptProcesses -ScriptName (Split-Path -Leaf $ScriptPath))
    }
    Remove-Item $PidPath -ErrorAction SilentlyContinue
    Write-Host "$Name stopped."
}

function Show-Status {
    $botState = if (Test-IsRunning -PidPath $BotPidPath) { "RUNNING (PID: $(Get-PidValue -PidPath $BotPidPath))" } else { "STOPPED" }
    $cliState = if (Test-IsRunning -PidPath $CliPidPath) { "RUNNING (PID: $(Get-PidValue -PidPath $CliPidPath))" } else { "STOPPED" }

    Write-Host "Bot : $botState"
    Write-Host "CLI : $cliState"
}

function Update-Dependencies {
    Ensure-VenvPython
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install -r (Join-Path $RootDir "requirements.txt")
}

function Update-IfNeeded {
    param([switch]$RestartRunning)

    if (-not (Test-Path (Join-Path $RootDir ".git"))) {
        Write-Host "Git repo tidak ditemukan. Skip auto-update."
        return
    }

    $git = Get-Command git -ErrorAction SilentlyContinue
    if (-not $git) {
        Write-Host "git tidak ditemukan. Skip auto-update."
        return
    }

    $botWasRunning = Test-IsRunning -PidPath $BotPidPath
    $cliWasRunning = Test-IsRunning -PidPath $CliPidPath

    & git -C $RootDir fetch --all --prune | Out-Null

    $upstream = (& git -C $RootDir rev-parse --abbrev-ref --symbolic-full-name "@{u}" 2>$null)
    if (-not $upstream) {
        Write-Host "Branch belum punya upstream. Skip auto-update."
        return
    }

    $local = (& git -C $RootDir rev-parse HEAD).Trim()
    $remote = (& git -C $RootDir rev-parse "@{u}").Trim()

    if ($local -eq $remote) {
        Write-Host "Tidak ada update baru."
        return
    }

    Write-Host "Update terdeteksi. Menjalankan git pull --rebase ..."
    & git -C $RootDir pull --rebase
    Update-Dependencies

    if ($RestartRunning) {
        if ($botWasRunning) {
            Stop-ManagedProcess -Name "Bot" -PidPath $BotPidPath -ScriptPath $BotScript
            Start-ManagedProcess -Name "Bot" -ScriptPath $BotScript -PidPath $BotPidPath -LogPath $BotLogPath
        }

        if ($cliWasRunning) {
            Stop-ManagedProcess -Name "CLI" -PidPath $CliPidPath -ScriptPath $CliScript
            Start-ManagedProcess -Name "CLI" -ScriptPath $CliScript -PidPath $CliPidPath -LogPath $CliLogPath
        }
    }
}

function Enable-AutoUpdateTask {
    $scriptPath = $MyInvocation.MyCommand.Path
    $runCmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`" -Action AutoUpdate"
    schtasks /Create /TN $AutoUpdateTask /TR $runCmd /SC MINUTE /MO 30 /F | Out-Null
    Write-Host "Auto-update task aktif (setiap 30 menit)."
}

function Disable-AutoUpdateTask {
    schtasks /Delete /TN $AutoUpdateTask /F 2>$null | Out-Null
    Write-Host "Auto-update task dinonaktifkan."
}

function Enable-AutoStartBotTask {
    Ensure-VenvPython
    $runCmd = "`"$VenvPython`" `"$BotScript`""
    schtasks /Create /TN $AutoStartTask /TR $runCmd /SC ONLOGON /F | Out-Null
    Write-Host "Auto-start bot saat login aktif."
}

function Disable-AutoStartBotTask {
    schtasks /Delete /TN $AutoStartTask /F 2>$null | Out-Null
    Write-Host "Auto-start bot saat login dinonaktifkan."
}

function Show-Menu {
    Clear-Host
    Write-Host "==============================="
    Write-Host "  Paneldor - Windows Control"
    Write-Host "==============================="
    Write-Host "1) Start Telegram Bot (background)"
    Write-Host "2) Stop Telegram Bot"
    Write-Host "3) Start CLI (background)"
    Write-Host "4) Stop CLI"
    Write-Host "5) Status"
    Write-Host "6) Tail Bot Log"
    Write-Host "7) Tail CLI Log"
    Write-Host "8) Check & Update Now"
    Write-Host "9) Enable Auto-Update (Task Scheduler)"
    Write-Host "10) Disable Auto-Update"
    Write-Host "11) Enable Auto-Start Bot (on login)"
    Write-Host "12) Disable Auto-Start Bot"
    Write-Host "0) Exit"
    Write-Host "-------------------------------"
}

switch ($Action) {
    "AutoUpdate" {
        Update-IfNeeded -RestartRunning
        exit 0
    }
    "StartBot" {
        Start-ManagedProcess -Name "Bot" -ScriptPath $BotScript -PidPath $BotPidPath -LogPath $BotLogPath
        exit 0
    }
    "StopBot" {
        Stop-ManagedProcess -Name "Bot" -PidPath $BotPidPath -ScriptPath $BotScript
        exit 0
    }
    "StartCli" {
        Start-ManagedProcess -Name "CLI" -ScriptPath $CliScript -PidPath $CliPidPath -LogPath $CliLogPath
        exit 0
    }
    "StopCli" {
        Stop-ManagedProcess -Name "CLI" -PidPath $CliPidPath -ScriptPath $CliScript
        exit 0
    }
    "Status" {
        Show-Status
        exit 0
    }
}

while ($true) {
    Show-Menu
    $choice = Read-Host "Pilih menu"

    switch ($choice) {
        "1" { Start-ManagedProcess -Name "Bot" -ScriptPath $BotScript -PidPath $BotPidPath -LogPath $BotLogPath }
        "2" { Stop-ManagedProcess -Name "Bot" -PidPath $BotPidPath -ScriptPath $BotScript }
        "3" { Start-ManagedProcess -Name "CLI" -ScriptPath $CliScript -PidPath $CliPidPath -LogPath $CliLogPath }
        "4" { Stop-ManagedProcess -Name "CLI" -PidPath $CliPidPath -ScriptPath $CliScript }
        "5" { Show-Status }
        "6" {
            if (Test-Path $BotLogPath) { Get-Content $BotLogPath -Tail 80 }
            else { Write-Host "Log bot belum ada." }
        }
        "7" {
            if (Test-Path $CliLogPath) { Get-Content $CliLogPath -Tail 80 }
            else { Write-Host "Log CLI belum ada." }
        }
        "8" { Update-IfNeeded -RestartRunning }
        "9" { Enable-AutoUpdateTask }
        "10" { Disable-AutoUpdateTask }
        "11" { Enable-AutoStartBotTask }
        "12" { Disable-AutoStartBotTask }
        "0" { break }
        default { Write-Host "Pilihan tidak valid." }
    }

    Write-Host ""
    Read-Host "Tekan Enter untuk lanjut"
}
