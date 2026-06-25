# ==============================================================
#  Interview Sarathi - start backend + frontend (Windows)
#  Run from the project root:  .\run.ps1
#  Backend  -> http://localhost:8000   (API + docs at /docs)
#  Frontend -> http://localhost:3000   (open this in the browser)
#  Press Ctrl+C in each window to stop.
# ==============================================================
$root     = $PSScriptRoot
$backend  = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$venv     = Join-Path $backend "venv"

if (-not (Test-Path "$venv\Scripts\python.exe")) {
    Write-Host "Virtual env not found. Run .\setup.ps1 first." -ForegroundColor Red
    exit 1
}

Write-Host "Starting backend (http://localhost:8000) ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd `"$backend`"; `$env:TF_CPP_MIN_LOG_LEVEL=3; .\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
)

Start-Sleep -Seconds 2

Write-Host "Starting frontend (http://localhost:3000) ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd `"$frontend`"; npm run dev"
)

Write-Host "`nBoth servers launching in separate windows." -ForegroundColor Green
Write-Host "Open http://localhost:3000 in your browser.`n" -ForegroundColor Green
