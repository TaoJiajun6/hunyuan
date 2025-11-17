# 基于混元大模型和SoulX-Podcast的AI播客生成系统

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-orange.svg)](https://pytorch.org/)

基于腾讯混元大模型(Hunyuan-A13B-Instruct)和SoulX-Podcast语音合成技术的智能AI播客生成系统。支持多角色、多风格的智能播客音频自动生成,提供Web界面、REST API和鸿蒙移动应用三种使用方式。

## ✨ 功能特性

本系统实现了"混元AI播客创新智造挑战赛"的三个子题目:

### 1. 多角色自然互动播客音频生成

- 支持通过文本标记(如`[角色A]`、`[角色B]`)区分不同角色
- 自动识别角色并生成对应的播客音频
- 支持多角色间的自然对话和互动
- 支持情绪标注,增强对话表现力

### 2. 自定义角色人设和音色播客生成

- 支持为每个角色设置详细的人设描述(身份、性格、说话风格等)
- 支持动态上传音色参考音频
- 根据角色人设生成符合风格的播客对话
- 确保角色人设一致性,风格固化

### 3. 主题深度播客生成

- 基于指定主题生成有深度、引发思考的播客内容
- 支持多维度分析,提供全面视角
- 引用理论、数据、案例等支撑观点
- 使用开放式结尾,引导听众继续思考

## 🚀 快速开始

### 系统要求

1. **Python 3.10+** (SoulX-Podcast要求)
2. **Git 和 Git-LFS** (用于下载模型文件)
3. **CUDA Toolkit 12.8+** (如果使用GPU加速,推荐)

### 安装步骤

#### 1. 克隆仓库

```bash
git clone https://github.com/your-username/hunyuan-podcast.git
cd hunyuan-podcast
```

#### 2. 安装依赖

**方式一: 使用pip(推荐)**

```bash
pip install -r requirements_podcast.txt
```

**方式二: 使用uv(如果需要使用SoulX-Podcast的uv环境)**

```bash
# 安装uv
pip install -U uv

# 进入SoulX-Podcast目录
cd SoulX-Podcast
uv sync --all-extras
```

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

在`hunyuan_podcast/config.py`中配置模型路径:

```python
SOULX_PODCAST_MODEL_DIR = "SoulX-Podcast/pretrained_models/SoulX-Podcast-1.7B"
```

#### 4. 配置API密钥

在`hunyuan_podcast/config.py`中配置API密钥:

```python
SILICONFLOW_API_KEY = "your-api-key"  # 从 https://cloud.siliconflow.cn 获取
```

或使用环境变量:

```bash
export SILICONFLOW_API_KEY="your-api-key"
```

#### 5. 配置HuggingFace镜像(可选,推荐)

如果网络访问HuggingFace较慢,建议设置镜像:

```bash
# Linux/macOS
export HF_ENDPOINT="https://hf-mirror.com"

# Windows PowerShell
$env:HF_ENDPOINT="https://hf-mirror.com"

# Windows CMD
set HF_ENDPOINT=https://hf-mirror.com
```

## 📖 使用方法

### 方式1: 使用Web UI界面(推荐用于测试)

#### 启动Web UI

```bash
# 方式1: 使用启动脚本(推荐)
python run_podcast_webui.py

# 方式2: 直接运行模块
python -m hunyuan_podcast.webui --port 7861
```

启动后访问: `http://localhost:7861`

#### 使用Web UI

1. **多角色互动播客**
   - 在文本输入框中输入包含角色标记的文本
   - 为每个角色上传音色参考音频
   - 点击"生成播客"按钮

2. **自定义角色播客**
   - 为每个角色设置名称、人设描述和音色文件
   - 输入播客主题(可选)
   - 点击"生成播客"按钮

3. **主题深度播客**
   - 输入播客主题
   - 选择角色数量和深度级别
   - 为每个角色选择音色文件
   - 点击"生成播客"按钮

### 方式2: 使用REST API(推荐用于工作流集成)

#### 启动API服务

```bash
# 安装API依赖
pip install fastapi uvicorn[standard] python-multipart

# 启动API服务
python run_api_server.py --host 0.0.0.0 --port 8000
```

启动后访问:
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

#### 使用API

**生成多角色播客:**

```bash
curl -X POST "http://localhost:8000/api/v1/podcast/multi-role" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "[角色A]你好 [角色B]你好啊",
    "role_voices": {
      "角色A": "base64_encoded_audio_data",
      "角色B": "base64_encoded_audio_data"
    }
  }'
```

**生成自定义角色播客:**

```bash
curl -X POST "http://localhost:8000/api/v1/podcast/character" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "AI技术的发展",
    "characters": [
      {
        "name": "角色A",
        "personality": "外向幽默",
        "speaking_style": "语速较快,常用网络流行语",
        "voice": "base64_encoded_audio_data"
      }
    ]
  }'
```

**生成主题深度播客:**

```bash
curl -X POST "http://localhost:8000/api/v1/podcast/deep" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "AI与人类的关系",
    "depth_level": "深度",
    "num_characters": 2,
    "role_voices": {
      "角色A": "base64_encoded_audio_data",
      "角色B": "base64_encoded_audio_data"
    }
  }'
```

### 方式3: 使用编程接口

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

### 方式4: 使用鸿蒙移动应用

#### 配置后端API地址

在`podcasters/components/lib_api/src/main/ets/services/PodcastService.ets`中配置:

```typescript
export class PodcastConfig {
  static readonly API_BASE_URL: string = 'http://your-api-server:8000';
  static readonly API_TIMEOUT: number = 600000; // 10分钟超时
  static readonly USE_CLOUD_FUNCTION: boolean = false;
}
```

#### 使用Cloud Studio(推荐)

1. 在腾讯云Cloud Studio中部署API服务器
2. 获取端口转发地址(格式: `https://${SPACE_KEY}--8000.${REGION}.cloudstudio.work`)
3. 在APP中配置API地址

详细说明请参考: [Cloud Studio部署指南](CLOUD_STUDIO_DEPLOYMENT.md)

#### 编译运行APP

1. 使用DevEco Studio打开`podcasters`目录
2. 配置签名和API地址
3. 编译运行应用

详细说明请参考: [鸿蒙APP使用说明](podcasters/PODCAST_README.md)

## 📁 项目结构

```
hunyuan-podcast/
├── hunyuan_podcast/          # 核心代码模块
│   ├── __init__.py
│   ├── config.py             # 配置文件
│   ├── api_client.py         # 混元大模型API客户端
│   ├── text_processor.py     # 文本处理模块
│   ├── podcast_generator.py  # 播客生成核心模块
│   ├── soulx_tts.py         # SoulX-Podcast TTS包装
│   ├── utils.py             # 工具函数
│   ├── webui.py             # Web UI界面
│   └── api_server.py        # REST API服务
├── SoulX-Podcast/            # SoulX-Podcast模型
│   ├── pretrained_models/   # 模型文件目录
│   └── ...
├── podcasters/               # 鸿蒙移动应用
│   ├── components/          # 组件库
│   ├── products/            # 产品配置
│   └── ...
├── outputs/                  # 输出目录
│   └── podcasts/            # 生成的播客音频
├── run_podcast_webui.py     # Web UI启动脚本
├── run_api_server.py        # API服务启动脚本
├── requirements_podcast.txt # Python依赖
├── README.md                # 本文件
├── 技术报告.md              # 技术报告
└── ...
```

## 🔧 配置说明

### API配置

在`hunyuan_podcast/config.py`中配置:

```python
# 硅基流动API配置
SILICONFLOW_API_KEY = "your-api-key"
SILICONFLOW_API_BASE = "https://api.siliconflow.cn/v1"
SILICONFLOW_MODEL = "tencent/Hunyuan-A13B-Instruct"
```

### 模型配置

```python
# SoulX-Podcast配置
SOULX_PODCAST_MODEL_DIR = "SoulX-Podcast/pretrained_models/SoulX-Podcast-1.7B"
SOULX_PODCAST_LLM_ENGINE = "hf"  # 或 "vllm"
SOULX_PODCAST_FP16_FLOW = False  # 或 True
```

### 音频配置

```python
# 音频合成配置
AUDIO_SILENCE_INTERVAL = 300  # 角色切换时的静音间隔(毫秒)
AUDIO_SAMPLING_RATE = 22050   # 采样率(Hz)
```

## 📚 文档

- [技术报告](技术报告.md) - 详细的技术报告,包含研究背景、方法论、实验设计等
- [快速开始指南](QUICKSTART.md) - 快速开始指南
- [API文档](API_QUICKSTART.md) - API使用文档
- [工作流集成指南](WORKFLOW_INTEGRATION.md) - 工作流集成指南
- [Cloud Studio部署指南](CLOUD_STUDIO_DEPLOYMENT.md) - Cloud Studio部署指南
- [鸿蒙APP使用说明](podcasters/PODCAST_README.md) - 鸿蒙APP使用说明
- [故障排查指南](TROUBLESHOOTING.md) - 故障排查指南

## 🎯 技术架构

- **混元大模型**: 通过硅基流动API调用tencent/Hunyuan-A13B-Instruct生成播客对话文本
- **SoulX-Podcast**: 将文本转换为高质量语音音频
- **音频合成**: 将多角色音频片段合成为完整播客
- **后端服务**: FastAPI构建的REST API服务
- **Web界面**: Gradio构建的Web UI界面
- **移动应用**: HarmonyOS原生开发的移动应用
- **云端部署**: 腾讯云Cloud Studio部署后端服务
- **云存储**: 华为AGC云存储管理音频文件

## 🔍 功能演示

### 多角色互动播客

输入文本:
```
[角色A]你好,欢迎收听本期播客!
[角色B]你好!今天我们要聊什么话题呢?
[角色A]今天我们来聊聊AI技术的发展。
```

生成效果:
- 自动识别两个角色
- 为每个角色生成对应的语音
- 合成为完整的播客音频

### 自定义角色人设播客

输入角色人设:
- 角色A: 外向幽默,语速较快,常用网络流行语
- 角色B: 理性严谨,语速平稳,逻辑性强

生成效果:
- 根据角色人设生成符合风格的对话
- 确保角色人设一致性
- 生成自然流畅的播客音频

### 主题深度播客

输入主题: "AI与人类的关系"

生成效果:
- 从多个维度分析主题
- 引用理论、数据、案例等支撑观点
- 使用开放式结尾,引导听众继续思考

## ⚠️ 注意事项

1. **模型文件**: 确保SoulX-Podcast模型文件已正确下载
2. **API密钥**: 确保API密钥有效且有足够的调用额度
3. **音色文件**: 音色参考音频建议使用清晰、无噪音的音频文件(WAV格式,5-30秒)
4. **GPU支持**: 推荐使用GPU加速,提高生成速度
5. **网络连接**: 确保网络连接正常,能够访问API服务
6. **文件大小**: 音色文件大小限制为10MB(客户端)或50MB(服务器)

## 🐛 故障排查

### 常见问题

1. **模型加载失败**
   - 检查模型文件是否已下载
   - 检查模型路径配置是否正确
   - 检查CUDA是否可用(如果使用GPU)

2. **API调用失败**
   - 检查API密钥是否有效
   - 检查网络连接是否正常
   - 检查API调用额度是否充足

3. **音频生成失败**
   - 检查音色文件格式是否正确
   - 检查音色文件大小是否超出限制
   - 检查文本格式是否正确

4. **移动应用连接失败**
   - 检查API服务器地址配置是否正确
   - 检查网络连接是否正常
   - 检查防火墙设置

详细故障排查指南请参考: [故障排查指南](TROUBLESHOOTING.md)

## 📄 许可证

本项目基于Apache 2.0许可证发布。请遵循相应的许可证要求。

## 🙏 致谢

- [混元大模型](https://cloud.tencent.com/product/hunyuan) - 腾讯混元大模型
- [SoulX-Podcast](https://github.com/Soul-AILab/SoulX-Podcast) - SoulX-Podcast语音合成模型
- [硅基流动](https://cloud.siliconflow.cn) - 硅基流动API平台
- [FastAPI](https://fastapi.tiangolo.com) - FastAPI Web框架
- [Gradio](https://gradio.app) - Gradio Web UI框架
- [HarmonyOS](https://developer.harmonyos.com) - 华为HarmonyOS开发框架

## 📮 联系方式

如有问题或建议,请通过以下方式联系:

- **Issues**: [GitHub Issues](https://github.com/your-username/hunyuan-podcast/issues)
- **Email**: (请填写联系方式)

## 🔄 更新日志

### v1.0.0 (2025-01)

- ✅ 实现多角色互动播客生成功能
- ✅ 实现自定义角色人设播客生成功能
- ✅ 实现主题深度播客生成功能
- ✅ 实现Web UI界面
- ✅ 实现REST API服务
- ✅ 实现鸿蒙移动应用
- ✅ 支持Cloud Studio云端部署
- ✅ 支持华为AGC云存储

---

**项目地址**: https://github.com/your-username/hunyuan-podcast

**文档地址**: https://github.com/your-username/hunyuan-podcast/wiki

**演示地址**: (请填写演示地址)





