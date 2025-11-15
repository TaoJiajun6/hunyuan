#!/bin/bash
# 混元AI播客生成系统 - uv环境启动脚本（Linux/macOS）

# 检查是否在 index-tts 目录
if [ ! -d "index-tts" ]; then
    echo "❌ 错误：未找到 index-tts 目录"
    echo "请确保在项目根目录运行此脚本"
    exit 1
fi

# 进入 index-tts 目录
cd index-tts

# 检查 uv 环境是否存在
if [ ! -d ".venv" ]; then
    echo "⚠️  警告：未找到 uv 虚拟环境"
    echo "正在创建环境..."
    uv sync --all-extras
fi

# 使用 uv run 运行播客系统
echo "🚀 正在启动混元AI播客生成系统..."
uv run python ../run_podcast_webui.py
























