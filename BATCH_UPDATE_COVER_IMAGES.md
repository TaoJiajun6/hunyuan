# 批量更新播客封面图脚本使用说明

## 功能说明

这个脚本用于批量为旧播客生成封面图并更新到数据库。

**主要功能：**
1. 从云数据库查询所有没有封面图的播客
2. 为每个播客生成封面图（使用AI图像生成）
3. 上传封面图到云存储
4. 更新数据库中的 `cover_image_url` 字段
5. 支持断点续传（记录已处理的播客，避免重复处理）

## 前置要求

### 1. 环境变量配置

确保以下环境变量已配置：

```bash
# 云数据库配置（必需）
AGC_DATABASE_URL=https://connect-drcn.dbankcloud.cn/agc/apigw/rest/...
AGC_DATABASE_ZONE=your_zone
AGC_DATABASE_OBJECT_TYPE=PodcastInfo
AGC_CLIENT_ID=your_client_id
AGC_CLIENT_SECRET=your_client_secret
AGC_PRODUCT_ID=your_product_id

# 云存储配置（必需，用于上传封面图）
AGC_STORAGE_URL=https://ops-server-drcn.agcstorage.link/v0/
AGC_BUCKET=your_bucket
AGC_STORAGE_CLIENT_ID=your_storage_client_id  # 可选，如果未设置则使用 AGC_CLIENT_ID
AGC_STORAGE_CLIENT_SECRET=your_storage_client_secret  # 可选，如果未设置则使用 AGC_CLIENT_SECRET

# 图像生成API配置（必需）
SILICONFLOW_API_KEY=your_siliconflow_api_key

# 混元大模型API配置（必需，用于生成图像提示词）
HUNYUAN_API_KEY=your_hunyuan_api_key
```

### 2. Python依赖

确保已安装以下Python包：

```bash
pip install requests pillow
```

## 使用方法

### 方法1：作为模块运行（推荐）

```bash
cd d:\Develop\hunyuan
python -m hunyuan_podcast.batch_update_cover_images
```

### 方法2：直接运行脚本

```bash
cd d:\Develop\hunyuan
python hunyuan_podcast/batch_update_cover_images.py
```

## 脚本工作流程

1. **加载进度记录**
   - 从 `outputs/cover_update_progress.json` 加载已处理的播客ID
   - 避免重复处理已完成的播客

2. **查询播客列表**
   - 从云数据库查询所有播客
   - 过滤出没有封面图的播客（`cover_image_url` 为空或不存在）
   - 排除已处理和失败的播客

3. **生成封面图**
   - 使用混元大模型根据播客内容生成图像提示词
   - 调用SiliconFlow API生成封面图
   - 如果API失败，生成占位图

4. **上传封面图**
   - 将生成的封面图上传到云存储
   - 路径格式：`outputs/podcasts/covers/cover_{podcast_id}.png`
   - 如果上传失败，使用base64格式的URL

5. **更新数据库**
   - 将封面图URL保存到数据库的 `cover_image_url` 字段

6. **保存进度**
   - 记录成功和失败的播客ID
   - 支持断点续传

## 进度记录文件

脚本会在 `outputs/cover_update_progress.json` 中保存进度：

```json
{
  "processed_ids": ["podcast_id_1", "podcast_id_2", ...],
  "failed_ids": ["podcast_id_3", ...],
  "last_update_time": 1234567890.123
}
```

**说明：**
- `processed_ids`: 已成功处理的播客ID列表
- `failed_ids`: 处理失败的播客ID列表
- `last_update_time`: 最后更新时间戳

## 日志文件

脚本会生成日志文件：`logs/batch_update_cover_images.log`

日志包含：
- 每个播客的处理状态
- 封面图生成和上传的详细信息
- 错误信息和堆栈跟踪

## 注意事项

1. **API调用限制**
   - 脚本在每次处理后会等待2秒，避免请求过快
   - 如果遇到API限流，可以增加延迟时间

2. **断点续传**
   - 如果脚本中断，重新运行时会跳过已处理的播客
   - 失败的播客不会自动重试，需要手动清理 `failed_ids` 后重新运行

3. **错误处理**
   - 单个播客处理失败不会影响其他播客
   - 所有错误都会记录到日志和进度文件中

4. **资源清理**
   - 临时封面图文件会在上传后自动删除
   - 如果上传失败，临时文件可能保留在 `outputs/` 目录

## 示例输出

```
============================================================
开始批量更新播客封面图
============================================================
已处理: 0 个
失败: 0 个
正在查询所有播客...
共查询到 50 个播客
需要处理的播客: 30 个
============================================================
[1/30] 处理播客: 1234567890_123456
  标题: 测试播客
============================================================
[1234567890_123456] 开始生成封面图提示词...
[1234567890_123456] 生成的图像提示词: Podcast cover art, modern design...
[1234567890_123456] 调用SiliconFlow图像生成API...
[1234567890_123456] 封面图生成成功
[1234567890_123456] 开始上传封面图到云存储: outputs/podcasts/covers/cover_1234567890_123456.png
[1234567890_123456] 封面图上传成功: https://ops-server-drcn.agcstorage.link/v0/bucket/outputs/podcasts/covers/cover_1234567890_123456.png
[1234567890_123456] 数据库更新成功
[1234567890_123456] ✓ 处理成功
...
============================================================
批量更新完成
成功: 28 个
失败: 2 个
总计: 30 个
============================================================
```

## 故障排查

### 问题1：无法连接到数据库

**错误信息：** `无法获取access token`

**解决方案：**
- 检查 `AGC_CLIENT_ID` 和 `AGC_CLIENT_SECRET` 是否正确
- 确认 `AGC_DATABASE_URL` 配置正确
- 检查网络连接

### 问题2：封面图生成失败

**错误信息：** `SiliconFlow API调用失败`

**解决方案：**
- 检查 `SILICONFLOW_API_KEY` 是否正确
- 确认API配额是否充足
- 检查网络连接

### 问题3：上传失败

**错误信息：** `封面图上传失败`

**解决方案：**
- 检查云存储配置（`AGC_STORAGE_URL`, `AGC_BUCKET`）
- 确认有上传权限
- 检查存储空间是否充足

### 问题4：数据库更新失败

**错误信息：** `数据库更新失败`

**解决方案：**
- 检查数据库连接
- 确认字段 `cover_image_url` 已在数据库Schema中添加
- 检查是否有写入权限

## 重新处理失败的播客

如果需要重新处理失败的播客，可以：

1. 编辑 `outputs/cover_update_progress.json`
2. 从 `failed_ids` 中移除要重试的播客ID
3. 重新运行脚本

或者直接删除进度文件，重新处理所有播客（会跳过已有封面图的播客）。

## 性能优化建议

1. **批量处理**
   - 如果播客数量很多，可以分批处理
   - 修改脚本添加 `limit` 参数限制每次处理的数量

2. **并发处理**
   - 可以修改脚本支持多线程/多进程并发处理
   - 注意API调用限制

3. **缓存机制**
   - 对于相同主题的播客，可以复用封面图
   - 添加缓存机制减少API调用

## 相关文件

- 脚本文件：`hunyuan_podcast/batch_update_cover_images.py`
- 进度文件：`outputs/cover_update_progress.json`
- 日志文件：`logs/batch_update_cover_images.log`
- 临时文件：`outputs/cover_{podcast_id}.png`（上传后自动删除）

