# 混元AI播客生成系统

基于混元大模型（tencent/Hunyuan-A13B-Instruct）和IndexTTS-2的智能播客音频生成工具。

## 功能特性

本系统实现了"混元AI播客创新智造挑战赛"的三个子题目：

### 1. 多角色自然互动播客音频生成
- 支持通过文本标记（如`[角色A]`、`[角色B]`）区分不同角色
- 自动识别角色并生成对应的播客音频
- 支持多角色间的自然对话和互动

### 2. 自定义角色人设和音色播客生成
- 支持为每个角色设置人设描述
- 支持动态上传音色参考音频
- 根据角色人设生成符合风格的播客对话

### 3. 主题深度播客生成
- 基于指定主题生成有深度、引发思考的播客内容
- 内容有依据、有见地，能够引发听众的深度思考

## 安装要求

### 系统要求

1. Python 3.10+（IndexTTS-2要求）
2. Git 和 Git-LFS
3. CUDA Toolkit 12.8+（如果使用GPU加速）

### 环境设置

#### 1. 安装 Git 和 Git-LFS

确保您的系统上同时具有 git 和 git-lfs。

还必须在当前用户帐户上启用 Git-LFS 插件：

```bash
git lfs install
```

#### 2. 下载 IndexTTS-2 存储库

如果还没有下载 IndexTTS-2，请执行：

```bash
git clone https://github.com/index-tts/index-tts.git && cd index-tts
git lfs pull  # 下载大型仓库文件
```

#### 3. 安装 uv 包管理器

`uv` 是 IndexTTS-2 推荐的包管理器，速度比 pip 快 115 倍。

**快速安装方法：**

```bash
pip install -U uv
```

> **警告**：IndexTTS-2 只支持 `uv` 安装方法。使用 `conda` 或 `pip` 可能导致依赖版本错误、缺少 GPU 加速等问题。

#### 4. 安装 IndexTTS-2 依赖

进入 `index-tts` 目录，安装所需的依赖项：

```bash
cd index-tts
uv sync --all-extras
```

如果下载速度很慢，可以使用国内镜像：

```bash
# 使用阿里云镜像
uv sync --all-extras --default-index "https://mirrors.aliyun.com/pypi/simple"

# 或使用清华镜像
uv sync --all-extras --default-index "https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple"
```

#### 5. 下载 IndexTTS-2 模型文件

下载所需的模型文件：

```bash
# 使用 huggingface-cli
uv tool install "huggingface-hub[cli,hf_xet]"
hf download IndexTeam/IndexTTS-2 --local-dir=checkpoints

# 或使用 modelscope
uv tool install "modelscope"
modelscope download --model IndexTeam/IndexTTS-2 --local_dir checkpoints
```

#### 6. 安装播客系统额外依赖

播客系统需要以下额外依赖（如果使用 uv 环境，这些可能已包含）：

```bash
# 如果使用 pip
pip install requests gradio

# 如果使用 uv（在项目根目录）
uv pip install requests gradio
```

## 配置

### API密钥配置

API密钥已配置在 `hunyuan_podcast/config.py` 中，也可以通过环境变量设置：

```bash
export SILICONFLOW_API_KEY="your-api-key"
```

### IndexTTS-2配置

**重要**：必须下载 IndexTTS-2 模型文件，否则无法运行！

确保IndexTTS-2的模型文件已下载到正确位置：
- 配置文件：`index-tts/checkpoints/config.yaml`
- 模型目录：`index-tts/checkpoints/`

**必需文件**：
- `config.yaml` - 配置文件
- `bpe.model` - BPE 分词模型
- `gpt.pth` - GPT 模型权重（约2-3GB）
- `s2mel.pth` - S2Mel 模型权重（约1-2GB）
- `wav2vec2bert_stats.pt` - Wav2Vec2BERT 统计文件

**下载方法**：

```bash
cd index-tts
# 使用 HuggingFace CLI
hf download IndexTeam/IndexTTS-2 --local-dir=checkpoints
# 或使用 ModelScope（国内用户）
modelscope download --model IndexTeam/IndexTTS-2 --local_dir checkpoints
```

详细下载说明请查看 [DOWNLOAD_MODELS.md](DOWNLOAD_MODELS.md)

