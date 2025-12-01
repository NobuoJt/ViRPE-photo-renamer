# Build script for creating a Windows EXE of ViRPE using PyInstaller
# Usage: Run from repository root in PowerShell (use the project's venv if available)

param(
    [switch]$OneFile = $false,
    [switch]$NoConsole = $false,
    [string]$Icon = ''
)

Write-Host "Activating virtual environment (if present)..."
if (Test-Path .\venv\Scripts\Activate.ps1) {
    & .\venv\Scripts\Activate.ps1
} else {
    Write-Host "No venv found at ./venv — continuing with current Python." -ForegroundColor Yellow
}

Write-Host "Installing build dependencies (PyInstaller)..."
python -m pip install --upgrade pip
python -m pip install -r .\requirements.txt
python -m pip install pyinstaller

Write-Host "Preparing PyInstaller arguments..."
$args = @()
if ($OneFile) { $args += '--onefile' } else { $args += '--onedir' }
if ($NoConsole) { $args += '--noconsole' }
if ($Icon -and (Test-Path $Icon)) { $args += "--icon=$Icon" } elseif ($Icon) { Write-Host "Icon file not found: $Icon" -ForegroundColor Yellow }

Write-Host "Running PyInstaller with args: $($args -join ' ')"
python -m PyInstaller @args ViRPE.py

Write-Host "Build finished. Check the ./dist folder for output."
