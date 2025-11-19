# 混元AI播客生成系统 - 完整安装指南

## 目录

1. [系统要求](#系统要求)
2. [安装步骤](#安装步骤)
3. [验证安装](#验证安装)
4. [常见问题](#常见问题)

## 系统要求

### 必需组件

- **Python 3.10+**（SoulX-Podcast要求Python 3.10或更高版本）
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

### 步骤 2：克隆项目仓库

```bash
# 克隆仓库
git clone https://github.com/your-username/hunyuan-podcast.git
cd hunyuan-podcast
```

### 步骤 3：安装Python依赖

```bash
# 安装依赖
pip install -r requirements_podcast.txt
```

### 步骤 4：下载SoulX-Podcast模型文件

模型文件较大（约几GB），需要单独下载。**这是必需步骤，否则无法运行！**

#### 方式 1：使用 HuggingFace CLI（推荐）

```bash
# 安装 huggingface-cli
pip install -U huggingface_hub

# 下载SoulX-Podcast模型
huggingface-cli download --resume-download Soul-AILab/SoulX-Podcast-1.7B --local-dir SoulX-Podcast/pretrained_models/SoulX-Podcast-1.7B
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

#### 方式 2：使用 Python 脚本下载

```python
from huggingface_hub import snapshot_download

snapshot_download(
    'Soul-AILab/SoulX-Podcast-1.7B',
    local_dir='SoulX-Podcast/pretrained_models/SoulX-Podcast-1.7B'
)
```

#### 验证模型文件

下载完成后，确保 `SoulX-Podcast/pretrained_models/SoulX-Podcast-1.7B/` 目录存在且包含模型文件。

### 步骤 5：配置模型路径

在 `hunyuan_podcast/config.py` 中配置模型路径：

```python
SOULX_PODCAST_MODEL_DIR = "SoulX-Podcast/pretrained_models/SoulX-Podcast-1.7B"
```

### 步骤 6：设置 HuggingFace 镜像（推荐，可选）

如果网络访问 HuggingFace 较慢，建议设置镜像：

```bash
# Linux/macOS
export HF_ENDPOINT="https://hf-mirror.com"

# Windows PowerShell
$env:HF_ENDPOINT="https://hf-mirror.com"

# Windows CMD
set HF_ENDPOINT=https://hf-mirror.com
```

> **提示**：启动脚本 `run_podcast_webui.py` 会自动设置镜像，无需手动设置。

### 步骤 7：配置 API 密钥

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

### 1. 检查模型文件

确保模型目录存在：

```bash
ls SoulX-Podcast/pretrained_models/SoulX-Podcast-1.7B/
```

### 2. 检查 GPU 支持（可选）

```bash
python -c "import torch; print(f'CUDA可用: {torch.cuda.is_available()}')"
```

### 3. 测试播客系统

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

### Q1: Git-LFS 下载失败

**解决方案：**

1. 确保 Git-LFS 已正确安装：
   ```bash
   git lfs version
   ```

2. 重新初始化 LFS：
   ```bash
   git lfs install
   ```

### Q2: 模型下载失败或很慢

**解决方案：**

1. 设置 HuggingFace 镜像：
   ```bash
   export HF_ENDPOINT="https://hf-mirror.com"
   ```

2. 使用断点续传：
   ```bash
   huggingface-cli download --resume-download Soul-AILab/SoulX-Podcast-1.7B --local-dir SoulX-Podcast/pretrained_models/SoulX-Podcast-1.7B
   ```

### Q3: CUDA 相关错误

**解决方案：**

1. 确保安装了正确版本的 CUDA Toolkit（12.8+）
2. 检查 PyTorch 是否正确识别 GPU：
   ```bash
   python -c "import torch; print(torch.cuda.is_available())"
   ```

3. 如果 GPU 不可用，系统会自动回退到 CPU 模式（速度较慢）

### Q4: 模型加载失败

**解决方案：**

1. 检查模型路径配置是否正确
2. 确保模型文件已完整下载
3. 检查文件权限

### Q5: API 调用失败

**解决方案：**

1. 检查 API 密钥是否正确配置
2. 检查网络连接
3. 查看 API 响应错误信息

## 下一步

安装完成后，请查看：

- [README.md](README.md) - 项目总览和快速开始
- [使用说明.md](使用说明.md) - 详细使用文档
- [部署说明.md](部署说明.md) - 部署指南

## 获取帮助

如果遇到问题：

1. 查看 [SoulX-Podcast 官方文档](https://github.com/Soul-AILab/SoulX-Podcast)
2. 检查错误日志
3. 确保所有依赖版本正确
4. 参考 [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - 故障排查指南

