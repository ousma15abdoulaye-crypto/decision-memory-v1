@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\premier_demarrage.ps1"
echo.
pause
