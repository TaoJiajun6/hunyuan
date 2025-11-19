# 云存储集成文档

## 概述

本功能实现了从鸿蒙APP上传音频文件到华为AGC云存储，后端API从云存储下载音频文件进行播客生成的功能。

## 架构说明

### 前端（HarmonyOS APP）

1. **文件选择与上传**：
   - 使用 `FileUtils.pickAudioFile()` 选择音频文件
   - 自动上传到华为AGC云存储
   - 获取云存储URL

2. **API请求**：
   - 如果使用云存储（`USE_CLOUD_STORAGE=true`），传递 `role_voice_urls` 字段
   - 如果不使用云存储，传递 `role_voices` 字段（base64编码）

### 后端（Python API Server）

1. **音频文件获取**：
   - 如果请求包含 `role_voice_urls`，从云存储URL下载音频文件
   - 如果请求包含 `role_voices`，从base64解码音频文件
   - 支持两种模式自动切换

2. **文件处理**：
   - 下载的音频文件保存到临时文件
   - 处理完成后自动清理临时文件

## 配置说明

### 前端配置

在 `podcasters/components/lib_api/src/main/ets/services/PodcastService.ets` 中：

```typescript
export class PodcastConfig {
  // 是否使用云存储
  static readonly USE_CLOUD_STORAGE: boolean = true; // 设置为 true 如果使用云存储
}
```

### 后端配置

后端API自动检测请求中的 `role_voice_urls` 或 `role_voices` 字段，无需额外配置。

## 文件结构

### 新增文件

1. **GlobalContext.ets** (`podcasters/products/phone/src/main/ets/common/GlobalContext.ets`)
   - 管理全局应用上下文
   - 用于云存储上传时获取UIAbilityContext

### 修改文件

1. **FileUtils.ets** (`podcasters/products/phone/src/main/ets/utils/FileUtils.ets`)
   - 添加 `AudioFileInfo` 接口
   - 添加 `pickAudioFile()` 方法，支持云存储上传
   - 添加 `uploadAudioToCloud()` 私有方法

2. **PodcastService.ets** (`podcasters/components/lib_api/src/main/ets/services/PodcastService.ets`)
   - 添加 `USE_CLOUD_STORAGE` 配置项
   - 修改请求接口，支持 `role_voice_urls` 和 `voice_url` 字段
   - 修改请求体类，支持云存储URL

3. **PodcastMultiRolePage.ets** (`podcasters/products/phone/src/main/ets/pages/podcast/PodcastMultiRolePage.ets`)
   - 添加 `roleVoiceUrls` 状态变量
   - 修改 `selectVoiceFile()` 方法，支持云存储上传
   - 修改 `generatePodcast()` 方法，传递云存储URL

4. **api_server.py** (`hunyuan_podcast/api_server.py`)
   - 添加 `download_audio_from_url()` 函数
   - 添加 `get_audio_file()` 函数
   - 修改请求模型，支持 `role_voice_urls` 和 `voice_url` 字段
   - 修改API端点，支持从URL下载音频文件

5. **EntryAbility.ets** (`podcasters/products/phone/src/main/ets/entryability/EntryAbility.ets`)
   - 初始化GlobalContext

## 使用流程

### 1. 选择音频文件

```typescript
const audioFileInfo = await FileUtils.pickAudioFile(context, true);
if (audioFileInfo && audioFileInfo.cloudUrl) {
  // 使用云存储URL
  roleVoiceUrls[roleName] = audioFileInfo.cloudUrl;
}
```

### 2. 发送API请求

```typescript
const request: MultiRoleRequest = {
  text: text,
  role_voice_urls: roleVoiceUrls, // 使用云存储URL
  silence_interval: 300
};
```

### 3. 后端处理

```python
# 自动检测使用云存储URL还是base64
if request.role_voice_urls:
    # 从云存储URL下载
    temp_file = download_audio_from_url(voice_url)
else:
    # 从base64解码
    temp_file = decode_base64_audio(voice_base64)
```

## 优势

1. **减少请求体大小**：使用云存储URL替代base64编码，大幅减少请求体大小
2. **提高传输效率**：音频文件直接从云存储下载，不经过API请求体
3. **支持大文件**：不受请求体大小限制，支持更大的音频文件
4. **文件可重复使用**：上传到云存储的文件可以重复使用，无需重复上传

## 注意事项

1. **权限配置**：确保在 `module.json5` 中配置了网络权限和云存储权限
2. **云存储初始化**：确保已开通华为AGC云存储服务
3. **文件大小限制**：客户端限制10MB，服务器限制50MB
4. **错误处理**：如果云存储上传失败，会自动回退到base64模式

## 测试建议

1. **测试云存储上传**：
   - 选择音频文件
   - 检查是否成功上传到云存储
   - 检查是否获取到云存储URL

2. **测试API请求**：
   - 使用云存储URL发送API请求
   - 检查后端是否成功下载音频文件
   - 检查播客是否成功生成

3. **测试错误处理**：
   - 测试云存储上传失败的情况
   - 测试URL下载失败的情况
   - 检查错误提示是否清晰

## 后续优化

1. **缓存机制**：可以添加云存储URL缓存，避免重复上传相同文件
2. **上传进度**：可以添加上传进度显示，提升用户体验
3. **文件管理**：可以添加文件管理功能，查看已上传的文件
4. **批量上传**：可以支持批量上传多个音频文件


























