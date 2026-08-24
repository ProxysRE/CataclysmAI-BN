@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
set "BN_DIR=%~1"

if not defined BN_DIR (
    echo Cataclysm AI - stock Bright Nights prototype
    echo.
    set /p "BN_DIR=Enter the folder containing cataclysm-bn-tiles.exe: "
)

if not defined BN_DIR (
    echo No Bright Nights directory was provided.
    pause
    exit /b 2
)

set "PYTHON_CMD="
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 set "PYTHON_CMD=py -3"

if not defined PYTHON_CMD (
    where python >nul 2>nul
    if %ERRORLEVEL% EQU 0 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo Python 3 was not found in PATH.
    echo Install Python 3, then run this file again.
    pause
    exit /b 3
)

echo Starting Cataclysm AI with stock Bright Nights...
%PYTHON_CMD% "%SCRIPT_DIR%launch_stock_bn_ai.py" "%BN_DIR%"
set "CATAI_EXIT=%ERRORLEVEL%"

if not "%CATAI_EXIT%"=="0" (
    echo.
    echo Cataclysm AI launcher exited with code %CATAI_EXIT%.
    pause
)

exit /b %CATAI_EXIT%
