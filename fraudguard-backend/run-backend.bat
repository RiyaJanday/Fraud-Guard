@echo off
REM Starts the FraudGuard backend correctly from Command Prompt.
REM Uses "python -m uvicorn" instead of the uvicorn.exe launcher stub --
REM that stub expands wildcard (*) characters in its arguments itself,
REM before Python ever sees them, which is what caused the
REM "Got unexpected extra arguments" error regardless of shell or quoting.

cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo ERROR: .venv not found. Run this from fraudguard-backend after creating the venv.
    exit /b 1
)

call .venv\Scripts\activate.bat

python -m uvicorn app.main:app --reload --reload-exclude "app/ml_engine/models/*" --reload-exclude "logs/*"
