# ============================================================
# FraudGuard Backend Launcher
# ============================================================

$ErrorActionPreference = "Stop"

# Always run from the directory containing this script
Set-Location $PSScriptRoot

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "       FraudGuard Backend Starting      " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ------------------------------------------------------------
# Check virtual environment
# ------------------------------------------------------------

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "ERROR: Python virtual environment not found." -ForegroundColor Red
    Write-Host ""
    Write-Host "Expected:" -ForegroundColor Yellow
    Write-Host $venvPython
    Write-Host ""
    exit 1
}

Write-Host "Virtual environment: OK" -ForegroundColor Green
Write-Host "Backend directory: $PSScriptRoot" -ForegroundColor Green
Write-Host ""

# ------------------------------------------------------------
# Start FastAPI / Uvicorn
# ------------------------------------------------------------
# IMPORTANT:
# Do NOT use --reload-exclude here.
# On this Windows setup, the wildcard values are being
# expanded into actual files before Uvicorn receives them.
#
# The simple command below has already been tested successfully.
# ------------------------------------------------------------

Write-Host "Starting FastAPI server..." -ForegroundColor Cyan
Write-Host ""
Write-Host "API:  http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "Docs: http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host ""
Write-Host "Press CTRL+C to stop the server." -ForegroundColor Yellow
Write-Host ""

& $venvPython -m uvicorn app.main:app --reload

# ------------------------------------------------------------
# Exit
# ------------------------------------------------------------

$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "       Backend stopped with error       " -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Exit code: $exitCode" -ForegroundColor Red
}

exit $exitCode