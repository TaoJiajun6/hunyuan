# 华为AGC云存储服务 - Node.js实现

## 概述

这是一个基于华为AGC Node.js Server SDK的云存储服务，用于上传和下载音色文件、播客文件等。

## 功能特性

- ✅ **上传文件**: 支持上传播客文件、音色文件等到云存储
- ✅ **下载文件**: 支持从云存储下载文件到本地
- ✅ **文件管理**: 支持列出文件、获取元数据、删除文件等操作
- ✅ **自动初始化**: 自动查找和加载AGC凭据文件
- ✅ **命令行工具**: 提供命令行接口，方便直接使用
- ✅ **模块导出**: 可以作为Node.js模块被其他代码调用

## 安装依赖

```bash
cd cloudstorage
npm install
```

## 配置

### 方式一：使用环境变量（推荐）

**Linux/Mac:**
```bash
export AGC_CONFIG="/path/to/agc-apiclient-xxx-xxx.json"
export AGC_BUCKET="podcasters-y0qig"
```

**Windows:**
```cmd
set AGC_CONFIG=C:\path\to\agc-apiclient-xxx-xxx.json
set AGC_BUCKET=podcasters-y0qig
```

### 方式二：使用默认路径

将AGC凭据文件放在 `hunyuan_podcast/agc-apiclient-*.json`，代码会自动查找。

## 使用方法

### 1. 作为命令行工具使用

#### 上传文件
```bash
# 上传播客文件
node cloudstorage_service.js upload ./podcast.wav outputs/podcasts/podcast.wav

# 上传音色文件
node cloudstorage_service.js upload ./voice.wav voices/voice.wav
```

#### 下载文件
```bash
# 下载播客文件
node cloudstorage_service.js download outputs/podcasts/podcast.wav ./downloads/podcast.wav

# 下载音色文件
node cloudstorage_service.js download voices/voice.wav ./downloads/voice.wav
```

#### 列出文件
```bash
# 列出所有播客文件
node cloudstorage_service.js list outputs/podcasts/

# 列出所有音色文件
node cloudstorage_service.js list voices/
```

#### 删除文件
```bash
node cloudstorage_service.js delete outputs/podcasts/podcast.wav
```

### 2. 作为Node.js模块使用

```javascript
const cloudStorage = require('./cloudstorage_service');

// 初始化（可选，会自动初始化）
cloudStorage.initializeStorage('/path/to/agc-apiclient-xxx-xxx.json');

// 上传播客文件
async function uploadPodcastExample() {
  try {
    const result = await cloudStorage.uploadPodcast('./podcast.wav');
    console.log('上传成功:', result.url);
  } catch (error) {
    console.error('上传失败:', error);
  }
}

// 上传音色文件
async function uploadVoiceExample() {
  try {
    const result = await cloudStorage.uploadVoice('./voice.wav');
    console.log('上传成功:', result.url);
  } catch (error) {
    console.error('上传失败:', error);
  }
}

// 下载播客文件
async function downloadPodcastExample() {
  try {
    const result = await cloudStorage.downloadPodcast('outputs/podcasts/podcast.wav');
    console.log('下载成功:', result.localPath);
  } catch (error) {
    console.error('下载失败:', error);
  }
}

// 下载音色文件
async function downloadVoiceExample() {
  try {
    const result = await cloudStorage.downloadVoice('voices/voice.wav');
    console.log('下载成功:', result.localPath);
  } catch (error) {
    console.error('下载失败:', error);
  }
}

// 列出文件
async function listFilesExample() {
  try {
    const result = await cloudStorage.listFiles('outputs/podcasts/');
    console.log('文件列表:', result.files);
  } catch (error) {
    console.error('列出文件失败:', error);
  }
}
```

### 3. 在Python中调用Node.js服务

可以创建一个Python包装器来调用Node.js服务：

```python
# python_cloudstorage_wrapper.py
import subprocess
import json
import os

def upload_file(local_path, cloud_path):
    """使用Node.js SDK上传文件"""
    script_path = os.path.join(os.path.dirname(__file__), 'cloudstorage', 'cloudstorage_service.js')
    result = subprocess.run(
        ['node', script_path, 'upload', local_path, cloud_path],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        # 解析输出中的JSON结果
        return json.loads(result.stdout.split('\n')[-2])
    else:
        raise Exception(f"上传失败: {result.stderr}")

def download_file(cloud_path, local_path):
    """使用Node.js SDK下载文件"""
    script_path = os.path.join(os.path.dirname(__file__), 'cloudstorage', 'cloudstorage_service.js')
    result = subprocess.run(
        ['node', script_path, 'download', cloud_path, local_path],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        return json.loads(result.stdout.split('\n')[-2])
    else:
        raise Exception(f"下载失败: {result.stderr}")
```

## API参考

### 函数列表

- `initializeStorage(credentialPath)` - 初始化AGC客户端
- `uploadFile(localFilePath, cloudPath, bucketName)` - 上传文件
- `downloadFile(cloudPath, localFilePath, bucketName)` - 下载文件
- `uploadPodcast(podcastFilePath, fileName)` - 上传播客文件（便捷方法）
- `uploadVoice(voiceFilePath, fileName)` - 上传音色文件（便捷方法）
- `downloadPodcast(cloudPath, localDir)` - 下载播客文件（便捷方法）
- `downloadVoice(cloudPath, localDir)` - 下载音色文件（便捷方法）
- `getFileMetadata(cloudPath, bucketName)` - 获取文件元数据
- `listFiles(prefix, bucketName)` - 列出文件
- `deleteFile(cloudPath, bucketName)` - 删除文件

## 与Python实现的对比

### Node.js SDK的优势

1. **官方支持**: 华为AGC官方提供的Node.js Server SDK
2. **功能完整**: 支持完整的云存储操作（上传、下载、列表、删除、元数据等）
3. **自动重试**: SDK内置重试机制
4. **更好的错误处理**: 提供详细的错误信息

### Python实现的优势

1. **与现有系统集成**: 当前系统主要使用Python
2. **自定义优化**: 可以针对特定需求进行优化（如无超时限制、TCP优化等）
3. **更灵活**: 可以完全控制上传过程

### 建议

- **新功能开发**: 优先使用Node.js SDK，功能更完整
- **现有功能**: 可以继续使用Python实现，或逐步迁移到Node.js
- **混合使用**: 可以在Python中调用Node.js脚本，结合两者优势

## 注意事项

1. 确保已安装Node.js 10.0.0或更高版本
2. 确保AGC凭据文件路径正确
3. 确保存储桶名称正确
4. 上传大文件时注意网络稳定性

## 故障排查

### 问题：找不到凭据文件

**解决方案**:
1. 检查环境变量 `AGC_CONFIG` 是否设置
2. 检查默认路径 `hunyuan_podcast/agc-apiclient-*.json` 是否存在
3. 或在代码中明确指定凭据文件路径

### 问题：上传/下载失败

**解决方案**:
1. 检查网络连接
2. 检查存储桶名称是否正确
3. 检查文件路径是否正确
4. 查看详细错误信息

## 相关文档

- [华为AGC云存储开发指南](https://developer.huawei.com/consumer/cn/doc/development/AppGallery-connect-Guides/agc-get-started)
- [Node.js Server SDK API参考](https://developer.huawei.com/consumer/cn/doc/development/AppGallery-connect-References/cloudstroage)

