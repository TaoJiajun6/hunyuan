# 混元AI播客生成系统 - 快速开始

## 快速启动

### 前置条件

1. **Python 3.10+**（IndexTTS-2要求）
2. **Git 和 Git-LFS** 已安装并配置
3. **CUDA Toolkit 12.8+**（如果使用GPU，推荐）

### 1. 环境设置

#### 安装 Git-LFS（如果未安装）

```bash
git lfs install
```

#### 安装 uv 包管理器

```bash
pip install -U uv
```

#### 安装 IndexTTS-2 依赖

```bash
cd index-tts
uv sync --all-extras
```

如果下载慢，使用国内镜像：

```bash
uv sync --all-extras --default-index "https://mirrors.aliyun.com/pypi/simple"
```

> **提示**：如果看到硬链接警告（`Failed to hardlink files`），这是正常的，不影响使用。如果想抑制警告，可以使用 `uv sync --all-extras --link-mode=copy`。

#### 下载 IndexTTS-2 模型（必需！）

**重要**：模型文件必须下载，否则无法运行！

```bash
# 进入 index-tts 目录
cd index-tts

# 方式1：使用 huggingface-cli（推荐）
uv tool install "huggingface-hub[cli,hf_xet]"
hf download IndexTeam/IndexTTS-2 --local-dir=checkpoints

# 方式2：使用 modelscope（国内用户推荐）
uv tool install "modelscope"
modelscope download --model IndexTeam/IndexTTS-2 --local_dir checkpoints
```

> **提示**：如果下载慢，可以使用 HuggingFace 镜像：
> ```bash
> export HF_ENDPOINT="https://hf-mirror.com"  # Linux/macOS
> # 或
> $env:HF_ENDPOINT="https://hf-mirror.com"  # Windows PowerShell
> ```

**验证下载**：确保 `checkpoints` 目录包含以下文件：
- `config.yaml`
- `bpe.model`
- `gpt.pth`（约2-3GB）
- `s2mel.pth`（约1-2GB）
- `wav2vec2bert_stats.pt`

详细说明请查看 [DOWNLOAD_MODELS.md](DOWNLOAD_MODELS.md)

#### 安装播客系统依赖

```bash
# 返回项目根目录
cd ..

# 如果使用uv环境
uv pip install requests gradio

# 或使用pip（在uv环境中）
pip install requests gradio
```

### 2. 设置 HuggingFace 镜像（推荐）

IndexTTS-2 首次运行时会自动下载一些小的模型文件，如果网络访问 HuggingFace 较慢，建议设置镜像：

```powershell
# Windows PowerShell
$env:HF_ENDPOINT="https://hf-mirror.com"

# Windows CMD
set HF_ENDPOINT=https://hf-mirror.com

# Linux/macOS
export HF_ENDPOINT="https://hf-mirror.com"
```

> **注意**：启动脚本 `run_podcast_webui.py` 会自动设置镜像，但手动运行时需要手动设置。

### 3. 启动WebUI

#### 如果使用 uv 环境（推荐）

```bash
# Linux/macOS
bash run_podcast_webui_uv.sh

# Windows
run_podcast_webui_uv.bat

# 或手动运行
cd index-tts
uv run python ../run_podcast_webui.py
```

#### 如果使用标准 Python 环境

```bash
# 方式1：使用启动脚本
python run_podcast_webui.py

# 方式2：直接运行模块
python -m hunyuan_podcast.webui

# 方式3：指定端口
python -m hunyuan_podcast.webui --port 7861
```

### 4. 访问WebUI

打开浏览器访问：`http://localhost:7861`

## 三个功能标签页

### 📝 多角色互动播客

1. 在文本框中输入包含角色标记的文本，例如：
   ```
   [角色A]大家好，欢迎收听今天的播客。
   [角色B]是的，今天我们要聊一个很有趣的话题。
   ```

2. 为每个角色上传音色参考音频

3. 点击"生成播客"按钮

### 👥 自定义角色播客

1. 为每个角色设置：
   - 角色名称
   - 角色人设描述（例如："一个幽默风趣的主持人"）
   - 音色参考音频

2. 输入播客主题（可选）

3. 点击"生成播客"按钮

### 💡 主题深度播客

1. 输入播客主题（例如："人工智能对人类社会的影响"）

2. 选择角色数量和深度级别

3. 为每个角色上传音色参考音频

4. 点击"生成播客"按钮

## 注意事项

1. **音色文件**：建议使用清晰、无噪音的音频文件（WAV格式）
2. **API密钥**：已配置在 `hunyuan_podcast/config.py` 中
3. **模型文件**：确保IndexTTS-2模型文件已下载到 `index-tts/checkpoints/`
4. **输出目录**：生成的音频保存在 `outputs/podcasts/` 目录

## 故障排除

### 问题1：无法导入IndexTTS2
- 检查 `index-tts` 目录是否存在
- 确认模型文件已下载

### 问题2：API调用失败
- 检查API密钥是否有效
- 确认网络连接正常

### 问题3：音频生成失败
- 检查音色文件路径是否正确
- 确认音色文件格式为WAV

## 技术支持

如有问题，请查看 `README_PODCAST.md` 获取详细文档。

