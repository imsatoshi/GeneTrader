@echo off
setlocal

cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_frontend.ps1"

if errorlevel 1 (
    echo.
    echo Frontend launcher failed. See the message above for details.
    pause
    exit /b %errorlevel%
)
