# SoulX-Podcast 使用前检查清单

## ✅ 代码迁移状态

代码已经完成迁移，`PodcastGenerator` 现在使用 SoulX-Podcast 替代了 IndexTTS。

## ⚠️ 需要完成的准备工作

### 1. 安装 SoulX-Podcast 依赖

```powershell
cd SoulX-Podcast
pip install -r requirements.txt
```

主要依赖包括：
- gradio
- torch==2.7.1
- torchaudio==2.7.1
- transformers==4.57.1
- s3tokenizer
- 等等

### 2. 下载 SoulX-Podcast 模型

模型需要下载到 `SoulX-Podcast/pretrained_models/` 目录。

#### 方法 1：使用 huggingface-cli（推荐）

```powershell
cd SoulX-Podcast
pip install -U huggingface_hub

# 基础模型
huggingface-cli download --resume-download Soul-AILab/SoulX-Podcast-1.7B --local-dir pretrained_models/SoulX-Podcast-1.7B

# 方言模型（可选）
huggingface-cli download --resume-download Soul-AILab/SoulX-Podcast-1.7B-dialect --local-dir pretrained_models/SoulX-Podcast-1.7B-dialect
```

#### 方法 2：使用 Python

```python
from huggingface_hub import snapshot_download

# 基础模型
snapshot_download("Soul-AILab/SoulX-Podcast-1.7B", local_dir="pretrained_models/SoulX-Podcast-1.7B")
```

#### 方法 3：使用 git clone（需要 git-lfs）

```powershell
cd SoulX-Podcast
mkdir -p pretrained_models
git lfs install
git clone https://huggingface.co/Soul-AILab/SoulX-Podcast-1.7B pretrained_models/SoulX-Podcast-1.7B
```

### 3. 检查模型文件

模型目录应包含以下文件：
- `flow.pt` - Flow 模型
- `hift.pt` - HiFi-GAN 模型
- `campplus.onnx` - 说话人识别模型
- `soulxpodcast_config.json` - 配置文件
- 其他模型文件

### 4. 验证安装

运行以下命令检查：

```python
# 检查依赖
python -c "import gradio; import torch; import s3tokenizer; print('✅ 依赖安装成功')"

# 检查模型路径
import os
model_path = "SoulX-Podcast/pretrained_models/SoulX-Podcast-1.7B"
if os.path.exists(model_path):
    print(f"✅ 模型目录存在: {model_path}")
else:
    print(f"❌ 模型目录不存在: {model_path}")
```

## 🚀 使用方式

### 方式 1：通过 PodcastGenerator（推荐）

```python
from hunyuan_podcast.podcast_generator import PodcastGenerator

# 初始化生成器
generator = PodcastGenerator()

# 设置角色音色
generator.set_role_voice("角色A", "path/to/voice_a.wav")
generator.set_role_voice("角色B", "path/to/voice_b.wav")

# 生成播客
text = """
[角色A] 大家好，欢迎收听今天的播客。
[角色B] 是的，今天我们要聊一个很有趣的话题。
"""

output_path = generator.generate_from_text(
    text=text,
    verbose=True
)
```

### 方式 2：通过 WebUI

```powershell
python -m hunyuan_podcast.webui
```

### 方式 3：通过 API 服务器

```powershell
python run_api_server.py
```

## ⚠️ 注意事项

1. **GPU 要求**：SoulX-Podcast 需要 GPU 支持，CPU 模式可能无法正常工作
2. **采样率**：SoulX-Podcast 输出 24000Hz，代码会自动转换为 22050Hz
3. **模型大小**：模型文件较大（约几GB），确保有足够的磁盘空间
4. **内存要求**：建议至少 16GB 内存

## 📝 当前状态检查

运行以下命令检查当前状态：

```powershell
# 检查模型目录
Test-Path "SoulX-Podcast\pretrained_models\SoulX-Podcast-1.7B"

# 检查依赖
python -c "import gradio; print('gradio:', '✅' if True else '❌')"
python -c "import torch; print('torch:', '✅' if True else '❌')"
python -c "import s3tokenizer; print('s3tokenizer:', '✅' if True else '❌')"
```

## 🔧 故障排除

如果遇到问题：

1. **ModuleNotFoundError**：安装缺失的依赖
2. **模型文件不存在**：下载模型文件
3. **CUDA 错误**：检查 GPU 驱动和 PyTorch CUDA 版本
4. **内存不足**：减少批次大小或使用更小的模型


