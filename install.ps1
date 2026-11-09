# ==============================================================================
# Reverse Flow & Pojia - One-Click Installer for Windows PowerShell
# ==============================================================================
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "  Reverse Flow & Pojia (破甲) 一键极速部署向导" -ForegroundColor Cyan
Write-Host "  支持平台: Claude Code CLI / OpenAI Codex" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan

# 1. 自动探测可用的真实 Python 解释器
$pythonCmd = $null
$candidates = @("py", "python3", "python")

foreach ($cmd in $candidates) {
    try {
        $check = Get-Command $cmd -ErrorAction SilentlyContinue
        if ($null -ne $check) {
            $path = $check.Source
            if ($path -like "*WindowsApps*" -and (-not (Test-Path $path))) {
                continue
            }
            $ver = & $cmd --version
            if ($LASTEXITCODE -eq 0) {
                $pythonCmd = $cmd
                break
            }
        }
    } catch {
        # ignore error
    }
}

if (-not $pythonCmd) {
    Write-Host ""
    Write-Host "[X] 未检测到可用的 Python 3.10+ 解释器！" -ForegroundColor Red
    Write-Host "    请先从 https://www.python.org/downloads/ 安装 Python 并在安装时勾选 Add Python to PATH。" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "[1/3] 检测到可用 Python 解释器: $pythonCmd" -ForegroundColor Green

# 2. 执行核心安装与同步
Write-Host "[2/3] 同步技能到 ~/.claude/skills 及 ~/.codex/skills 并注入免扰白名单..." -ForegroundColor Green
& $pythonCmd scripts/purge_friction.py install
if ($LASTEXITCODE -ne 0) {
    Write-Host "[X] 技能同步或白名单注入失败，退出。" -ForegroundColor Red
    exit 1
}

# 3. 运行全量单元测试自检
Write-Host ""
Write-Host "[3/3] 运行 48 项全量自检单元测试 (含 Craft Anything 双轨核验)..." -ForegroundColor Green
& $pythonCmd run_tests.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "[X] 单元测试未全部通过，请检查环境！" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "  [OK] 全部安装配置完成！新电脑已 100% 准备就绪！" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "  【日常调用方法】" -ForegroundColor Yellow
Write-Host "  - 摸底分诊/建 Case 流程:  打开 Claude Code 或 Codex 输入: 真心为你" -ForegroundColor White
Write-Host "  - 深入提取指令与算法还原: 打开 Claude Code 或 Codex 输入: 破甲" -ForegroundColor White
Write-Host "  - 查看 30 秒演示效果:     运行 $pythonCmd demo_quickstart.py" -ForegroundColor White
Write-Host "==================================================================" -ForegroundColor Cyan
