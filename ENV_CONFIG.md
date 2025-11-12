# 环境变量配置说明

## .env 文件配置

项目根目录下的 `.env` 文件用于配置 AGC 云存储上传相关的环境变量。

### 必需的环境变量

在项目根目录创建 `.env` 文件，并配置以下变量：

```bash
# AGC 云存储配置
AGC_STORAGE_URL=https://ops-server-drcn.agcstorage.link/v0/
AGC_BUCKET=your-bucket-name
AGC_CLIENT_ID=your-client-id
AGC_CLIENT_SECRET=your-client-secret
AGC_PRODUCT_ID=your-product-id

# AGC 域名（可选，默认值：connect-api.cloud.huawei.com）
AGC_DOMAIN=connect-api.cloud.huawei.com
```

### 配置说明

1. **AGC_STORAGE_URL**: 云存储服务的基础URL
   - 格式：`https://ops-server-drcn.agcstorage.link/v0/`
   - 注意：必须以 `/v0/` 结尾

2. **AGC_BUCKET**: 云存储实例名称
   - 例如：`podcasters-y0qig`

3. **AGC_CLIENT_ID**: AGC API 客户端ID
   - 从 AGC 控制台获取

4. **AGC_CLIENT_SECRET**: AGC API 客户端密钥
   - 从 AGC 控制台获取
   - ⚠️ **重要**：请妥善保管，不要提交到代码仓库

5. **AGC_PRODUCT_ID**: AGC 项目ID（productId）
   - 从 AGC 控制台获取
   - 对应 Java 参考代码中的 `projectId`

6. **AGC_DOMAIN**: AGC API 域名（可选）
   - 默认值：`connect-api.cloud.huawei.com`
   - 用于获取 access_token

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
AGC_CLIENT_ID=84903XXXXXX32064
AGC_CLIENT_SECRET=00E5CCADB655891XXXXXXXXXXXX8CDCC83ACF22
AGC_PRODUCT_ID=461323198430936564
AGC_DOMAIN=connect-api.cloud.huawei.com
```

### 验证配置

启动 API 服务器后，检查日志中是否有以下信息：
- `检测到 .env 文件，正在加载环境变量: ...`
- 上传时日志中应显示正确的 URL 和配置信息

### 注意事项

1. `.env` 文件不应提交到 Git 仓库（应在 `.gitignore` 中）
2. 如果使用 `agc-apiclient-*.json` 文件，可以不在 `.env` 中配置 `AGC_CLIENT_ID` 和 `AGC_CLIENT_SECRET`
3. 服务器重启后，需要确保 `.env` 文件被正确加载

