$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$rootDir = (Get-Location).Path

function Get-PythonExe {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($ver in @("3.12", "3.11", "3.10")) {
            try {
                $candidate = (& py -$ver -c "import sys; print(sys.executable)" 2>$null).Trim()
                if ($candidate) {
                    return $candidate
                }
            }
            catch {
            }
        }
    }

    if (Get-Command py -ErrorAction SilentlyContinue) {
        return (& py -3 -c "import sys; print(sys.executable)").Trim()
    }

    if (Get-Command python -ErrorAction SilentlyContinue) {
        return (& python -c "import sys; print(sys.executable)").Trim()
    }

    throw "Python 3 tidak ditemukan. Install Python 3.10+ terlebih dahulu."
}

$pythonExe = Get-PythonExe
Write-Host "Python executable: $pythonExe"

if (-not (Test-Path ".venv")) {
    Write-Host "Membuat virtual environment (.venv)..."
    & $pythonExe -m venv .venv
}

$venvPython = Join-Path (Get-Location) ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    throw "Gagal menemukan interpreter venv di $venvPython"
}

Write-Host "Meng-upgrade pip dan menginstal dependencies..."
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r requirements.txt

$allowFile = Join-Path $rootDir "user_allow.txt"
if (-not (Test-Path $allowFile)) {
    @(
        "# Daftar user id Telegram yang diizinkan mengakses bot.",
        "# Satu id per baris, contoh:",
        "# 123456789"
    ) | Set-Content -Path $allowFile -Encoding UTF8
}

$panelScript = Join-Path $rootDir "panel_windows.ps1"
if (-not (Test-Path $panelScript)) {
    throw "panel_windows.ps1 tidak ditemukan di $rootDir"
}

$panelBinDir = Join-Path $env:LOCALAPPDATA "paneldor"
if (-not (Test-Path $panelBinDir)) {
    New-Item -ItemType Directory -Path $panelBinDir | Out-Null
}

$shimPath = Join-Path $panelBinDir "paneldor.cmd"
$shimContent = @(
    "@echo off",
    "powershell -NoProfile -ExecutionPolicy Bypass -File `"$panelScript`" %*"
)
$shimContent | Set-Content -Path $shimPath -Encoding ASCII

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (-not $userPath) { $userPath = "" }
if (-not ($userPath -split ';' | Where-Object { $_.TrimEnd('\\') -ieq $panelBinDir.TrimEnd('\\') })) {
    $newUserPath = ($userPath.TrimEnd(';') + ";" + $panelBinDir).Trim(';')
    [Environment]::SetEnvironmentVariable("Path", $newUserPath, "User")
    Write-Host "PATH user diperbarui. Buka terminal baru agar command paneldor terdeteksi."
}

Write-Host "Selesai."
Write-Host "Jalankan aplikasi CLI: .venv\Scripts\python.exe main.py"
Write-Host "Jalankan bot Telegram: .venv\Scripts\python.exe telegram_main.py"
Write-Host "Jalankan panel Windows: paneldor"
