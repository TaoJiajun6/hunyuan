# 云存储问题排查指南

## 常见问题：extras为空

当云存储上传失败且 `extras` 为空时，通常表示云存储服务端配置问题。以下是详细的排查步骤。

## 问题现象

- 上传任务启动失败
- 上传过程中失败，但 `extras` 字段为空
- 日志显示：`注意: extras为空，可能是云存储服务端配置问题`

## 排查步骤

### 1. 检查AppGallery Connect配置

#### 1.1 登录AppGallery Connect
1. 访问：https://developer.huawei.com/consumer/cn/service/josp/agc/index.html
2. 登录您的开发者账号
3. 选择对应的项目

#### 1.2 检查云存储服务
1. 在左侧菜单中找到"云存储"服务
2. 确认服务状态为"已开通"
3. 如果未开通，点击"开通服务"

#### 1.3 检查存储实例
1. 进入"云存储" > "文件"标签
2. 检查是否有存储实例（默认实例或自定义实例）
3. 如果没有，需要创建存储实例：
   - 点击"创建存储实例"
   - 选择数据处理位置（建议选择"中国"）
   - 创建成功后，记录实例名称

### 2. 检查应用配置

#### 2.1 检查client_id配置
在 `podcasters/products/phone/src/main/module.json5` 中：

```json5
{
  "module": {
    "metadata": [
      {
        "name": "client_id",
        "value": "您的client_id"  // 必须与AppGallery Connect中的client_id一致
      }
    ]
  }
}
```

**获取client_id的方法**：
1. 登录AppGallery Connect
2. 进入项目设置
3. 查看"应用信息" > "Client ID"

#### 2.2 检查权限配置
在 `module.json5` 中确认已配置网络权限：

```json5
{
  "module": {
    "requestPermissions": [
      {
        "name": "ohos.permission.INTERNET"
      }
    ]
  }
}
```

### 3. 检查云存储权限

#### 3.1 检查安全规则
1. 在AppGallery Connect中进入"云存储" > "安全"标签
2. 检查安全规则配置：
   - 确保允许读取和写入操作
   - 检查路径规则是否正确

#### 3.2 默认安全规则示例
```json
{
  "rules": {
    "hunyuan/*": {
      "read": true,
      "write": true
    }
  }
}
```

### 4. 检查代码配置

#### 4.1 检查GlobalContext初始化
在 `EntryAbility.ets` 中确认已初始化：

```typescript
import { GlobalContext } from '../common/GlobalContext';

onCreate(want: Want, launchParam: AbilityConstant.LaunchParam) {
  // 初始化全局应用上下文
  GlobalContext.initContext(this.context);
  // ...
}
```

#### 4.2 检查云存储初始化
确认 `FileUtils.getStorageBucket()` 正确调用：

```typescript
private static getStorageBucket(): cloudStorage.StorageBucket {
  if (!FileUtils.storageBucket) {
    FileUtils.storageBucket = cloudStorage.bucket(); // 使用默认实例
    // 或指定实例：cloudStorage.bucket('your-bucket-name')
  }
  return FileUtils.storageBucket;
}
```

### 5. 检查网络连接

#### 5.1 测试网络连接
1. 确保设备可以访问互联网
2. 确保可以访问华为AGC服务
3. 检查防火墙设置

#### 5.2 检查代理设置
如果使用代理，确保代理配置正确。

### 6. 检查文件信息

#### 6.1 文件大小限制
- 客户端限制：10MB（在 `FileUtils.MAX_FILE_SIZE` 中定义）
- 服务器限制：50MB（在 `api_server.py` 中定义）

#### 6.2 支持的文件格式
- WAV（推荐）
- MP3
- M4A
- AAC
- OGG
- FLAC
- WMA
- AMR

#### 6.3 文件路径格式
云存储路径格式：`hunyuan/${fileName}`

示例：
- ✅ 正确：`hunyuan/audio.wav`
- ✅ 正确：`hunyuan/voices/audio.wav`
- ❌ 错误：`/hunyuan/audio.wav`（不能以/开头）
- ❌ 错误：`hunyuan/audio.wav/`（不能以/结尾）

### 7. 查看详细日志

#### 7.1 应用日志
查看应用日志中的 `[FileUtils]` 标签：
- 上传任务创建是否成功
- 上传进度信息
- 错误详情

#### 7.2 AppGallery Connect日志
1. 登录AppGallery Connect
2. 进入"云存储" > "用量统计"
3. 查看操作日志和错误日志

### 8. 常见错误代码

| 错误代码 | 含义 | 解决方法 |
|---------|------|---------|
| 401 | 未授权 | 检查client_id配置和权限设置 |
| 403 | 禁止访问 | 检查安全规则配置 |
| 404 | 资源不存在 | 检查存储实例是否存在 |
| 413 | 文件过大 | 检查文件大小是否超过限制 |
| 500 | 服务器错误 | 检查AppGallery Connect服务状态 |

## 测试步骤

### 1. 基础测试
1. 选择一个小文件（<1MB）进行测试
2. 使用WAV格式（最兼容）
3. 检查上传是否成功

### 2. 完整流程测试
1. 选择音频文件
2. 等待上传完成
3. 检查是否获取到云存储URL
4. 使用URL调用后端API
5. 检查播客是否成功生成

## 联系支持

如果以上步骤都无法解决问题：

1. **查看官方文档**：
   - https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/cloudfoundation-storage-upload-file

2. **提交工单**：
   - 在AppGallery Connect中提交技术支持工单

3. **社区支持**：
   - 华为开发者社区：https://developer.huawei.com/consumer/cn/forum/

## 预防措施

1. **定期检查配置**：定期检查AppGallery Connect中的配置是否正确
2. **监控配额**：定期检查云存储配额使用情况
3. **错误处理**：在代码中添加完善的错误处理和用户提示
4. **日志记录**：保留详细的日志记录，便于问题排查

