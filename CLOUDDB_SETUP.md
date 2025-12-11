# AGC CloudDB 配置说明

## 问题说明

如果遇到错误：`the type of clientId not match`，说明 CloudDB REST API 需要使用**服务端 API Key**，而不是 OAuth client_id。

## 配置步骤

### 1. 在 AGC 控制台创建服务端 API Key

1. 登录 [华为 AGC 控制台](https://developer.huawei.com/consumer/cn/service/josp/agc/index.html)
2. 进入 **我的项目** > 选择你的项目
3. 进入 **API管理** > **凭据**
4. 点击 **创建凭据**
5. 选择 **服务端 API Key**（不是 OAuth 客户端）
6. 复制生成的 API Key

### 2. 配置环境变量

在服务器上设置环境变量：

**Windows (PowerShell):**
```powershell
$env:AGC_API_KEY = "你的API_KEY"
$env:AGC_PRODUCT_ID = "你的项目ID"
$env:AGC_DOMAIN = "connect-drcn.dbankcloud.cn"  # 可选，默认值
$env:AGC_CLOUD_DB_ZONE = "cloudDBZone"  # 可选，默认值
```

**Linux/Mac:**
```bash
export AGC_API_KEY="你的API_KEY"
export AGC_PRODUCT_ID="你的项目ID"
export AGC_DOMAIN="connect-drcn.dbankcloud.cn"  # 可选
export AGC_CLOUD_DB_ZONE="cloudDBZone"  # 可选
```

### 3. 验证配置

重启服务器后，生成一个播客，检查日志中是否有：
```
播客元数据已保存到AGC云数据库
```

如果没有，检查日志中的错误信息。

## 注意事项

1. **API Key vs OAuth Client ID**：
   - CloudDB REST API 需要使用 **服务端 API Key**
   - OAuth Client ID 用于客户端应用，不适用于服务端 REST API

2. **存储区名称**：
   - 默认存储区名称是 `cloudDBZone`
   - 如果创建了自定义存储区，请设置 `AGC_CLOUD_DB_ZONE` 环境变量

3. **对象类型名称**：
   - 代码中使用的对象类型名称是 `PodcastInfo`
   - 确保在 AGC 控制台创建的对象类型名称与此一致

## 测试连接

生成一个播客后，可以通过以下方式验证：

1. 查看服务器日志，确认是否有保存成功的消息
2. 在 AGC 控制台 > CloudDB > 数据管理 中查看是否有数据
3. 调用 `/api/v1/podcast/history` API，检查返回的数据是否包含云数据库中的播客

## 故障排查

### 错误：`the type of clientId not match`
- **原因**：使用了 OAuth client_id 而不是 API Key
- **解决**：在 AGC 控制台创建服务端 API Key，并设置 `AGC_API_KEY` 环境变量

### 错误：`无法获取access token`
- **原因**：未配置 API Key 或 OAuth 凭证
- **解决**：按照上述步骤配置 `AGC_API_KEY` 或 OAuth 凭证

### 错误：`对象类型不存在`
- **原因**：CloudDB 中未创建 `PodcastInfo` 对象类型
- **解决**：在 AGC 控制台创建 `PodcastInfo` 对象类型，字段类型与代码中的 schema 一致

