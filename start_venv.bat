@@echo off
REM Change to the script directory
cd /d "%~dp0"

REM Activate the virtual environment
call venv\Scripts\activate

REM Open a new command prompt window with the venv activated
start cmd /k "call venv\Scripts\activate && echo Virtual environment activated. && cd /d %~dp0"
