# ==============================================================
#  Interview Sarathi - one-time setup (Windows / PowerShell)
#  Run from the project root:  .\setup.ps1
# ==============================================================
$ErrorActionPreference = "Stop"
$root     = $PSScriptRoot
$backend  = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$venv     = Join-Path $backend "venv"

Write-Host "`n=== Interview Sarathi setup ===`n" -ForegroundColor Cyan

# 1. Python virtual environment + dependencies
if (-not (Test-Path $venv)) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv $venv
}
& "$venv\Scripts\python.exe" -m pip install --upgrade pip
& "$venv\Scripts\python.exe" -m pip install -r (Join-Path $backend "requirements.txt")
Write-Host "Python dependencies installed." -ForegroundColor Green

# 2. .env file
$envFile = Join-Path $backend ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "No backend\.env found - add your GEMINI_API_KEY there." -ForegroundColor Yellow
    Write-Host "Get a free key: https://aistudio.google.com/app/apikey" -ForegroundColor Yellow
}

# 3. Frontend dependencies
if (Test-Path (Join-Path $frontend "package.json")) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
    Push-Location $frontend
    npm install
    Pop-Location
    Write-Host "Frontend dependencies installed." -ForegroundColor Green
}

Write-Host "`nSetup complete. Start the app with:  .\run.ps1`n" -ForegroundColor Cyan
