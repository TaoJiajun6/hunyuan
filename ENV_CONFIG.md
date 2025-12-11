# 环境变量配置说明

## .env 文件配置

项目根目录下的 `.env` 文件用于配置 AGC 云存储上传相关的环境变量。

### 必需的环境变量

在项目根目录创建 `.env` 文件，并配置以下变量：

```bash
# AGC 云存储配置
AGC_STORAGE_URL=https://ops-server-drcn.agcstorage.link/v0/
AGC_BUCKET=your-bucket-name
AGC_PRODUCT_ID=your-product-id

# 云存储专用凭证（推荐，如果云存储和云数据库使用不同的client_id）
AGC_STORAGE_CLIENT_ID=your-storage-client-id
AGC_STORAGE_CLIENT_SECRET=your-storage-client-secret
# 云存储专用域名（可选，默认值：connect-api.cloud.huawei.com）
AGC_STORAGE_DOMAIN=connect-api.cloud.huawei.com

# 云数据库专用凭证（推荐，如果云存储和云数据库使用不同的client_id）
AGC_DATABASE_CLIENT_ID=your-database-client-id
AGC_DATABASE_CLIENT_SECRET=your-database-client-secret
# 云数据库专用域名（可选，默认值：connect-drcn.dbankcloud.cn）
AGC_DATABASE_DOMAIN=connect-drcn.dbankcloud.cn

# 通用凭证（如果云存储和云数据库使用相同的client_id，可以只配置这个）
# 如果配置了上面的专用凭证，这些会被忽略
AGC_CLIENT_ID=your-client-id
AGC_CLIENT_SECRET=your-client-secret
# 通用域名（可选，如果云存储和云数据库使用相同的域名）
# 如果配置了上面的专用域名，这些会被忽略
AGC_DOMAIN=connect-api.cloud.huawei.com
```

### 配置说明

1. **AGC_STORAGE_URL**: 云存储服务的基础URL
   - 格式：`https://ops-server-drcn.agcstorage.link/v0/`
   - 注意：必须以 `/v0/` 结尾

2. **AGC_BUCKET**: 云存储实例名称
   - 例如：`podcasters-y0qig`

3. **AGC_STORAGE_CLIENT_ID** / **AGC_STORAGE_CLIENT_SECRET**: 云存储专用凭证（**强烈推荐**）
   - **必须**：从 AGC 控制台的**云存储项目**中获取
   - 在 AGC 控制台 > 我的项目 > 项目设置 > 常规 中查看
   - 如果云存储和云数据库使用不同的项目，**必须**分别配置
   - ⚠️ **重要**：请妥善保管，不要提交到代码仓库
   - ⚠️ **注意**：如果使用云数据库项目的 client_id，会导致 "invalid client id" 错误

4. **AGC_DATABASE_CLIENT_ID** / **AGC_DATABASE_CLIENT_SECRET**: 云数据库专用凭证（**强烈推荐**）
   - **必须**：从 AGC 控制台的**云数据库项目**中获取
   - 在 AGC 控制台 > 我的项目 > 项目设置 > 常规 中查看
   - 如果云存储和云数据库使用不同的项目，**必须**分别配置
   - ⚠️ **重要**：请妥善保管，不要提交到代码仓库

5. **AGC_CLIENT_ID** / **AGC_CLIENT_SECRET**: 通用凭证（可选）
   - 如果云存储和云数据库使用相同的 client_id，可以只配置这个
   - 如果配置了专用凭证（AGC_STORAGE_* 或 AGC_DATABASE_*），这些会被忽略
   - 从 AGC 控制台获取
   - ⚠️ **重要**：请妥善保管，不要提交到代码仓库

6. **AGC_PRODUCT_ID**: AGC 项目ID（productId）
   - 从 AGC 控制台获取
   - 对应 Java 参考代码中的 `projectId`

