# 修复 HuggingFace 下载问题

## 错误信息

如果看到以下错误：

```
ProxyError: Unable to connect to proxy
HTTPSConnectionPool(host='huggingface.co', port=443): Max retries exceeded
```

或

```
urllib3.exceptions.MaxRetryError: HTTPSConnectionPool(host='huggingface.co', port=443)
```

说明在下载 IndexTTS-2 运行时的额外模型文件时遇到网络问题。

## 问题说明

IndexTTS-2 在首次运行时会自动下载一些小的模型文件：
- `semantic_codec/model.safetensors` (来自 `amphion/MaskGCT`)
- 其他辅助模型文件

这些文件会在首次运行时自动下载，如果网络访问 HuggingFace 较慢或有问题，会导致下载失败。

## 解决方案

### 方法 1：设置 HuggingFace 镜像（推荐）

#### Windows PowerShell

```powershell
# 设置镜像环境变量
$env:HF_ENDPOINT="https://hf-mirror.com"

# 然后运行程序
cd D:\Develop\hunyuan\index-tts
uv run webui.py
```

#### Windows CMD

```cmd
set HF_ENDPOINT=https://hf-mirror.com
cd D:\Develop\hunyuan\index-tts
uv run webui.py
```

#### Linux/macOS

```bash
export HF_ENDPOINT="https://hf-mirror.com"
cd index-tts
uv run webui.py
```

### 方法 2：永久设置环境变量（Windows）

#### 通过系统设置

1. 右键"此电脑" -> "属性"
2. 点击"高级系统设置"
3. 点击"环境变量"
4. 在"用户变量"中点击"新建"
5. 变量名：`HF_ENDPOINT`
6. 变量值：`https://hf-mirror.com`
7. 点击"确定"保存

#### 通过 PowerShell（当前用户）

```powershell
[System.Environment]::SetEnvironmentVariable("HF_ENDPOINT", "https://hf-mirror.com", "User")
```

需要重新打开终端才能生效。

### 方法 3：在代码中设置

如果不想设置环境变量，可以在运行前在代码中设置。但 IndexTTS-2 的代码在导入时就会下载，所以需要在导入前设置。

创建一个启动脚本：

```python
# run_with_hf_mirror.py
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

# 然后导入和运行
from indextts.webui import ...
```

### 方法 4：手动下载文件

如果镜像也无法使用，可以尝试手动下载：

1. 访问 HuggingFace 镜像站或使用其他方式下载：
   - `amphion/MaskGCT` 仓库中的 `semantic_codec/model.safetensors`

2. 下载后放到缓存目录：
   - Windows: `C:\Users\<用户名>\.cache\huggingface\hub\`
   - Linux/macOS: `~/.cache/huggingface/hub/`

## 验证设置

设置环境变量后，可以验证：

```powershell
# PowerShell
echo $env:HF_ENDPOINT

# 应该输出: https://hf-mirror.com
```

```bash
# Linux/macOS
echo $HF_ENDPOINT

# 应该输出: https://hf-mirror.com
```

## 其他 HuggingFace 镜像

如果 `hf-mirror.com` 也无法使用，可以尝试：

```powershell
# 其他镜像选项
$env:HF_ENDPOINT="https://hf-mirror.com"  # 推荐
# 或
$env:HF_ENDPOINT="https://huggingface.co"  # 官方（如果网络好）
```

## 代理设置

如果使用代理，可能需要配置代理设置：

```powershell
# 设置代理（如果需要）
$env:HTTP_PROXY="http://proxy.example.com:8080"
$env:HTTPS_PROXY="http://proxy.example.com:8080"
```

## 常见问题

### Q1: 设置环境变量后仍然失败

**解决方案：**
1. 确保重新打开了终端窗口
2. 检查环境变量是否正确设置：`echo $env:HF_ENDPOINT`
3. 尝试清除 HuggingFace 缓存后重试

### Q2: 镜像站也无法访问

**解决方案：**
1. 检查网络连接
2. 尝试使用 VPN 或代理
3. 手动下载文件并放到缓存目录

### Q3: 下载速度很慢

**解决方案：**
1. 使用镜像站（hf-mirror.com）
2. 使用稳定的网络连接
3. 耐心等待（文件通常不大，但首次下载可能需要一些时间）

## 清除缓存重新下载

如果下载的文件损坏，可以清除缓存：

```powershell
# Windows
Remove-Item -Recurse -Force "$env:USERPROFILE\.cache\huggingface\hub\*"

# Linux/macOS
rm -rf ~/.cache/huggingface/hub/*
```

然后重新运行程序，会重新下载。

## 相关文档

- [INSTALL.md](INSTALL.md) - 完整安装指南
- [DOWNLOAD_MODELS.md](DOWNLOAD_MODELS.md) - 模型下载指南


