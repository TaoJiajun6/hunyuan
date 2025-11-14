# 批量上传音乐文件到云存储

这个脚本可以将本地的 `music/` 目录下的所有音乐文件批量上传到华为 AGC 云存储，保持原有的目录结构。

## 功能特点

- ✅ 递归扫描 `music/` 目录下的所有音频文件（.mp3, .wav, .m4a, .flac, .ogg, .aac）
- ✅ 保持目录结构（如 `music/体育/file.mp3` → 云存储 `music/体育/file.mp3`）
- ✅ 显示上传进度和统计信息
- ✅ 支持断点续传（失败的文件会列出，可以重新运行）
- ✅ 自动从配置文件读取认证信息

## 配置方式

### 方式1：使用环境变量（推荐）

在 `.env` 文件中或系统环境变量中设置：

```bash
AGC_STORAGE_URL=https://ops-server-drcn.agcstorage.link/v0/
AGC_BUCKET=your-bucket-name
AGC_CLIENT_ID=your-client-id
AGC_CLIENT_SECRET=your-client-secret
AGC_PRODUCT_ID=your-product-id
```

### 方式2：使用配置文件

在 `hunyuan_podcast/agc-apiclient-*.json` 文件中配置：

```json
{
  "client_id": "your-client-id",
  "client_secret": "your-client-secret",
  "project_id": "your-product-id"
}
```

### 方式3：命令行参数

直接通过命令行参数提供：

```bash
python tools/upload_music_to_cloud.py \
  --music-dir ./music \
  --storage-url https://ops-server-drcn.agcstorage.link/v0/ \
  --bucket your-bucket-name \
  --client-id your-client-id \
  --client-secret your-client-secret \
  --product-id your-product-id
```

## 使用方法

### 基本用法

```bash
# 从项目根目录运行
python tools/upload_music_to_cloud.py
```

脚本会：
1. 自动扫描 `music/` 目录下的所有音频文件
2. 显示找到的文件列表
3. 询问确认后开始上传
4. 显示每个文件的上传进度
5. 最后显示统计信息

### 指定音乐目录

```bash
python tools/upload_music_to_cloud.py --music-dir /path/to/music
```

### 查看帮助

```bash
python tools/upload_music_to_cloud.py --help
```

## 输出示例

```
============================================================
批量上传音乐文件到云存储
============================================================
音乐目录: D:\Develop\hunyuan\music
存储URL: https://ops-server-drcn.agcstorage.link/v0/
存储桶: podcasters-y0qig
客户端ID: 12345678...
项目ID: 461323198430936564
============================================================

============================================================
正在扫描音乐文件...
音乐目录: D:\Develop\hunyuan\music
============================================================
✓ 找到 200 个音频文件

正在获取 AGC access token...
✓ Token 获取成功

============================================================
开始批量上传...
============================================================
[1/200] 上传: music/体育/adrenaline-rush-sport-rock-music-402354.mp3
  文件: adrenaline-rush-sport-rock-music-402354.mp3 (2.45 MB)
  ✓ 上传成功

[2/200] 上传: music/财经/music1.mp3
  文件: music1.mp3 (1.23 MB)
  ✓ 上传成功

...

============================================================
上传完成！
============================================================
总计: 200 个文件
成功: 200 个
失败: 0 个

🎉 所有文件上传成功！
```

## 注意事项

1. **文件大小限制**：确保单个文件不超过云存储的限制（通常为 5GB）
2. **网络稳定性**：上传大文件时建议在网络稳定的环境下运行
3. **超时设置**：脚本设置了 5 分钟的超时时间，适合大文件上传
4. **重复上传**：如果文件已存在，会覆盖原有文件
5. **中断恢复**：如果上传中断，可以重新运行脚本，已上传的文件会覆盖（不会跳过）

## 故障排除

### 问题1：找不到配置文件

**错误信息**：
```
错误：需要提供 client_id 和 client_secret
```

**解决方法**：
- 确保在 `.env` 文件中配置了 `AGC_CLIENT_ID` 和 `AGC_CLIENT_SECRET`
- 或在 `hunyuan_podcast/agc-apiclient-*.json` 文件中配置
- 或通过命令行参数 `--client-id` 和 `--client-secret` 提供

### 问题2：Token 获取失败

**错误信息**：
```
✗ 获取 token 失败: ...
```

**解决方法**：
- 检查 `client_id` 和 `client_secret` 是否正确
- 检查网络连接是否正常
- 确认 AGC 服务是否可用

### 问题3：上传失败

**错误信息**：
```
✗ 上传失败: HTTP 403 Forbidden
```

**解决方法**：
- 检查云存储的安全规则配置
- 确认 `client_id` 有上传权限
- 检查 `product_id` 是否正确

### 问题4：文件路径问题

**错误信息**：
```
错误：音乐目录不存在: music
```

**解决方法**：
- 确保从项目根目录运行脚本
- 或使用 `--music-dir` 参数指定正确的路径

## 高级用法

### 只上传特定子目录

如果需要只上传特定子目录，可以临时移动或复制文件到新目录：

```bash
# 创建临时目录
mkdir temp_music
# 复制特定子目录
cp -r music/体育 temp_music/
# 上传临时目录
python tools/upload_music_to_cloud.py --music-dir temp_music
```

### 检查上传结果

上传完成后，可以登录 [AppGallery Connect](https://developer.huawei.com/consumer/cn/service/josp/agc/index.html) 控制台，进入"云存储"界面查看文件列表，确认文件已正确上传。

## 相关文件

- `tools/upload_music_to_cloud.py` - 批量上传脚本
- `hunyuan_podcast/upload_client.py` - 上传客户端库
- `hunyuan_podcast/cloud_storage_music.py` - 云存储音乐访问模块

