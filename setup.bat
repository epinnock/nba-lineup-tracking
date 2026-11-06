@echo off
REM NBA Lineup Tracker - Automated Setup Script (Windows)
REM This script sets up a Python virtual environment and installs all dependencies

echo.
echo NBA Lineup Tracker - Environment Setup
echo ==========================================
echo.

REM Check Python version
echo Checking Python version...
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Python not found. Please install Python 3.9 or higher.
    exit /b 1
)

python --version
echo.

REM Create virtual environment
echo Creating virtual environment...
if exist venv (
    echo Virtual environment already exists.
    set /p RECREATE="Do you want to remove and recreate? (y/N): "
    if /i "%RECREATE%"=="y" (
        rmdir /s /q venv
        python -m venv venv
        echo Virtual environment recreated
    ) else (
        echo Using existing virtual environment
    )
) else (
    python -m venv venv
    echo Virtual environment created
)
echo.

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo Virtual environment activated
echo.

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip >nul 2>&1
echo pip upgraded
echo.

REM Install dependencies
echo Installing dependencies...
echo This may take a few minutes...
pip install -r requirements.txt
echo.

REM Verify installation
echo Verifying installation...
python -c "import nba_api" 2>nul
if %ERRORLEVEL% EQU 0 (
    echo nba_api installed successfully
) else (
    echo nba_api installation failed
    exit /b 1
)

python -c "import pandas" 2>nul
if %ERRORLEVEL% EQU 0 (
    echo pandas installed successfully
) else (
    echo pandas installation failed
    exit /b 1
)

python -c "import pytest" 2>nul
if %ERRORLEVEL% EQU 0 (
    echo pytest installed successfully
) else (
    echo pytest installation failed
    exit /b 1
)

echo.
echo ==========================================
echo Setup complete!
echo.
echo To activate the environment in the future, run:
echo   venv\Scripts\activate
echo.
echo To run the application:
echo   python main.py 0022500032
echo.
echo To run tests:
echo   pytest tests/ -v
echo.
echo To deactivate when done:
echo   deactivate
echo ==========================================
echo.
pause