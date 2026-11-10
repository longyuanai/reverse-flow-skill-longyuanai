@echo off
@chcp 65001 >nul
title [破甲 + Craft Anything] 双轨净室逆向与智能复刻工作台
setlocal
cd /d "%~dp0"

echo ==============================================================================
echo        🚀 Pojia (破甲) + Craft Anything (双轨净室逆向与复刻引擎)
echo ==============================================================================

where py >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set "PY_CMD=py"
) else (
    set "PY_CMD=python"
)

%PY_CMD% scripts\craft_pojia_bridge.py audit
echo ------------------------------------------------------------------------------
echo 常用命令说明:
echo   1. 联合分诊: %PY_CMD% scripts\craft_pojia_bridge.py triage ^<样本路径^>
echo   2. 双轨验证: %PY_CMD% scripts\craft_pojia_bridge.py verify --cmd ^<原程序^> --py ^<复刻代码^>
echo   3. 启动MCP:  craft-anything-cli mcp
echo ==============================================================================
cmd /k
