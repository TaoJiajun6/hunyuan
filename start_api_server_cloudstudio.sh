#!/bin/bash
# Cloud Studio API服务器启动脚本
# 用于在Cloud Studio环境中启动混元AI播客生成API服务

echo "🚀 启动混元AI播客生成API服务（Cloud Studio环境）"
echo "=========================================="

# 设置HuggingFace镜像
if [ -z "$HF_ENDPOINT" ]; then
    export HF_ENDPOINT="https://hf-mirror.com"
    echo "💡 已设置 HuggingFace 镜像: $HF_ENDPOINT"
fi

# 设置GPU配置（如果Cloud Studio提供GPU）
export USE_FP16="true"
export USE_CUDA_KERNEL="true"
export DEVICE="cuda:0"

echo "⚙️  配置信息:"
echo "   - USE_FP16: $USE_FP16"
echo "   - USE_CUDA_KERNEL: $USE_CUDA_KERNEL"
echo "   - DEVICE: $DEVICE"
echo ""

# 检查Python环境
if ! command -v python &> /dev/null; then
    echo "❌ 错误: 未找到Python"
    exit 1
fi

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查必要的文件
if [ ! -f "run_api_server.py" ]; then
    echo "❌ 错误: 未找到 run_api_server.py"
    exit 1
fi

# 创建日志目录
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/api_server_$(date +%Y%m%d_%H%M%S).log"

echo "📝 日志文件: $LOG_FILE"
echo ""

# 启动API服务器（后台运行）
echo "🚀 正在启动API服务器..."
nohup python run_api_server.py \
    --host 0.0.0.0 \
    --port 8000 \
    --fp16 \
    --cuda_kernel \
    > "$LOG_FILE" 2>&1 &

# 获取进程ID
PID=$!
echo "✅ API服务器已启动，进程ID: $PID"
echo ""

# 等待几秒检查服务是否正常启动
sleep 3

# 检查进程是否还在运行
if ps -p $PID > /dev/null; then
    echo "✅ 服务运行正常"
    echo ""
    echo "📋 服务信息:"
    echo "   - 进程ID: $PID"
    echo "   - 端口: 8000"
    echo "   - 日志文件: $LOG_FILE"
    echo ""
    echo "💡 查看日志: tail -f $LOG_FILE"
    echo "💡 停止服务: kill $PID"
    echo ""
    echo "📡 访问地址:"
    echo "   - 本地: http://127.0.0.1:8000"
    echo "   - 健康检查: http://127.0.0.1:8000/health"
    echo "   - API文档: http://127.0.0.1:8000/docs"
    echo ""
    echo "🌐 Cloud Studio端口转发地址请查看日志文件获取"
else
    echo "❌ 服务启动失败，请查看日志: $LOG_FILE"
    exit 1
fi






















