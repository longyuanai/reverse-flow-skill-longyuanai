#!/usr/bin/env bash
# ==============================================================================
# Reverse Flow & Pojia - One-Click Installer for Linux & macOS
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================================================="
echo "  🚀 Reverse Flow & Pojia (破甲) 一键极速部署向导 (Linux/macOS)"
echo "  支持平台: Claude Code CLI / OpenAI Codex"
echo "=================================================================="

# 1. 查找 Python 解释器
PYTHON_CMD=""
for cmd in python3 python py; do
    if command -v "$cmd" >/dev/null 2>&1; then
        if "$cmd" -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >/dev/null 2>&1; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "[✗] 错误: 未检测到 Python 3.10+，请先安装 Python 3.10 或更高版本。"
    exit 1
fi

echo "[1/3] 检测到可用 Python 解释器: $PYTHON_CMD ($($PYTHON_CMD --version))"

# 2. 执行核心安装与同步
echo "[2/3] 同步技能并注入全局/本地免扰白名单..."
"$PYTHON_CMD" scripts/purge_friction.py install

# 3. 运行单元测试
echo "[3/3] 运行 48 项全量自检单元测试 (含 Craft Anything 双轨核验)..."
"$PYTHON_CMD" run_tests.py

echo "=================================================================="
echo "  🎉 全部安装配置完成！新电脑已 100% 准备就绪！"
echo "  在 Claude Code 或 Codex 中输入【真心为你】或【破甲】即可直接使用！"
echo "=================================================================="
