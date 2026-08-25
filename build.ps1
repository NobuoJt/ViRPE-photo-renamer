# Build script for creating a Windows EXE of ViRPE using PyInstaller
# Usage: Run from repository root in PowerShell (use the project's venv if available)

param(
    [switch]$OneFile = $false,
    [switch]$NoConsole = $false,
    [string]$Icon = ''
)

Write-Host "Activating virtual environment (if present)..."
if (Test-Path .\.venv\Scripts\Activate.ps1) {
    & .\.venv\Scripts\Activate.ps1
} else {
    Write-Host "No venv found at ./.venv — continuing with current Python." -ForegroundColor Yellow
}

Write-Host "Installing build dependencies (PyInstaller)..."
python -m pip install --upgrade pip
python -m pip install -r .\requirements.txt
python -m pip install pyinstaller

Write-Host "Preparing PyInstaller arguments..."
$args_v = @()
if ($OneFile) { $args_v += '--onefile' } else { $args_v += '--onedir' }
if ($NoConsole) { $args_v += '--noconsole' }
if ($Icon -and (Test-Path $Icon)) { $args_v += "--icon=$Icon" } elseif ($Icon) { Write-Host "Icon file not found: $Icon" -ForegroundColor Yellow }

Write-Host "Running PyInstaller with args_v: $($args_v -join ' ')"
python -m PyInstaller @args_v ViRPE.pyw

Write-Host "Build finished. Check the ./dist folder for output."
