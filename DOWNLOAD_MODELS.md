# IndexTTS-2 模型文件下载指南

## 错误提示

如果看到以下错误：

```
Required file ./checkpoints\bpe.model does not exist. Please download it.
```

或

```
警告：配置文件不存在 index-tts/checkpoints/config.yaml
警告：模型目录不存在 index-tts/checkpoints
```

说明模型文件未下载或下载不完整。

## 快速解决方案

### 方法 1：使用 HuggingFace CLI（推荐）

```bash
# 1. 进入 index-tts 目录
cd index-tts

# 2. 安装 huggingface-cli（如果还没安装）
uv tool install "huggingface-hub[cli,hf_xet]"

# 3. 下载模型
hf download IndexTeam/IndexTTS-2 --local-dir=checkpoints
```

### 方法 2：使用 ModelScope（国内用户推荐）

```bash
# 1. 进入 index-tts 目录
cd index-tts

# 2. 安装 modelscope（如果还没安装）
uv tool install "modelscope"

# 3. 下载模型
modelscope download --model IndexTeam/IndexTTS-2 --local_dir checkpoints
```

### 方法 3：使用 HuggingFace 镜像（如果下载慢）

```bash
# 设置镜像（在下载前执行）
# Linux/macOS
export HF_ENDPOINT="https://hf-mirror.com"

# Windows PowerShell
$env:HF_ENDPOINT="https://hf-mirror.com"

# Windows CMD
set HF_ENDPOINT=https://hf-mirror.com

# 然后使用 HuggingFace CLI 下载
cd index-tts
hf download IndexTeam/IndexTTS-2 --local-dir=checkpoints
```

## 必需文件清单

下载完成后，`index-tts/checkpoints/` 目录应包含：

### 核心文件（必需）

- ✅ `config.yaml` - 配置文件
- ✅ `bpe.model` - BPE 分词模型
- ✅ `gpt.pth` - GPT 模型权重（约 2-3GB）
- ✅ `s2mel.pth` - S2Mel 模型权重（约 1-2GB）
- ✅ `wav2vec2bert_stats.pt` - Wav2Vec2BERT 统计文件

### 其他文件

- `pinyin.vocab` - 拼音词汇表
- `emo_matrix.pt` - 情感矩阵
- `spk_matrix.pt` - 说话人矩阵
- 其他辅助文件

## 验证下载

### 检查文件是否存在

```bash
cd index-tts/checkpoints

# Linux/macOS
ls -lh

# Windows PowerShell
Get-ChildItem

# Windows CMD
dir
```

### 检查文件大小

主要文件应该有合理的大小：

- `gpt.pth` - 通常 > 2GB
- `s2mel.pth` - 通常 > 1GB
- `bpe.model` - 通常几MB到几十MB

如果文件大小异常小（如只有几KB），说明下载不完整，需要重新下载。

### 测试导入

```bash
cd index-tts
uv run python -c "from indextts.infer_v2 import IndexTTS2; print('模型文件完整！')"
```

如果成功，说明所有文件都已正确下载。

## 常见问题

### Q1: 下载速度很慢

**解决方案：**

1. 使用 ModelScope（国内用户）：
   ```bash
   modelscope download --model IndexTeam/IndexTTS-2 --local_dir checkpoints
   ```

2. 使用 HuggingFace 镜像：
   ```bash
   export HF_ENDPOINT="https://hf-mirror.com"
   hf download IndexTeam/IndexTTS-2 --local-dir=checkpoints
   ```

3. 使用代理（如果有）

### Q2: 下载中断

**解决方案：**

重新运行下载命令，工具会自动断点续传：

```bash
hf download IndexTeam/IndexTTS-2 --local-dir=checkpoints
```

### Q3: 某些文件下载失败

**解决方案：**

1. 检查网络连接
2. 使用不同的下载方式（HuggingFace ↔ ModelScope）
3. 手动检查缺失的文件，单独下载

### Q4: 磁盘空间不足

**解决方案：**

模型文件总共需要约 **5-10GB** 空间。确保有足够的磁盘空间：

```bash
# 检查磁盘空间
# Linux/macOS
df -h

# Windows PowerShell
Get-PSDrive C
```

### Q5: 权限错误

**解决方案：**

确保对 `checkpoints` 目录有写入权限：

```bash
# Linux/macOS
chmod -R 755 index-tts/checkpoints

# Windows
# 右键 checkpoints 文件夹 -> 属性 -> 安全 -> 编辑权限
```

## 下载进度

下载过程可能需要一些时间，取决于网络速度：

- **快速网络**：10-30 分钟
- **普通网络**：30-60 分钟
- **慢速网络**：1-2 小时或更长

请耐心等待，不要中断下载过程。

## 验证安装

下载完成后，运行以下命令验证：

```bash
cd index-tts
uv run python -c "
from indextts.infer_v2 import IndexTTS2
import os

# 检查文件
required_files = [
    'config.yaml',
    'bpe.model',
    'gpt.pth',
    's2mel.pth',
    'wav2vec2bert_stats.pt'
]

checkpoints_dir = 'checkpoints'
missing = []

for file in required_files:
    path = os.path.join(checkpoints_dir, file)
    if not os.path.exists(path):
        missing.append(file)
    else:
        size = os.path.getsize(path) / (1024*1024)  # MB
        print(f'✅ {file}: {size:.1f} MB')

if missing:
    print(f'❌ 缺少文件: {missing}')
    print('请重新下载模型文件')
else:
    print('✅ 所有必需文件都已下载！')
"
```

## 相关文档

- [INSTALL.md](INSTALL.md) - 完整安装指南
- [QUICKSTART.md](QUICKSTART.md) - 快速开始
- [README_PODCAST.md](README_PODCAST.md) - 播客系统文档


