7. **AGC_STORAGE_DOMAIN**: 云存储专用域名（可选）
   - 默认值：`connect-api.cloud.huawei.com`（中国站点）
   - 支持的站点域名：
     - `connect-api.cloud.huawei.com` - 中国站点
     - `connect-api-dre.cloud.huawei.com` - 德国站点
     - `connect-api-dra.cloud.huawei.com` - 新加坡站点
     - `connect-api-drru.cloud.huawei.com` - 俄罗斯站点
   - **重要**：必须与项目设置的数据处理位置对应
   - **注意**：代码会根据 `AGC_STORAGE_URL` 自动推断正确的 Token 接口和域名，此参数主要用于没有 `AGC_STORAGE_URL` 的情况或覆盖自动推断

8. **AGC_DATABASE_DOMAIN**: 云数据库专用域名（可选）
   - 默认值：`connect-drcn.dbankcloud.cn`
   - 用于云数据库获取 access_token

9. **AGC_DOMAIN**: 通用域名（可选）
   - 默认值：`connect-api.cloud.huawei.com`
   - 如果云存储和云数据库使用相同的域名，可以只配置这个
   - 如果配置了专用域名（`AGC_STORAGE_DOMAIN` 或 `AGC_DATABASE_DOMAIN`），这些会被忽略

### 配置优先级

环境变量的读取优先级：
1. **函数参数**（如果直接调用 `upload_generated_podcast`）
2. **环境变量**（从 `.env` 文件或系统环境变量）
3. **agc-apiclient-*.json 文件**（在 `hunyuan_podcast/` 目录下）

### 示例 .env 文件

```bash
# AGC 云存储配置
AGC_STORAGE_URL=https://ops-server-drcn.agcstorage.link/v0/
AGC_BUCKET=podcasters-y0qig
AGC_PRODUCT_ID=461323198430936564

# 云存储专用凭证（推荐）
AGC_STORAGE_CLIENT_ID=84903XXXXXX32064
AGC_STORAGE_CLIENT_SECRET=00E5CCADB655891XXXXXXXXXXXX8CDCC83ACF22
AGC_STORAGE_DOMAIN=connect-api.cloud.huawei.com

# 云数据库专用凭证（推荐，如果使用云数据库功能）
AGC_DATABASE_CLIENT_ID=26XXXXXXXX20
AGC_DATABASE_CLIENT_SECRET=************************
AGC_DATABASE_DOMAIN=connect-drcn.dbankcloud.cn

# 或者使用通用凭证（如果云存储和云数据库使用相同的client_id和域名）
# AGC_CLIENT_ID=84903XXXXXX32064
# AGC_CLIENT_SECRET=00E5CCADB655891XXXXXXXXXXXX8CDCC83ACF22
# AGC_DOMAIN=connect-api.cloud.huawei.com
```

### 验证配置

启动 API 服务器后，检查日志中是否有以下信息：
- `检测到 .env 文件，正在加载环境变量: ...`
- 上传时日志中应显示正确的 URL 和配置信息

### 注意事项

1. `.env` 文件不应提交到 Git 仓库（应在 `.gitignore` 中）
2. 如果使用 `agc-apiclient-*.json` 文件，可以不在 `.env` 中配置凭证
3. **云存储和云数据库使用不同的凭证和域名**：
   - 云存储使用 `AGC_STORAGE_CLIENT_ID` / `AGC_STORAGE_CLIENT_SECRET` / `AGC_STORAGE_DOMAIN`
   - 云数据库使用 `AGC_DATABASE_CLIENT_ID` / `AGC_DATABASE_CLIENT_SECRET` / `AGC_DATABASE_DOMAIN`
   - 如果两者使用相同的凭证和域名，可以只配置 `AGC_CLIENT_ID` / `AGC_CLIENT_SECRET` / `AGC_DOMAIN`
   - ⚠️ **重要**：如果云存储和云数据库是不同的项目，**必须**分别配置，否则会出现 "invalid client id" 错误
4. **常见错误**：
   - 错误：`invalid client id` 或 `203882498`
   - 原因：使用了云数据库项目的 client_id 来访问云存储，或反之
   - 解决：确保 `AGC_STORAGE_CLIENT_ID` 是云存储项目的凭证，`AGC_DATABASE_CLIENT_ID` 是云数据库项目的凭证
5. 服务器重启后，需要确保 `.env` 文件被正确加载

