# 故障排除指南

## 问题：生成后找不到输出文件

### 检查步骤

1. **确认生成是否成功**
   - 查看WebUI中的"状态信息"区域
   - 如果显示"✅ 播客生成成功！"，说明生成已完成
   - 查看状态信息中显示的"输出文件"路径

2. **检查输出目录**

   输出文件默认保存在：
   ```
   D:\Develop\hunyuan\outputs\podcasts\
   ```

   检查方法：
   ```powershell
   # 查看目录内容
   Get-ChildItem D:\Develop\hunyuan\outputs\podcasts
   
   # 或使用文件管理器直接打开
   explorer D:\Develop\hunyuan\outputs\podcasts
   ```

3. **检查文件是否在其他位置**

   有时文件可能保存在：
   - 项目根目录：`D:\Develop\hunyuan\`
   - SoulX-Podcast 目录：`SoulX-Podcast/outputs/`
   - 临时目录

### 解决方案

#### 方案1：在WebUI中直接播放/下载

生成成功后，WebUI的"生成的播客音频"区域会显示音频播放器，可以：
- 直接在浏览器中播放
- 点击下载按钮下载文件

#### 方案2：查看状态信息中的文件路径

生成成功后，状态信息会显示完整的文件路径，例如：
```
输出文件：D:\Develop\hunyuan\outputs\podcasts\podcast_1234567890.wav
```

直接使用这个路径访问文件。

#### 方案3：搜索文件

如果找不到文件，可以搜索：

```powershell
# 搜索最近生成的WAV文件
Get-ChildItem -Path D:\Develop\hunyuan -Recurse -Filter "podcast_*.wav" | Sort-Object LastWriteTime -Descending | Select-Object -First 5
```

### 常见原因

1. **生成失败但未显示错误**
   - 检查浏览器控制台（F12）是否有错误
   - 检查服务器终端是否有错误信息

2. **文件保存权限问题**
   - 确保对 `outputs/podcasts` 目录有写入权限

3. **路径问题**
   - 已修复：现在使用绝对路径，确保文件保存到正确位置

### 验证文件生成

运行以下Python脚本检查：

```python
import os
from hunyuan_podcast.config import OUTPUT_DIR

print(f"输出目录: {OUTPUT_DIR}")
print(f"绝对路径: {os.path.abspath(OUTPUT_DIR)}")
print(f"目录存在: {os.path.exists(OUTPUT_DIR)}")

if os.path.exists(OUTPUT_DIR):
    files = os.listdir(OUTPUT_DIR)
    print(f"文件数量: {len(files)}")
    for f in files:
        print(f"  - {f}")
```

### 手动测试生成

如果WebUI生成失败，可以尝试使用Python脚本直接测试：

```python
from hunyuan_podcast.podcast_generator import PodcastGenerator

generator = PodcastGenerator()

# 设置角色音色
generator.set_role_voice("角色A", "index-tts/examples/voice_01.wav")
generator.set_role_voice("角色B", "index-tts/examples/voice_02.wav")

# 生成播客
text = "[角色A]测试 [角色B]测试成功"
output_path = generator.generate_from_text(text, verbose=True)
print(f"生成的文件: {output_path}")
```

## 其他常见问题

### 问题：生成时间很长

**原因：**
- 首次生成需要下载额外模型文件
- 音频生成本身需要时间
- 使用CPU模式会更慢

**解决方案：**
- 使用GPU加速
- 启用FP16模式
- 耐心等待（首次生成可能需要5-10分钟）

### 问题：生成失败但没有错误信息

**检查：**
1. 查看浏览器控制台（F12 -> Console）
2. 查看服务器终端输出
3. 检查网络连接
4. 检查API密钥是否有效

## 获取帮助

如果问题仍然存在：
1. 查看完整错误信息（浏览器控制台 + 服务器终端）
2. 检查所有依赖是否正确安装
3. 确认模型文件已完整下载
4. 查看相关文档：
   - [使用说明.md](使用说明.md) - 使用指南
   - [README.md](README.md) - 详细文档





























