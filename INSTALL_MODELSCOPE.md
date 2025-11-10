# 在Linux下安装ModelScope

## ⚡ 快速解决方案（推荐）

如果你在 conda base 环境或标准 Python 环境中，直接使用 pip 安装：

```bash
# 安装 modelscope（推荐使用指定版本）
pip install modelscope==1.27.0

# 验证安装
python -c "import modelscope; print('ModelScope安装成功！版本:', modelscope.__version__)"

# 运行下载脚本
python download_model.py
```

## 方式 1：使用 pip 安装（标准Python环境）

```bash
# 安装 modelscope
pip install modelscope

# 或者指定版本（推荐）
pip install modelscope==1.27.0

# 如果遇到权限问题，使用 --user
pip install --user modelscope==1.27.0
```

## 方式 2：使用 uv 环境（需要先安装 uv）

### 2.1 安装 uv 工具

如果系统中没有 `uv`，需要先安装：

```bash
# 使用 curl 安装 uv（推荐）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或者使用 pip 安装
pip install uv

# 安装后重新加载 shell 配置
source ~/.bashrc
# 或
source ~/.zshrc
```

### 2.2 使用 uv 安装 modelscope

```bash
# 进入 index-tts 目录
cd index-tts

# 同步所有依赖（包括 modelscope）
uv sync --all-extras

# 或单独安装 modelscope
uv pip install modelscope==1.27.0
```

然后使用 uv 环境运行：

```bash
# 使用 uv run 运行脚本
uv run python download_model.py

# 或者激活环境后运行
source .venv/bin/activate
python download_model.py
```

## 方式 3：在 uv 环境中单独安装 modelscope

```bash
# 进入 index-tts 目录
cd index-tts

# 在 uv 环境中安装 modelscope
uv pip install modelscope==1.27.0

# 或者使用 uv add
uv add modelscope==1.27.0
```

## 方式 4：使用 uv tool 安装（命令行工具）

```bash
# 安装 modelscope 命令行工具
uv tool install "modelscope"

# 然后可以直接使用 modelscope 命令下载模型
modelscope download --model IndexTeam/IndexTTS-2 --local_dir checkpoints
```

## 验证安装

安装完成后，可以验证 modelscope 是否安装成功：

```bash
# 检查 modelscope 是否可导入
python -c "import modelscope; print(modelscope.__version__)"

# 或者检查命令行工具
modelscope --version
```

## 常见问题

### 问题 1：在 conda base 环境中

如果你在 conda 的 base 环境中，建议：

1. **创建独立的 conda 环境**（推荐）：
```bash
conda create -n index-tts python=3.10
conda activate index-tts
pip install modelscope==1.27.0
```

2. **或者在 base 环境中直接安装**：
```bash
pip install modelscope==1.27.0
```

### 问题 2：权限问题

如果遇到权限问题，可以使用 `--user` 参数：

```bash
pip install --user modelscope==1.27.0
```

### 问题 3：网络问题（国内用户）

如果下载模型时遇到网络问题，ModelScope 对国内用户更友好，应该可以正常使用。

## 🚀 快速解决当前问题

### 情况 1：uv 命令未找到（你当前的情况）

**最简单的方法 - 使用 pip 安装：**

```bash
# 在 /workspace/hunyuan/index-tts 目录下
cd /workspace/hunyuan/index-tts

# 直接使用 pip 安装（conda base 环境支持）
pip install modelscope==1.27.0

# 验证安装
python -c "import modelscope; print('安装成功！')"

# 运行下载脚本
python ../hunyuan_podcast/download_model.py
# 或者如果在 index-tts 目录下有 download_model.py
python download_model.py
```

### 情况 2：想要使用 uv 环境

**先安装 uv，然后使用 uv：**

```bash
# 1. 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# 2. 进入 index-tts 目录
cd /workspace/hunyuan/index-tts

# 3. 同步依赖
uv sync --all-extras

# 4. 运行脚本
uv run python download_model.py
```

### 情况 3：在 conda 环境中

**创建独立的 conda 环境（推荐）：**

```bash
# 创建新环境
conda create -n index-tts python=3.10
conda activate index-tts

# 安装 modelscope
pip install modelscope==1.27.0

# 运行脚本
python download_model.py
```

