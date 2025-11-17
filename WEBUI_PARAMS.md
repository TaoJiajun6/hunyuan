# IndexTTS-2 WebUI 命令行参数说明

## 命令格式

```bash
uv run webui.py [选项]
```

## 参数详解

### 基础参数

#### `-h, --help`
- **功能**：显示帮助信息
- **示例**：`uv run webui.py -h`
- **说明**：列出所有可用参数及其说明

#### `--verbose`
- **功能**：启用详细输出模式
- **默认值**：`False`（关闭）
- **示例**：`uv run webui.py --verbose`
- **说明**：启用后会输出更详细的调试信息，包括：
  - 文本处理过程
  - 音频生成进度
  - 模型加载状态
  - 错误详情

### 网络配置

#### `--port PORT`
- **功能**：设置 WebUI 运行的端口号
- **默认值**：`7860`
- **示例**：`uv run webui.py --port 7861`
- **说明**：
  - 如果 7860 端口被占用，可以指定其他端口
  - 访问地址：`http://localhost:PORT`

#### `--host HOST`
- **功能**：设置 WebUI 绑定的主机地址
- **默认值**：`0.0.0.0`（监听所有网络接口）
- **示例**：
  - `uv run webui.py --host 127.0.0.1`（仅本地访问）
  - `uv run webui.py --host 0.0.0.0`（允许外部访问）
- **说明**：
  - `127.0.0.1`：只能从本机访问
  - `0.0.0.0`：可以从局域网内其他设备访问

### 模型配置

#### `--model_dir MODEL_DIR`
- **功能**：指定模型检查点目录
- **默认值**：`./checkpoints`
- **示例**：`uv run webui.py --model_dir /path/to/checkpoints`
- **说明**：
  - 包含模型权重文件（gpt.pth, s2mel.pth 等）
  - 包含配置文件（config.yaml）
  - 包含其他必需文件（bpe.model, wav2vec2bert_stats.pt 等）

### 性能优化参数

#### `--fp16`
- **功能**：使用 FP16（半精度）进行推理
- **默认值**：`False`（使用 FP32）
- **示例**：`uv run webui.py --fp16`
- **说明**：
  - ✅ **优点**：
    - 显存占用减少约 50%
    - 推理速度提升约 20-30%
    - 质量损失很小（通常难以察觉）
  - ⚠️ **要求**：
    - 需要支持 FP16 的 GPU（现代 NVIDIA GPU）
    - CPU 模式不支持 FP16
  - 💡 **推荐**：如果显存不足或想提升速度，建议启用

#### `--deepspeed`
- **功能**：使用 DeepSpeed 加速推理
- **默认值**：`False`（不使用）
- **示例**：`uv run webui.py --deepspeed`
- **说明**：
  - ✅ **优点**：
    - 可能提升推理速度
    - 优化显存使用
  - ⚠️ **注意**：
    - 性能提升取决于硬件配置
    - 某些系统可能反而变慢
    - 需要安装 DeepSpeed（通过 `--all-extras` 安装）
  - 💡 **建议**：可以尝试启用，如果变慢则关闭

#### `--cuda_kernel`
- **功能**：使用自定义 CUDA 内核加速 BigVGAN
- **默认值**：`False`（使用 PyTorch 实现）
- **示例**：`uv run webui.py --cuda_kernel`
- **说明**：
  - ✅ **优点**：
    - BigVGAN 语音合成速度提升
    - 使用优化的 CUDA 实现
  - ⚠️ **要求**：
    - 需要 NVIDIA GPU
    - 需要 CUDA 支持
    - 需要编译 CUDA 内核（首次使用时会自动编译）
  - 💡 **推荐**：如果有 NVIDIA GPU，建议启用

### 文本处理参数

#### `--gui_seg_tokens GUI_SEG_TOKENS`
- **功能**：设置 GUI 中每个生成片段的最大 token 数
- **默认值**：`120`
- **示例**：`uv run webui.py --gui_seg_tokens 100`
- **说明**：
  - **作用**：控制文本分句的长度
  - **值越大**：
    - 分句越长，生成的音频片段更长
    - 可能提高整体流畅度
    - 但可能导致显存占用增加
  - **值越小**：
    - 分句越短，生成的音频片段更短
    - 显存占用更少
    - 但可能导致音频不够流畅
  - **推荐范围**：`80-200`
  - **建议**：
    - 显存充足：使用 120-200
    - 显存有限：使用 80-120

## 常用命令组合示例

### 示例 1：基础启动（默认配置）

```bash
cd index-tts
uv run webui.py
```

访问：`http://localhost:7860`

### 示例 2：启用性能优化（推荐）

```bash
cd index-tts
uv run webui.py --fp16 --cuda_kernel
```

- 启用 FP16 减少显存占用
- 启用 CUDA 内核加速

### 示例 3：自定义端口和主机

```bash
cd index-tts
uv run webui.py --port 7861 --host 0.0.0.0
```

- 使用 7861 端口
- 允许局域网访问

### 示例 4：完整优化配置

```bash
cd index-tts
uv run webui.py \
  --fp16 \
  --cuda_kernel \
  --deepspeed \
  --port 7861 \
  --verbose
```

- 启用所有性能优化
- 使用自定义端口
- 显示详细日志

### 示例 5：显存受限配置

```bash
cd index-tts
uv run webui.py \
  --fp16 \
  --gui_seg_tokens 80
```

- 启用 FP16 减少显存
- 使用较小的分句长度

## 性能优化建议

### 根据显存选择配置

| 显存大小 | 推荐配置 |
|---------|---------|
| 8GB | `--fp16 --gui_seg_tokens 80` |
| 12GB | `--fp16 --cuda_kernel --gui_seg_tokens 100` |
| 16GB+ | `--fp16 --cuda_kernel --deepspeed --gui_seg_tokens 120` |

### 根据需求选择配置

**追求速度**：
```bash
uv run webui.py --fp16 --cuda_kernel --deepspeed
```

**追求质量**：
```bash
uv run webui.py  # 使用默认 FP32
```

**显存不足**：
```bash
uv run webui.py --fp16 --gui_seg_tokens 80
```

## 故障排除

### 问题：FP16 报错
- **原因**：GPU 不支持 FP16 或使用 CPU
- **解决**：移除 `--fp16` 参数

### 问题：DeepSpeed 报错
- **原因**：未安装 DeepSpeed 或配置问题
- **解决**：移除 `--deepspeed` 参数，或重新安装：
  ```bash
  uv sync --extra deepspeed
  ```

### 问题：CUDA 内核编译失败
- **原因**：CUDA 版本不匹配或缺少编译工具
- **解决**：移除 `--cuda_kernel` 参数，使用 PyTorch 实现

## 相关文档

- [INSTALL.md](INSTALL.md) - 安装指南
- [QUICKSTART.md](QUICKSTART.md) - 快速开始
- [README_PODCAST.md](README_PODCAST.md) - 播客系统文档



























