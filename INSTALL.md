# 混元AI播客生成系统 - 完整安装指南

## 目录

1. [系统要求](#系统要求)
2. [安装步骤](#安装步骤)
3. [验证安装](#验证安装)
4. [常见问题](#常见问题)

## 系统要求

### 必需组件

- **Python 3.10+**（IndexTTS-2要求Python 3.10或更高版本）
- **Git** 和 **Git-LFS**
- **操作系统**：Windows 10+, Linux, macOS

### 可选组件（推荐）

- **NVIDIA GPU** 和 **CUDA Toolkit 12.8+**（用于GPU加速）
- **至少 8GB 显存**（推荐16GB+用于最佳性能）

## 安装步骤

### 步骤 1：安装 Git 和 Git-LFS

#### Windows

1. 下载并安装 [Git for Windows](https://git-scm.com/download/win)
2. 下载并安装 [Git LFS](https://git-lfs.github.com/)
3. 打开命令提示符或PowerShell，运行：

```bash
git lfs install
```

#### Linux

```bash
# Ubuntu/Debian
sudo apt-get install git git-lfs
git lfs install

# CentOS/RHEL
sudo yum install git git-lfs
git lfs install
```

#### macOS

```bash
# 使用 Homebrew
brew install git git-lfs
git lfs install
```

### 步骤 2：下载 IndexTTS-2

```bash
# 克隆仓库
git clone https://github.com/index-tts/index-tts.git
cd index-tts

# 下载大型文件（模型文件等）
git lfs pull
```

### 步骤 3：安装 uv 包管理器

`uv` 是 IndexTTS-2 官方推荐的包管理器，速度比 pip 快 115 倍。

```bash
pip install -U uv
```

> ⚠️ **重要**：IndexTTS-2 只支持 `uv` 安装方法。使用 `conda` 或直接使用 `pip` 可能导致依赖版本错误、缺少 GPU 加速等问题。

### 步骤 4：安装 IndexTTS-2 依赖

进入 `index-tts` 目录：

```bash
cd index-tts
uv sync --all-extras
```

这个命令会：
- 自动创建虚拟环境 `.venv`
- 安装正确版本的 Python
- 安装所有必需的依赖项（包括 WebUI 和 DeepSpeed 支持）

#### 使用国内镜像（如果下载慢）

```bash
# 阿里云镜像
uv sync --all-extras --default-index "https://mirrors.aliyun.com/pypi/simple"

# 清华镜像
uv sync --all-extras --default-index "https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple"
```

#### 关于硬链接警告

如果安装时看到以下警告：

```
warning: Failed to hardlink files; falling back to full copy. This may lead to degraded performance.
```

这是正常的，通常发生在：
- 缓存目录和目标目录在不同的文件系统上
- Windows 系统上某些配置

**解决方案（可选）：**

如果想抑制这个警告，可以设置环境变量：

```bash
# Linux/macOS
export UV_LINK_MODE=copy

# Windows (PowerShell)
$env:UV_LINK_MODE="copy"

# Windows (CMD)
set UV_LINK_MODE=copy
```

或者在命令中直接指定：

```bash
uv sync --all-extras --link-mode=copy
```

> **注意**：这个警告不影响功能，只是性能可能略有下降。可以安全忽略。

### 步骤 5：下载 IndexTTS-2 模型文件

模型文件较大（约几GB），需要单独下载。**这是必需步骤，否则无法运行！**

#### 方式 1：使用 HuggingFace CLI（推荐）

```bash
# 进入 index-tts 目录
cd index-tts

# 安装 huggingface-cli
uv tool install "huggingface-hub[cli,hf_xet]"

# 下载模型（会自动下载到 checkpoints 目录）
hf download IndexTeam/IndexTTS-2 --local-dir=checkpoints
```

> **注意**：如果网络环境访问 HuggingFace 较慢，可以设置镜像：
> ```bash
> # Linux/macOS
> export HF_ENDPOINT="https://hf-mirror.com"
> 
> # Windows PowerShell
> $env:HF_ENDPOINT="https://hf-mirror.com"
> 
> # Windows CMD
> set HF_ENDPOINT=https://hf-mirror.com
> ```

#### 方式 2：使用 ModelScope（推荐国内用户）

```bash
# 进入 index-tts 目录
cd index-tts

# 安装 modelscope
uv tool install "modelscope"

# 下载模型
modelscope download --model IndexTeam/IndexTTS-2 --local_dir checkpoints
```

#### 验证模型文件

下载完成后，确保以下文件存在于 `index-tts/checkpoints/` 目录：

```bash
# 检查必需文件
ls index-tts/checkpoints/
```

应该包含以下文件：
- ✅ `config.yaml` - 配置文件
- ✅ `bpe.model` - BPE 分词模型
- ✅ `gpt.pth` - GPT 模型权重（较大，约几GB）
- ✅ `s2mel.pth` - S2Mel 模型权重（较大）
- ✅ `wav2vec2bert_stats.pt` - Wav2Vec2BERT 统计文件
- ✅ 其他模型相关文件

如果缺少任何文件，请重新下载。

### 步骤 6：设置 HuggingFace 镜像（推荐）

IndexTTS-2 在首次运行时会自动下载一些小的模型文件（如 `semantic_codec/model.safetensors`）。如果网络访问 HuggingFace 较慢，建议设置镜像：

```bash
# Linux/macOS
export HF_ENDPOINT="https://hf-mirror.com"

# Windows PowerShell
$env:HF_ENDPOINT="https://hf-mirror.com"

# Windows CMD
set HF_ENDPOINT=https://hf-mirror.com
```

> **提示**：启动脚本 `run_podcast_webui.py` 会自动设置镜像，无需手动设置。

### 步骤 7：安装播客系统额外依赖

返回项目根目录，安装播客系统需要的额外依赖：

```bash
# 返回项目根目录
cd ..

# 如果使用 uv 环境
uv pip install requests gradio

# 或激活 uv 环境后使用 pip
source index-tts/.venv/bin/activate  # Linux/macOS
# 或
index-tts\.venv\Scripts\activate  # Windows
pip install requests gradio
```

### 步骤 8：配置 API 密钥

API 密钥已配置在 `hunyuan_podcast/config.py` 中，也可以通过环境变量设置：

```bash
# Linux/macOS
export SILICONFLOW_API_KEY="your-api-key"

# Windows (PowerShell)
$env:SILICONFLOW_API_KEY="your-api-key"

# Windows (CMD)
set SILICONFLOW_API_KEY=your-api-key
```

## 验证安装

### 1. 检查 IndexTTS-2 安装

```bash
cd index-tts
uv run python -c "from indextts.infer_v2 import IndexTTS2; print('IndexTTS-2 安装成功！')"
```

### 2. 检查模型文件

确保以下文件存在：

```bash
ls index-tts/checkpoints/
# 应该包含：
# - config.yaml
# - bpe.model
# - gpt.pth
# - s2mel.pth
# - wav2vec2bert_stats.pt
```

### 3. 检查 GPU 支持（可选）

```bash
cd index-tts
uv run python tools/gpu_check.py
```

### 4. 测试播客系统

```bash
# 启动 WebUI
python run_podcast_webui.py
```

如果成功启动，应该看到：

```
🚀 混元AI播客生成系统已启动！
📡 访问地址: http://0.0.0.0:7861
```

## 常见问题

### Q1: `uv` 命令未找到

**解决方案：**

```bash
# 重新安装 uv
pip install -U uv

# 或使用完整路径
python -m uv sync --all-extras
```

### Q2: Git-LFS 下载失败

**解决方案：**

1. 确保 Git-LFS 已正确安装：
   ```bash
   git lfs version
   ```

2. 重新初始化 LFS：
   ```bash
   git lfs install
   git lfs pull
   ```

### Q3: 模型下载失败或很慢

**解决方案：**

1. 使用 ModelScope（国内用户推荐）：
   ```bash
   modelscope download --model IndexTeam/IndexTTS-2 --local_dir checkpoints
   ```

2. 设置 HuggingFace 镜像：
   ```bash
   export HF_ENDPOINT="https://hf-mirror.com"
   ```

### Q4: CUDA 相关错误

**解决方案：**

1. 确保安装了正确版本的 CUDA Toolkit（12.8+）
2. 检查 PyTorch 是否正确识别 GPU：
   ```bash
   python -c "import torch; print(torch.cuda.is_available())"
   ```

3. 如果 GPU 不可用，系统会自动回退到 CPU 模式（速度较慢）

### Q5: 导入 IndexTTS2 失败

**解决方案：**

1. 确保在正确的环境中运行：
   ```bash
   cd index-tts
   uv run python your_script.py
   ```

2. 检查路径配置：
   ```python
   import sys
   sys.path.insert(0, 'path/to/index-tts')
   ```

### Q6: API 调用失败

**解决方案：**

1. 检查 API 密钥是否正确配置
2. 检查网络连接
3. 查看 API 响应错误信息

### Q7: uv 安装时出现硬链接警告

**问题：**
```
warning: Failed to hardlink files; falling back to full copy.
```

**解决方案：**

这是正常警告，不影响功能。如果想抑制：

```bash
# 方法1：设置环境变量
export UV_LINK_MODE=copy  # Linux/macOS
# 或
$env:UV_LINK_MODE="copy"  # Windows PowerShell

# 方法2：在命令中指定
uv sync --all-extras --link-mode=copy
```

> **说明**：硬链接失败通常发生在缓存和目标目录在不同文件系统时，uv 会自动回退到复制模式，功能不受影响。

## 下一步

安装完成后，请查看：

- [QUICKSTART.md](QUICKSTART.md) - 快速开始指南
- [README_PODCAST.md](README_PODCAST.md) - 详细使用文档

## 获取帮助

如果遇到问题：

1. 查看 [IndexTTS-2 官方文档](https://github.com/index-tts/index-tts)
2. 检查错误日志
3. 确保所有依赖版本正确

