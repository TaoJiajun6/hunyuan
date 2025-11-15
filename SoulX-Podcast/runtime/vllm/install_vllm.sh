#!/bin/bash
# VLLM 手动安装脚本 (Linux/Mac)
# 用于安装 SoulX-Podcast 修改版的 VLLM 0.10.1

echo "========================================"
echo "VLLM 手动安装脚本"
echo "========================================"
echo ""

# 检查 Python
echo "[1/5] 检查 Python 环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python3，请先安装 Python 3.11"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo "✅ Python 已安装: $PYTHON_VERSION"

# 检查 CUDA
echo "[2/5] 检查 CUDA 支持..."
CUDA_CHECK=$(python3 -c "import torch; print('CUDA available:', torch.cuda.is_available())" 2>&1)
echo "✅ $CUDA_CHECK"
if [[ ! $CUDA_CHECK =~ "True" ]]; then
    echo "⚠️  警告: CUDA 不可用，VLLM 需要 GPU 支持"
fi

# 安装基础 VLLM
echo "[3/5] 安装基础 VLLM 0.10.1..."
echo "这可能需要几分钟时间..."
if pip3 install vllm==0.10.1; then
    echo "✅ VLLM 0.10.1 安装成功"
else
    echo "❌ VLLM 安装失败，尝试从源码安装..."
    echo "请手动执行: pip3 install git+https://github.com/vllm-project/vllm.git@v0.10.1"
    exit 1
fi

# 获取 VLLM 安装路径
echo "[4/5] 获取 VLLM 安装路径..."
VLLM_PATH=$(python3 -c "import vllm; import os; print(os.path.dirname(vllm.__file__))")
if [ -z "$VLLM_PATH" ]; then
    echo "❌ 错误: 无法获取 VLLM 路径，请检查安装"
    exit 1
fi
echo "✅ VLLM 路径: $VLLM_PATH"

# 克隆修改版 VLLM
echo "[5/5] 下载修改版 VLLM 文件..."
TEMP_DIR="${TMPDIR:-/tmp}"
VLLM_REPO_PATH="$TEMP_DIR/vllm"

if [ -d "$VLLM_REPO_PATH" ]; then
    echo "清理旧的仓库..."
    rm -rf "$VLLM_REPO_PATH"
fi

if git clone https://github.com/Soul-AILab/vllm.git "$VLLM_REPO_PATH" && \
   cd "$VLLM_REPO_PATH" && \
   git checkout v0.10.1.1-soulxpodcast; then
    echo "✅ 修改版 VLLM 下载成功"
    cd - > /dev/null
else
    echo "❌ 错误: 下载修改版 VLLM 失败"
    echo "请手动执行:"
    echo "  cd $TEMP_DIR"
    echo "  git clone https://github.com/Soul-AILab/vllm.git"
    echo "  cd vllm"
    echo "  git checkout v0.10.1.1-soulxpodcast"
    exit 1
fi

# 复制修改版文件
echo "[6/6] 应用修改版文件..."
FILES=(
    "vllm/model_executor/layers/sampler.py:model_executor/layers/sampler.py"
    "vllm/model_executor/layers/utils.py:model_executor/layers/utils.py"
    "vllm/model_executor/sampling_metadata.py:model_executor/sampling_metadata.py"
    "vllm/sampling_params.py:sampling_params.py"
)

for file_pair in "${FILES[@]}"; do
    IFS=':' read -r source_file dest_file <<< "$file_pair"
    source_path="$VLLM_REPO_PATH/$source_file"
    dest_path="$VLLM_PATH/$dest_file"
    
    if [ ! -f "$source_path" ]; then
        echo "⚠️  警告: 源文件不存在: $source_file"
        continue
    fi
    
    dest_dir=$(dirname "$dest_path")
    mkdir -p "$dest_dir"
    
    if cp "$source_path" "$dest_path"; then
        echo "  ✅ 已复制: $dest_file"
    else
        echo "❌ 错误: 复制文件失败: $dest_file"
        exit 1
    fi
done

echo "✅ 修改版文件应用成功"

# 验证安装
echo ""
echo "验证安装..."
if python3 -c "from vllm import LLM; print('✅ VLLM 安装成功，可以正常导入')"; then
    echo ""
    echo "========================================"
    echo "✅ VLLM 安装完成！"
    echo "========================================"
    echo ""
    echo "下一步："
    echo "1. 设置环境变量: export SOULX_PODCAST_LLM_ENGINE=vllm"
    echo "2. 或在 config.py 中设置: SOULX_PODCAST_LLM_ENGINE = 'vllm'"
    echo ""
else
    echo "❌ 验证失败，请检查安装过程"
    exit 1
fi

