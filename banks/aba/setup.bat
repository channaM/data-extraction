@echo off
REM ABA Bank ETL Engine — Windows setup
REM Run once to create the virtual environment and install dependencies.
REM After this, always use:  venv\Scripts\python run.py <file>

echo.
echo ============================================
echo   ABA Bank ETL Engine -- Setup
echo ============================================

cd /d "%~dp0"

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.10 or later.
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo Python version: %PY_VER%

REM Create venv
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
) else (
    echo Virtual environment already exists.
)

REM Install dependencies
echo Installing dependencies...
venv\Scripts\pip install --upgrade pip --quiet
venv\Scripts\pip install -r requirements.txt --quiet

echo.
echo Setup complete.
echo.
echo To run the ETL engine:
echo   venv\Scripts\python run.py downloads\aba_sample_202501_USD.xlsx
echo.
pause
