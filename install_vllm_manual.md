# 手动安装 VLLM（修改版 v0.10.1）指南

## 前置要求

1. **Python 环境**：Python 3.11（推荐）
2. **CUDA 支持**：需要 NVIDIA GPU 和 CUDA
3. **已安装基础依赖**：torch, transformers 等

## 安装步骤

### 方法 1：使用安装脚本（推荐）

运行以下命令：

```bash
# Windows PowerShell
cd SoulX-Podcast\runtime\vllm
.\install_vllm.ps1

# Linux/Mac
cd SoulX-Podcast/runtime/vllm
chmod +x install_vllm.sh
./install_vllm.sh
```

### 方法 2：手动安装

#### 步骤 1：安装基础 VLLM 0.10.1

```bash
# 使用 pip 安装基础版本
pip install vllm==0.10.1
```

**注意**：如果 pip 安装失败，可能需要从源码安装。先尝试 pip，如果失败再使用源码安装。

#### 步骤 2：克隆修改版 VLLM 仓库

```bash
# 进入临时目录
cd /tmp  # Linux/Mac
# 或
cd %TEMP%  # Windows

# 克隆 Soul-AILab 的修改版 vllm
git clone https://github.com/Soul-AILab/vllm.git
cd vllm

# 切换到修改版分支
git checkout v0.10.1.1-soulxpodcast
```

#### 步骤 3：找到已安装的 VLLM 路径

```bash
# Python 命令获取 VLLM 安装路径
python -c "import vllm; import os; print(os.path.dirname(vllm.__file__))"
```

保存这个路径，例如：`C:\Users\YourName\AppData\Local\Programs\Python\Python311\Lib\site-packages\vllm`

#### 步骤 4：替换修改版文件

将克隆的修改版文件复制到已安装的 VLLM 目录：

**Windows PowerShell:**
```powershell
# 假设 VLLM 路径是 $VLLM_PATH，修改版路径是 $MODIFIED_VLLM_PATH
$VLLM_PATH = python -c "import vllm; import os; print(os.path.dirname(vllm.__file__))"
$MODIFIED_VLLM_PATH = "$env:TEMP\vllm"

# 复制修改版文件
Copy-Item "$MODIFIED_VLLM_PATH\vllm\model_executor\layers\sampler.py" "$VLLM_PATH\model_executor\layers\sampler.py" -Force
Copy-Item "$MODIFIED_VLLM_PATH\vllm\model_executor\layers\utils.py" "$VLLM_PATH\model_executor\layers\utils.py" -Force
Copy-Item "$MODIFIED_VLLM_PATH\vllm\model_executor\sampling_metadata.py" "$VLLM_PATH\model_executor\sampling_metadata.py" -Force
Copy-Item "$MODIFIED_VLLM_PATH\vllm\sampling_params.py" "$VLLM_PATH\sampling_params.py" -Force
```

**Linux/Mac:**
```bash
# 获取路径
VLLM_PATH=$(python3 -c "import vllm; import os; print(os.path.dirname(vllm.__file__))")
MODIFIED_VLLM_PATH="/tmp/vllm"

# 复制修改版文件
cp "$MODIFIED_VLLM_PATH/vllm/model_executor/layers/sampler.py" "$VLLM_PATH/model_executor/layers/sampler.py"
cp "$MODIFIED_VLLM_PATH/vllm/model_executor/layers/utils.py" "$VLLM_PATH/model_executor/layers/utils.py"
cp "$MODIFIED_VLLM_PATH/vllm/model_executor/sampling_metadata.py" "$VLLM_PATH/model_executor/sampling_metadata.py"
cp "$MODIFIED_VLLM_PATH/vllm/sampling_params.py" "$VLLM_PATH/sampling_params.py"
```

#### 步骤 5：验证安装

```python
# 测试 VLLM 是否可以正常导入
python -c "from vllm import LLM; print('✅ VLLM 安装成功')"
```

如果出现错误，检查：
1. CUDA 是否正确安装
2. PyTorch 是否支持 CUDA
3. 文件是否成功复制

## 配置使用 VLLM

安装完成后，设置环境变量：

```bash
# Windows PowerShell
$env:SOULX_PODCAST_LLM_ENGINE = "vllm"

# Linux/Mac
export SOULX_PODCAST_LLM_ENGINE=vllm
```

或者在代码中设置：

```python
# hunyuan_podcast/config.py 或环境变量
SOULX_PODCAST_LLM_ENGINE = "vllm"
```

## 常见问题

### 1. 安装 vllm==0.10.1 失败

如果 pip 安装失败，可能需要：
- 检查 CUDA 版本兼容性
- 尝试从源码安装：`pip install git+https://github.com/vllm-project/vllm.git@v0.10.1`

### 2. 文件复制权限错误

- Windows：以管理员身份运行 PowerShell
- Linux/Mac：使用 `sudo` 或确保有写入权限

### 3. 导入 VLLM 失败

检查：
- CUDA 是否可用：`python -c "import torch; print(torch.cuda.is_available())"`
- VLLM 版本：`python -c "import vllm; print(vllm.__version__)"`

## 性能提升

安装成功后，预期性能提升：
- **HF 引擎**：每段 7-10 秒
- **VLLM 引擎**：每段 1.5-3 秒（提升 2-5 倍）

## 回退到 HF 引擎

如果遇到问题，可以随时回退：

```bash
# 设置环境变量
export SOULX_PODCAST_LLM_ENGINE=hf
# 或
$env:SOULX_PODCAST_LLM_ENGINE = "hf"
```

系统会自动使用 HF 引擎，不会报错。

