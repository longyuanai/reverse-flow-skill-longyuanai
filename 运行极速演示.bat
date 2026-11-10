@echo off
@chcp 65001 >nul
title [reverse-flow & pojia 自动化逆向极速演示]
setlocal
cd /d "%~dp0"

echo ==============================================================================
echo        reverse-flow (真心为你) ^& pojia (破甲) 自动化逆向极速演示
echo ==============================================================================

where py >nul 2>&1
if %ERRORLEVEL% equ 0 (
    py "%~dp0demo_quickstart.py"
) else (
    python "%~dp0demo_quickstart.py"
)

echo.
pause
