@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_safe_test_matrix.ps1"
exit /b %ERRORLEVEL%
