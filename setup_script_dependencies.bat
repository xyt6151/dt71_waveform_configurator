@echo off
echo This script will set up your virtual environment and install necessary dependencies.
echo Press ENTER to begin the process.
pause >nul

REM Change to the script directory
cd /d "%~dp0"

REM Create virtual environment
python -m venv venv

REM Activate virtual environment
call venv\Scripts\activate

REM Install dependencies
pip install matplotlib numpy pyperclip scipy

REM Check if tkinter is available
python -c "import tkinter" 2>nul || (
    echo.
    echo tkinter is not installed. Please ensure you have Python with tkinter support.
    echo.
    pause
)

REM Open a new command prompt window with the venv activated
start cmd /k "call venv\Scripts\activate && echo Virtual environment activated. && cd /d %~dp0"
