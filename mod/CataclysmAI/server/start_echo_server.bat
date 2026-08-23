@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if %errorlevel%==0 (
    py -3 cataclysm_ai_server.py
    goto :done
)

where python >nul 2>&1
if %errorlevel%==0 (
    python cataclysm_ai_server.py
    goto :done
)

echo.
echo Python 3 was not found.
echo Cataclysm AI 0.1 echo server requires Python 3.
pause
exit /b 1

:done
if errorlevel 1 pause