### HuggingFace 镜像设置（推荐）

IndexTTS-2 首次运行时会自动下载一些小的模型文件。如果网络访问 HuggingFace 较慢，建议设置镜像：

```bash
# Linux/macOS
export HF_ENDPOINT="https://hf-mirror.com"

# Windows PowerShell
$env:HF_ENDPOINT="https://hf-mirror.com"

# Windows CMD
set HF_ENDPOINT=https://hf-mirror.com
```

> **注意**：启动脚本 `run_podcast_webui.py` 会自动设置镜像。

## 使用方法

### 方式1：使用WebUI界面（推荐用于测试）

### 启动WebUI

**重要**：如果使用 `uv` 环境，需要先激活环境或使用 `uv run`：

```bash
# 方式1：使用启动脚本（推荐）
python run_podcast_webui.py

# 方式2：在 uv 环境中运行
cd index-tts
uv run python ../run_podcast_webui.py

# 方式3：直接运行模块
python -m hunyuan_podcast.webui --port 7861
```

> **注意**：如果 IndexTTS-2 使用 `uv` 管理依赖，建议在 `uv` 环境中运行播客系统。

### 使用WebUI

1. **多角色互动播客**
   - 在文本输入框中输入包含角色标记的文本
   - 为每个角色上传音色参考音频
   - 点击"生成播客"按钮

2. **自定义角色播客**
   - 为每个角色设置名称、人设描述和音色文件
   - 输入播客主题（可选）
   - 点击"生成播客"按钮

3. **主题深度播客**
   - 输入播客主题
   - 为每个角色上传音色文件
   - 选择角色数量和深度级别
   - 点击"生成播客"按钮

### 方式2：使用REST API（推荐用于工作流集成）

#### 启动API服务

```bash
# 安装API依赖
pip install fastapi uvicorn[standard] python-multipart

# 启动API服务
python run_api_server.py --host 0.0.0.0 --port 8000
```

启动后访问：
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

#### 使用工作流插件

```python
from workflow_plugin import HunyuanPodcastPlugin

# 创建插件实例
plugin = HunyuanPodcastPlugin(api_base_url="http://localhost:8000")

# 生成多角色播客
result = plugin.generate_multi_role_podcast(
    text="中科曙光发布640卡超节点，算力密度提升20倍...",
    role_voice_files={
        "角色A": "path/to/voice_a.wav",
        "角色B": "path/to/voice_b.wav"
    },
    output_path="output.wav"
)

if result["success"]:
    print(f"✅ 生成成功！音频文件: {result['data']['audio_path']}")
    print(f"脚本: {result['data']['script']}")
```

详细文档请参考：
- [API快速开始](API_QUICKSTART.md)
- [工作流集成指南](WORKFLOW_INTEGRATION.md)

### 方式3：编程接口

```python
from hunyuan_podcast.podcast_generator import PodcastGenerator

# 初始化生成器
generator = PodcastGenerator()

# 设置角色音色
generator.set_role_voice("角色A", "path/to/voice_a.wav")
generator.set_role_voice("角色B", "path/to/voice_b.wav")

# 生成播客
text = "[角色A]你好 [角色B]你好啊"
output_path = generator.generate_from_text(text)
```

## 项目结构

```
hunyuan_podcast/
├── __init__.py              # 包初始化
├── __main__.py              # 主入口
├── config.py                # 配置文件
├── api_client.py            # 硅基流动API客户端
├── text_processor.py        # 文本处理模块
├── podcast_generator.py     # 播客生成核心模块
├── utils.py                 # 工具函数
└── webui.py                 # WebUI界面
```

## 技术架构

- **混元大模型**：通过硅基流动API调用tencent/Hunyuan-A13B-Instruct生成播客对话文本
- **IndexTTS-2**：将文本转换为高质量语音音频
- **音频合成**：将多角色音频片段合成为完整播客

## 注意事项

1. 确保IndexTTS-2模型文件已正确下载
2. API密钥需要有效且有足够的调用额度
3. 音色参考音频建议使用清晰、无噪音的音频文件
4. 生成的音频文件保存在 `outputs/podcasts/` 目录

## 许可证

本项目基于IndexTTS-2项目开发，请遵循相应的许可证要求。

