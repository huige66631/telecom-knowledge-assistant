@echo off
setlocal

cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_app.ps1"

if errorlevel 1 (
    echo.
    echo Startup failed. Check .env, Python, or installed dependencies.
    pause
)
