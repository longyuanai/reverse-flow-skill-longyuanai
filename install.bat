@echo off
setlocal
cd /d "%~dp0"
echo ==================================================================
echo   Reverse Flow ^& Pojia (PoJia) - Windows One-Click Installer
echo ==================================================================

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"

pause
