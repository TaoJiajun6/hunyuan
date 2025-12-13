# 基于混元大模型和SoulX-Podcast的AI播客生成系统

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-orange.svg)](https://pytorch.org/)

基于腾讯混元大模型(Hunyuan-A13B-Instruct)和SoulX-Podcast语音合成技术的智能AI播客生成系统。支持多角色、多风格的智能播客音频自动生成，提供**Web界面(Gradio)**、**React Web应用**、**REST API**和**鸿蒙移动应用**四种使用方式。

## ✨ 核心功能特性

本系统实现了"混元AI播客创新智造挑战赛"的三个子题目，并在此基础上扩展了丰富的实用功能：

### 🎙️ 1. 多角色自然互动播客音频生成

- ✅ 支持通过文本标记(如`[角色A]`、`[角色B]`)区分不同角色
- ✅ 自动识别角色并生成对应的播客音频
- ✅ 支持多角色间的自然对话和互动
- ✅ 支持情绪标注，增强对话表现力(如`[角色A](兴奋地):内容`)
- ✅ 支持多种输入格式：文字、文件、公众号文章、网页URL等
- ✅ 智能数字转中文：自动将数字、日期、价格、技术术语转换为中文读音

### 👥 2. 自定义角色人设和音色播客生成

- ✅ 支持为每个角色设置详细的人设描述(身份、性格、说话风格、口头禅等)
- ✅ 支持动态上传音色参考音频(支持云存储URL)
- ✅ 根据角色人设生成符合风格的播客对话
- ✅ 确保角色人设一致性，风格固化
- ✅ 支持最多4个角色同时参与对话

### 🎯 3. 主题深度播客生成

- ✅ 基于指定主题生成有深度、引发思考的播客内容
- ✅ 支持多维度分析，提供全面视角
- ✅ 引用理论、数据、案例等支撑观点
- ✅ 使用开放式结尾，引导听众继续思考
- ✅ 支持深度级别选择(深度/中等/浅层)
- ✅ 支持1-3个角色参与讨论

### 🚀 4. 高级功能

- ✅ **批量生成**: 支持一次提交最多50个播客生成任务，自动队列管理
- ✅ **智能背景音乐**: AI自动分析播客内容，从云存储或本地选择合适背景音乐
- ✅ **文本分析**: 自动分析文本素材，提取主题、角色、情绪等信息
- ✅ **进度跟踪**: 实时进度查询，支持SSE流式进度推送
- ✅ **云存储集成**: 支持华为AGC云存储，自动上传和管理音频文件
- ✅ **云数据库集成**: 支持华为AGC CloudDB，自动保存播客元数据
- ✅ **任务管理**: 完整的任务队列、状态查询、历史记录功能

## 🚀 快速开始

### 系统要求

1. **Python 3.10+** (SoulX-Podcast要求)
2. **Git 和 Git-LFS** (用于下载模型文件)
3. **CUDA Toolkit 12.8+** (如果使用GPU加速，推荐)
4. **Node.js 16+** (如果使用React Web应用)

### 安装步骤

#### 1. 克隆仓库

```bash
git clone https://github.com/your-username/hunyuan-podcast.git
cd hunyuan
```

#### 2. 安装Python依赖

**使用conda环境(推荐)**

```bash
# 创建conda环境
conda create -n hunyuan python=3.10

# 激活环境
conda activate hunyuan

# 安装依赖
pip install -r requirements_podcast.txt
```

**注意**: 以后每次使用系统前，都需要先激活conda环境: `conda activate hunyuan`

#### 3. 下载模型文件

**下载SoulX-Podcast模型:**

```bash
# 使用HuggingFace CLI
pip install -U huggingface_hub
huggingface-cli download --resume-download Soul-AILab/SoulX-Podcast-1.7B --local-dir SoulX-Podcast/pretrained_models/SoulX-Podcast-1.7B

# 或使用Python
python -c "from huggingface_hub import snapshot_download; snapshot_download('Soul-AILab/SoulX-Podcast-1.7B', local_dir='SoulX-Podcast/pretrained_models/SoulX-Podcast-1.7B')"
```

**配置模型路径:**

模型路径会自动检测，如需手动配置，可在`hunyuan_podcast/config.py`中设置:

```python
SOULX_PODCAST_MODEL_DIR = "SoulX-Podcast/pretrained_models/SoulX-Podcast-1.7B"
```

#### 4. 配置API密钥

**方式一: 使用环境变量(推荐)**

创建`.env`文件(在项目根目录):

```bash
# 混元大模型API配置
HUNYUAN_API_KEY=your-api-key
HUNYUAN_MODEL=hunyuan-a13b  # 可选，默认值
HUNYUAN_FAST_THINKING=True  # 可选，默认开启快思考模式

# 华为AGC云存储配置(可选)
AGC_STORAGE_URL=https://ops-server-drcn.agcstorage.link/v0/
AGC_BUCKET=your-bucket-name
AGC_CLIENT_ID=your-client-id
AGC_CLIENT_SECRET=your-client-secret
AGC_PRODUCT_ID=your-product-id

# 华为AGC云数据库配置(可选)
AGC_API_KEY=your-api-key
AGC_CLOUD_DB_ZONE=cloudDBZone
```

**方式二: 直接在config.py中配置**

在`hunyuan_podcast/config.py`中直接设置:

```python
HUNYUAN_API_KEY = "your-api-key"
```

#### 5. 配置HuggingFace镜像(可选，推荐)

如果网络访问HuggingFace较慢，建议设置镜像:

```bash
# Linux/macOS
export HF_ENDPOINT="https://hf-mirror.com"

# Windows PowerShell
$env:HF_ENDPOINT="https://hf-mirror.com"

# Windows CMD
set HF_ENDPOINT=https://hf-mirror.com
```

系统启动脚本会自动设置此镜像。

## 📖 使用方法

### 方式1: 使用Gradio Web UI界面(推荐用于快速测试)

#### 启动Web UI

```bash
# 使用启动脚本(推荐)
python run_podcast_webui.py

# 或直接运行模块
python -m hunyuan_podcast.webui --port 7861
```

启动后访问: `http://localhost:7861`

#### 使用Web UI

1. **多角色互动播客**
   - 选择输入类型(文字/文件/公众号/网页等)
   - 输入文本内容或上传文件/URL
   - 为每个角色上传音色参考音频
   - 点击"生成播客"按钮

2. **自定义角色播客**
   - 输入文本素材(必需)
   - 为每个角色设置名称、人设描述和音色文件
   - 输入播客主题(可选)
   - 点击"生成播客"按钮

3. **主题深度播客**
   - 输入播客主题
   - 选择角色数量和深度级别
   - 为每个角色选择音色文件
   - 点击"生成播客"按钮

### 方式2: 使用React Web应用(推荐用于生产环境)

#### 安装和启动

```bash
cd web
npm install
npm run dev
```

应用将在 `http://localhost:3000` 启动。

#### 配置API地址

创建`web/.env`文件(可选，默认使用云服务器):

```env
VITE_API_BASE_URL=http://localhost:8000
```

#### 功能特性

- 🎨 现代化UI设计，响应式布局
- 📊 实时进度显示
- 🎵 内置音频播放器
- 📁 文件上传到云存储

详细说明请参考: [web/README.md](web/README.md)

### 方式3: 使用REST API(推荐用于工作流集成)

#### 启动API服务

```bash
# 基本启动(自动检测GPU并启用优化)
python run_api_server.py --host 0.0.0.0 --port 8000

# 启用多进程模式(支持并发处理进度查询)
python run_api_server.py --host 0.0.0.0 --port 8000 --workers 2

# 禁用FP16(如果GPU不支持)
python run_api_server.py --host 0.0.0.0 --port 8000 --no-fp16

# 禁用CUDA内核加速
python run_api_server.py --host 0.0.0.0 --port 8000 --no-cuda-kernel
```

**启动参数说明**:
- `--host`: 服务主机地址，默认0.0.0.0(允许外部访问)
- `--port`: 服务端口，默认8000
- `--fp16`: 启用FP16精度（GPU加速，检测到GPU时默认启用）
- `--no-fp16`: 禁用FP16精度
- `--cuda_kernel`: 启用CUDA内核加速（GPU加速，检测到GPU时默认启用）
- `--no-cuda-kernel`: 禁用CUDA内核加速
- `--workers`: 工作进程数，>=2时可并发处理进度查询

**注意**: 系统会自动检测GPU，并在可用时启用FP16和CUDA内核加速，通常无需手动指定这些参数。

启动后访问:
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health
- **根路径**: http://localhost:8000/

#### 主要API端点

**生成播客:**
- `POST /api/v1/podcast/multi_role` - 多角色互动播客
- `POST /api/v1/podcast/character` - 自定义角色播客
- `POST /api/v1/podcast/deep` - 主题深度播客
- `POST /api/v1/podcast/batch` - 批量生成播客

**辅助功能:**
- `POST /api/v1/podcast/analyze` - 分析文本素材
- `POST /api/v1/podcast/generate_cover` - 生成播客封面
- `POST /api/v1/podcast/upload_voice` - 上传音色文件

**任务管理:**
- `GET /api/v1/podcast/progress/{job_id}` - 查询任务进度
- `GET /api/v1/podcast/progress/{job_id}/stream` - 流式进度推送(SSE)
- `GET /api/v1/podcast/task/{task_id}` - 查询任务详情
- `GET /api/v1/podcast/tasks` - 列出所有任务
- `GET /api/v1/podcast/history` - 获取历史记录

#### 使用示例

**生成多角色播客:**

```bash
curl -X POST "http://localhost:8000/api/v1/podcast/multi_role" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "[角色A]你好,欢迎收听本期播客! [角色B]你好啊!",
    "role_voice_urls": {
      "角色A": "https://cloud-storage-url/voice1.wav",
      "角色B": "https://cloud-storage-url/voice2.wav"
    },
    "category": "科技",
    "silence_interval": 800,
    "background_volume": 0.3
  }'
```

**批量生成播客:**

```bash
curl -X POST "http://localhost:8000/api/v1/podcast/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "tasks": [
      {
        "task_type": "multi_role",
        "request_data": {
          "text": "[角色A]你好 [角色B]你好",
          "role_voice_urls": {...}
        }
      },
      {
        "task_type": "deep",
        "request_data": {
          "topic": "AI的未来",
          "role_voice_urls": {...}
        }
      }
    ]
  }'
```

详细API文档请参考: [API_QUICKSTART.md](API_QUICKSTART.md)

### 方式4: 使用编程接口

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
print(f"生成成功!音频文件: {output_path}")
```

### 方式5: 使用鸿蒙移动应用

#### 配置后端API地址

在`podcasters/components/lib_api/src/main/ets/services/PodcastService.ets`中配置:

```typescript
export class PodcastConfig {
  // 使用Cloud Studio端口转发地址(推荐)
  static readonly API_BASE_URL: string = 'https://${SPACE_KEY}--8000.${REGION}.cloudstudio.work';
  // 或使用本地/其他服务器地址
  // static readonly API_BASE_URL: string = 'http://your-api-server:8000';
  static readonly API_TIMEOUT: number = 600000; // 10分钟超时
  static readonly USE_CLOUD_STORAGE: boolean = true; // 使用云存储
}
```

#### 使用Cloud Studio(推荐)

1. 在腾讯云Cloud Studio中部署API服务器
2. 获取端口转发地址(格式: `https://${SPACE_KEY}--8000.${REGION}.cloudstudio.work`)
3. 在APP中配置API地址

详细说明请参考: [部署说明.md](部署说明.md)

#### 编译运行APP

1. 使用DevEco Studio打开`podcasters`目录
2. 配置签名和API地址
3. 编译运行应用

详细说明请参考: [鸿蒙APP使用说明](podcasters/PODCAST_README.md)

## 📁 项目结构

```
hunyuan/
├── hunyuan_podcast/              # 核心代码模块
│   ├── __init__.py
│   ├── config.py                 # 配置文件
│   ├── api_client.py             # 混元大模型API客户端
│   ├── text_processor.py         # 文本处理模块(数字转中文等)
│   ├── input_processor.py       # 输入格式处理(文件/网页/公众号等)
│   ├── podcast_generator.py     # 播客生成核心模块
│   ├── soulx_tts.py             # SoulX-Podcast TTS包装
│   ├── music_selector.py        # 背景音乐自动选择
│   ├── cloud_storage_music.py   # 云存储音乐客户端
│   ├── agc_database.py          # AGC云数据库客户端
│   ├── upload_client.py         # 文件上传客户端
│   ├── utils.py                 # 工具函数
│   ├── log_config.py            # 日志配置
│   ├── webui.py                 # Gradio Web UI界面
│   ├── api_server.py            # REST API服务
│   └── web/                     # 静态Web文件
├── SoulX-Podcast/                # SoulX-Podcast模型
│   ├── pretrained_models/       # 模型文件目录
│   ├── api/                     # API服务
│   └── ...
├── web/                          # React Web应用
│   ├── src/                     # 源代码
│   │   ├── components/          # 组件
│   │   ├── pages/               # 页面
│   │   ├── services/            # API服务
│   │   └── utils/               # 工具函数
│   ├── package.json
│   └── ...
├── podcasters/                   # 鸿蒙移动应用
│   ├── components/              # 组件库
│   ├── products/                # 产品配置
│   └── ...
├── outputs/                      # 输出目录
│   └── podcasts/                # 生成的播客音频
├── tools/                        # 工具脚本
│   ├── upload_music_to_cloud.py # 上传音乐到云存储
│   └── ...
├── run_podcast_webui.py         # Web UI启动脚本
├── run_api_server.py            # API服务启动脚本
├── requirements_podcast.txt     # Python依赖
├── README.md                     # 本文件
├── 技术报告.md                   # 技术报告
├── 使用说明.md                   # 使用说明
├── 部署说明.md                   # 部署说明
└── ...
```

## 🔧 配置说明

### API配置

**混元大模型API配置:**

在`.env`文件或`hunyuan_podcast/config.py`中配置:

```python
# 混元大模型API配置
HUNYUAN_API_KEY = "your-api-key"  # 从 https://console.cloud.tencent.com/hunyuan/start 获取
HUNYUAN_API_BASE = "https://api.hunyuan.cloud.tencent.com/v1"
HUNYUAN_MODEL = "hunyuan-a13b"  # 默认使用 hunyuan-a13b
HUNYUAN_FAST_THINKING = True  # 快思考模式，提升速度
```

### 模型配置

```python
# SoulX-Podcast配置
SOULX_PODCAST_MODEL_DIR = "SoulX-Podcast/pretrained_models/SoulX-Podcast-1.7B"
SOULX_PODCAST_LLM_ENGINE = "hf"  # 仅支持 "hf" 引擎（vllm 支持已移除）
SOULX_PODCAST_FP16_FLOW = True  # 使用FP16精度（GPU加速，默认启用）
```

**注意**: 系统仅支持HuggingFace引擎，vllm支持已移除。如果环境变量设置为"vllm"，代码会自动转换为"hf"。

### 音频配置

```python
# 音频合成配置
AUDIO_SILENCE_INTERVAL = 800  # 角色切换时的静音间隔(毫秒)，默认800ms以保持对话流畅自然
AUDIO_SAMPLING_RATE = 22050   # 采样率(Hz)
```

### 云存储配置(可选)

```bash
# 华为AGC云存储配置
AGC_STORAGE_URL=https://ops-server-drcn.agcstorage.link/v0/
AGC_BUCKET=your-bucket-name
AGC_CLIENT_ID=your-client-id
AGC_CLIENT_SECRET=your-client-secret
AGC_PRODUCT_ID=your-product-id

# 云存储音乐文件夹路径
CLOUD_STORAGE_MUSIC_PATH=music/
```

### 云数据库配置(可选)

```bash
# 华为AGC云数据库配置
AGC_API_KEY=your-api-key  # 服务端API Key
AGC_PRODUCT_ID=your-product-id
AGC_CLOUD_DB_ZONE=cloudDBZone
```

详细配置说明请参考:
- [ENV_CONFIG.md](ENV_CONFIG.md) - 环境变量配置
- [CLOUD_MUSIC_CONFIG.md](CLOUD_MUSIC_CONFIG.md) - 云存储音乐配置
- [CLOUDDB_SETUP.md](CLOUDDB_SETUP.md) - 云数据库配置

## 📚 文档

### 核心文档

- [技术报告](技术报告.md) - 详细的技术报告，包含研究背景、方法论、实验设计等
- [使用说明.md](使用说明.md) - 详细的使用说明和使用示例
- [部署说明.md](部署说明.md) - 完整部署说明(包含Cloud Studio部署)
- [文档索引.md](文档索引.md) - 所有文档的索引

### 功能文档

- [API_QUICKSTART.md](API_QUICKSTART.md) - API快速开始指南
- [API_STATUS.md](API_STATUS.md) - API状态说明
- [BATCH_PODCAST_GUIDE.md](BATCH_PODCAST_GUIDE.md) - 批量播客生成指南

### 移动应用文档

- [podcasters/PODCAST_README.md](podcasters/PODCAST_README.md) - 鸿蒙APP使用说明
- [podcasters/QUICK_START.md](podcasters/QUICK_START.md) - 鸿蒙APP快速开始

### Web应用文档

- [web/README.md](web/README.md) - React Web应用说明
- [web/QUICK_START.md](web/QUICK_START.md) - Web应用快速开始

### 配置和故障排查

- [INSTALL.md](INSTALL.md) - 完整安装指南
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - 故障排查指南
- [ENV_CONFIG.md](ENV_CONFIG.md) - 环境变量配置
- [CLOUD_MUSIC_CONFIG.md](CLOUD_MUSIC_CONFIG.md) - 云存储音乐配置
- [CLOUDDB_SETUP.md](CLOUDDB_SETUP.md) - 云数据库配置

## 🎯 技术架构

### 核心设计理念

**工作流程**: 文本/素材 → 混元大模型生成脚本 → 音色/背景 → TTS 合成 → 音频输出

**四大设计原则**:
1. **用户友好原则**: 降低使用门槛、透明化过程、容错设计
2. **技术实用原则**: 选用成熟技术栈、平衡质量与速度、资源高效利用
3. **系统健壮原则**: 分层防御、异步解耦、监控可观测
4. **扩展开放原则**: 模块化设计、标准化接口、配置驱动

### 核心组件

- **混元大模型**: 通过腾讯云API调用Hunyuan-A13B-Instruct生成播客对话文本
- **SoulX-Podcast**: 将文本转换为高质量语音音频，支持零样本音色克隆
- **音频合成**: 将多角色音频片段合成为完整播客，支持背景音乐混合
- **智能处理**: 数字转中文、文本分析、音乐自动选择等

### 服务层

- **后端服务**: FastAPI构建的REST API服务，支持异步处理和流式响应
- **Web界面**: 
  - Gradio构建的快速原型Web UI
  - React构建的现代化Web应用
- **移动应用**: HarmonyOS原生开发的移动应用
- **云端部署**: 支持腾讯云Cloud Studio部署后端服务

### 数据存储

- **本地存储**: 文件系统存储生成的音频文件
- **云存储**: 华为AGC云存储管理音频文件和背景音乐
- **云数据库**: 华为AGC CloudDB保存播客元数据和历史记录

### 高级特性

- **批量处理**: 任务队列管理，支持并发控制
- **进度跟踪**: 实时进度查询和SSE流式推送
- **智能选择**: AI自动分析内容，选择合适背景音乐

## 🔍 功能演示

### 多角色互动播客

**输入文本:**
```
[角色A]你好,欢迎收听本期播客!
[角色B]你好!今天我们要聊什么话题呢?
[角色A]今天我们来聊聊AI技术的发展。
[角色B](兴奋地)这个话题很有意思!
```

**生成效果:**
- 自动识别两个角色
- 为每个角色生成对应的语音
- 识别情绪标注并体现在语音中
- 合成为完整的播客音频
- 自动添加合适的背景音乐

### 自定义角色人设播客

**输入角色人设:**
- 角色A: 外向幽默,语速较快,常用网络流行语,身份是科技博主
- 角色B: 理性严谨,语速平稳,逻辑性强,身份是AI研究员

**生成效果:**
- 根据角色人设生成符合风格的对话
- 确保角色人设一致性
- 生成自然流畅的播客音频
- 对话内容符合角色身份和性格

### 主题深度播客

**输入主题:** "AI与人类的关系"

**生成效果:**
- 从多个维度分析主题(技术、伦理、社会影响等)
- 引用理论、数据、案例等支撑观点
- 使用开放式结尾,引导听众继续思考
- 生成有深度的播客内容

## ⚠️ 注意事项

1. **模型文件**: 确保SoulX-Podcast模型文件已正确下载(约3.5GB)
2. **API密钥**: 确保混元大模型API密钥有效且有足够的调用额度（从 https://console.cloud.tencent.com/hunyuan/start 获取）
3. **音色文件**: 
   - 格式: WAV格式(推荐)，也支持MP3等常见格式
   - 时长: 5-30秒（推荐20-30秒）
   - 大小: 最大50MB（服务器端限制）
   - 质量: 清晰、无噪音的音频文件效果更好
   - 上传: 必须先上传到云存储，获取URL后使用
4. **GPU支持**: 推荐使用GPU加速，提高生成速度（系统会自动检测并启用优化）
5. **网络连接**: 确保网络连接正常，能够访问API服务和云存储
6. **conda环境**: 推荐使用conda环境管理依赖，避免环境冲突
7. **并发控制**: 批量生成时注意GPU显存，可通过`MAX_CONCURRENT_PODCAST_TASKS`环境变量控制（默认最多2个并发任务）

## 🐛 故障排查

### 常见问题

1. **模型加载失败**
   - 检查模型文件是否已下载
   - 检查模型路径配置是否正确
   - 检查CUDA是否可用(如果使用GPU)
   - 查看日志文件获取详细错误信息

2. **API调用失败**
   - 检查API密钥是否有效
   - 检查网络连接是否正常
   - 检查API调用额度是否充足
   - 查看API响应日志

3. **音频生成失败**
   - 检查音色文件格式是否正确
   - 检查音色文件大小是否超出限制
   - 检查文本格式是否正确
   - 查看TTS生成日志

4. **移动应用连接失败**
   - 检查API服务器地址配置是否正确
   - 检查网络连接是否正常
   - 检查防火墙设置
   - 检查Cloud Studio端口转发配置

5. **云存储/云数据库连接失败**
   - 检查环境变量配置是否正确
   - 检查API Key或Client ID/Secret是否有效
   - 检查网络连接是否正常
   - 查看相关配置文档

详细故障排查指南请参考: [故障排查指南](TROUBLESHOOTING.md)

## 📄 许可证

本项目基于Apache 2.0许可证发布。请遵循相应的许可证要求。

## 🙏 致谢

感谢以下组织和技术支持：

- **开放原子大赛组委会** - 提供比赛平台和指导
- **腾讯云** - 提供混元大模型API和Cloud Studio平台支持
- **华为云** - 提供AGC云存储和CloudDB服务支持
- [混元大模型](https://cloud.tencent.com/product/hunyuan) - 腾讯混元大模型
- [SoulX-Podcast](https://github.com/Soul-AILab/SoulX-Podcast) - SoulX-Podcast语音合成模型
- [FastAPI](https://fastapi.tiangolo.com) - FastAPI Web框架
- [Gradio](https://gradio.app) - Gradio Web UI框架
- [React](https://react.dev) - React UI框架
- [HarmonyOS](https://developer.harmonyos.com) - 华为HarmonyOS开发框架
- [华为AGC](https://developer.huawei.com/consumer/cn/service/josp/agc/index.html) - 华为应用云服务


## 📮 联系方式

如有问题或建议，请通过以下方式联系:

- **Email**: gavintao@petalmail.com

## 🔄 更新日志

### v1.1.0 (2025-12)

- ✅ 新增React Web应用
- ✅ 实现批量播客生成功能
- ✅ 实现文本分析功能
- ✅ 实现智能背景音乐选择
- ✅ 支持多种输入格式(文件/网页/公众号/PDF/Word)
- ✅ 集成华为AGC云存储和云数据库
- ✅ 完善任务管理和进度跟踪
- ✅ 优化GPU自动检测和配置
- ✅ 更新为使用conda环境管理依赖
- ✅ 优化API配置（腾讯云混元API直接调用）
- ✅ 更新模型配置（仅支持hf引擎）

### v1.0.0 (2025-11)

- ✅ 实现多角色互动播客生成功能
- ✅ 实现自定义角色人设播客生成功能
- ✅ 实现主题深度播客生成功能
- ✅ 实现Gradio Web UI界面
- ✅ 实现REST API服务
- ✅ 实现鸿蒙移动应用
- ✅ 支持Cloud Studio云端部署
- ✅ 支持华为AGC云存储

---

**开发团队**: 谁更像AI团队（成都锦城学院开放原子开源社团）

**项目背景**: 2025开放原子大赛 - 腾讯混元AI播客创新智造挑战赛

---

**最后更新**: 2025年12月
