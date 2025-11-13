# 云存储背景音乐配置说明

## 问题说明

如果生成播客时没有加入云存储的 `music/` 文件夹中的背景音乐，通常是因为没有正确配置音乐文件的访问方式。

## 解决方案

### 方案1：通过环境变量配置音乐文件URL列表（推荐）

在 `.env` 文件中或系统环境变量中添加 `CLOUD_MUSIC_URLS`，提供云存储中音乐文件的下载URL列表。

#### 方式A：JSON格式（推荐）

```bash
CLOUD_MUSIC_URLS='["https://ops-server-drcn.agcstorage.link/v0/podcasters-y0qig/music/music1.mp3", "https://ops-server-drcn.agcstorage.link/v0/podcasters-y0qig/music/music2.mp3"]'
```

#### 方式B：逗号分隔格式

```bash
CLOUD_MUSIC_URLS='https://ops-server-drcn.agcstorage.link/v0/podcasters-y0qig/music/music1.mp3,https://ops-server-drcn.agcstorage.link/v0/podcasters-y0qig/music/music2.mp3'
```

### 方案2：获取音乐文件URL的方法

#### 方法1：从HarmonyOS应用获取

1. 在HarmonyOS应用中上传背景音乐到云存储
2. 上传成功后，应用会返回下载URL
3. 将这些URL添加到环境变量 `CLOUD_MUSIC_URLS` 中

#### 方法2：从AGC控制台获取

1. 登录华为AGC控制台
2. 进入云存储服务
3. 找到 `music/` 文件夹中的音乐文件
4. 获取每个文件的下载URL
5. 将这些URL添加到环境变量 `CLOUD_MUSIC_URLS` 中

#### 方法3：通过API自动获取（推荐，需要认证）

系统现在支持通过AGC REST API自动获取云存储中的音乐文件列表，无需手动配置URL。

**配置步骤：**

1. 在 `.env` 文件中配置以下环境变量：

```bash
# AGC云存储基础配置
AGC_STORAGE_URL=https://ops-server-drcn.agcstorage.link/v0/
AGC_BUCKET=your-bucket-name

# AGC API认证配置（用于获取文件列表）
AGC_CLIENT_ID=your-client-id
AGC_CLIENT_SECRET=your-client-secret
AGC_PRODUCT_ID=your-product-id
AGC_DOMAIN=connect-api.cloud.huawei.com

# 音乐文件夹路径（可选，默认为 music/）
CLOUD_STORAGE_MUSIC_PATH=music/
```

2. 或者，将认证信息保存在 `hunyuan_podcast/agc-apiclient-*.json` 文件中：

```json
{
  "client_id": "your-client-id",
  "client_secret": "your-client-secret",
  "project_id": "your-product-id"
}
```

**工作原理：**

1. 系统会自动获取AGC access_token
2. 使用token调用云存储API列出 `music/` 文件夹中的所有文件
3. 自动过滤出音频文件（.mp3, .wav, .m4a, .flac, .ogg, .aac）
4. 自动下载文件到本地缓存
5. AI根据播客内容自动选择合适的背景音乐

**优势：**

- ✅ 无需手动配置URL列表
- ✅ 自动发现云存储中的新音乐文件
- ✅ 支持递归获取子目录中的文件
- ✅ 自动缓存，提高性能

**注意事项：**

- 确保 `AGC_CLIENT_ID` 和 `AGC_CLIENT_SECRET` 有足够的权限访问云存储
- 如果API获取失败，系统会自动回退到方案1（手动配置URL）或本地文件

## 验证配置

配置完成后，运行播客生成时，控制台会输出详细的调试信息：

```
============================================================
开始AI自动选择背景音乐...
尝试从云存储获取音乐文件 (bucket: podcasters-y0qig, path: music/)
从URL列表处理 2 个音乐文件
  - 添加音乐文件: music1.mp3 (路径: music/music1.mp3)
  - 添加音乐文件: music2.mp3 (路径: music/music2.mp3)
✓ 从URL列表获取到 2 个音乐文件
✓ 从云存储获取到 2 个音乐文件
  [1/2] 下载音乐文件: music1.mp3
    ✓ 下载成功: /tmp/hunyuan_music_cache/music1.mp3
  [2/2] 下载音乐文件: music2.mp3
    ✓ 下载成功: /tmp/hunyuan_music_cache/music2.mp3
✓ 成功下载 2/2 个音乐文件到本地缓存
============================================================
```

如果看到 "⚠️ 云存储中没有找到音乐文件" 或 "✗ 从云存储获取音乐文件失败"，请检查：

1. 环境变量 `CLOUD_MUSIC_URLS` 是否正确配置
2. URL是否可访问（可以在浏览器中测试）
3. 云存储配置是否正确（`AGC_STORAGE_URL`、`AGC_BUCKET` 等）

## 常见问题

### Q: 为什么AI自动选择音乐时找不到云存储文件？

A: 请确保：
1. 已配置 `CLOUD_MUSIC_URLS` 环境变量
2. URL格式正确且可访问
3. 音乐文件已上传到云存储的 `music/` 文件夹

### Q: 如何获取音乐文件的下载URL？

A: 有几种方式：
1. 从HarmonyOS应用上传时获取返回的URL
2. 从AGC控制台查看文件详情获取URL
3. 使用云存储API的 `getDownloadURL` 方法

### Q: 可以自动从云存储列出所有音乐文件吗？

A: 目前Python端暂未实现自动列出功能，需要手动配置URL列表。未来可能会添加此功能。

## 调试技巧

如果背景音乐仍然没有加入，请查看控制台输出的详细日志：

1. **AI选择阶段**：查看是否有 "✓ 从云存储获取到 X 个音乐文件"
2. **下载阶段**：查看是否有 "✓ 下载成功"
3. **处理阶段**：查看是否有 "✓ 找到单个背景音乐文件" 或 "✓ 有效文件"
4. **混合阶段**：查看是否有 "✓ 背景音乐混合完成"

根据日志信息，可以快速定位问题所在。

