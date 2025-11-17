# Cloud Studio云函数部署指南

本文档说明如何配置华为AGC云函数以连接Cloud Studio API服务器。

## 前置条件

1. **Cloud Studio API服务器已部署**
   - API服务器地址：`https://pexlsj--8000.ap-singapore.cloudstudio.work`
   - 健康检查：`https://pexlsj--8000.ap-singapore.cloudstudio.work/health`
   - API文档：`https://pexlsj--8000.ap-singapore.cloudstudio.work/docs`

2. **华为AGC账号**
   - 已注册华为开发者账号
   - 已开通云函数服务

## 部署步骤

### 1. 准备云函数代码

1. 下载或克隆项目代码
2. 进入 `cloud_function_package` 目录
3. 检查 `podcast-cloud.js` 和 `package.json` 文件

### 2. 创建云函数

1. 登录[华为AGC控制台](https://developer.huawei.com/consumer/cn/agconnect/)
2. 进入"云函数"服务
3. 点击"创建函数"
4. 填写函数信息：
   - 函数名称：`podcast-cloud-function`
   - 运行时：`Node.js 18` 或更高版本
   - 执行超时：`600秒`（10分钟，重要！）

### 3. 上传代码

**方式一：在线编辑**
1. 在云函数控制台选择"在线编辑"
2. 复制 `podcast-cloud.js` 的内容到编辑器
3. 保存

**方式二：上传ZIP包**
1. 创建ZIP文件，包含：
   - `podcast-cloud.js`
   - `package.json`
   - `node_modules/` 目录（或上传后运行 `npm install`）
2. 在云函数控制台上传ZIP包

### 4. 安装依赖

在云函数控制台的终端中执行：

```bash
npm install axios
```

或者上传 `node_modules.zip` 并解压。

### 5. 配置环境变量

在云函数控制台的"配置"页面，添加环境变量：

| 变量名 | 变量值 | 说明 |
|--------|--------|------|
| `BACKEND_API_URL` | `https://pexlsj--8000.ap-singapore.cloudstudio.work` | Cloud Studio API地址 |
| `SKIP_SSL_VERIFY` | `false` | SSL验证（通常为false） |

**重要**：
- 确保URL格式正确，不要包含末尾斜杠
- 如果Cloud Studio使用自签名证书，可以设置 `SKIP_SSL_VERIFY=true`（不推荐）

### 6. 配置HTTP触发器

1. 在云函数控制台选择"触发器"
2. 点击"创建触发器"
3. 选择"HTTP触发器"
4. 配置触发器：
   - 触发方式：`HTTP请求`
   - 认证方式：`无认证` 或 `APP认证`（根据需要）
   - 请求方法：`GET, POST, OPTIONS`
5. 保存触发器配置
6. **记录触发器URL**（后续在APP中使用）

### 7. 测试云函数

#### 健康检查测试

**请求**：
```bash
curl -X GET "https://your-cloud-function-url.com?path=health"
```

**预期响应**：
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "service": "混元AI播客生成API"
  }
}
```

#### 多角色播客测试

**请求**：
```bash
curl -X POST "https://your-cloud-function-url.com" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "[角色A]你好 [角色B]你好啊",
    "role_voices": {
      "角色A": "base64音频数据...",
      "角色B": "base64音频数据..."
    },
    "silence_interval": 300
  }'
```

### 8. 配置APP使用云函数

在 `PodcastService.ets` 中配置：

```typescript
export class PodcastConfig {
  // 使用云函数URL（替换为实际的触发器URL）
  static readonly API_BASE_URL: string = 'https://your-cloud-function-url.com';
  static readonly API_TIMEOUT: number = 600000; // 10分钟超时
  static readonly USE_CLOUD_FUNCTION: boolean = true; // 启用云函数模式
}
```

## 故障排查

### 1. 连接失败

**问题**：云函数无法连接到Cloud Studio API服务器

**解决方案**：
- 检查 `BACKEND_API_URL` 环境变量是否正确
- 检查Cloud Studio服务器是否运行
- 检查网络连接
- 查看云函数日志

### 2. 超时错误

**问题**：请求超时（504错误）

**解决方案**：
- 增加云函数执行超时时间（建议10分钟）
- 检查Cloud Studio服务器性能
- 优化音频文件大小
- 查看后端服务器日志

### 3. SSL证书错误

**问题**：SSL证书验证失败

**解决方案**：
- 如果Cloud Studio使用有效证书，确保云函数可以访问HTTPS
- 如果使用自签名证书，设置 `SKIP_SSL_VERIFY=true`（仅用于测试）

### 4. 请求大小限制

**问题**：请求体过大（413错误）

**解决方案**：
- 减小音频文件大小（建议每个文件小于10MB）
- 检查云函数的请求大小限制
- 使用压缩的音频格式

### 5. 参数错误

**问题**：400错误，参数验证失败

**解决方案**：
- 检查请求参数格式
- 查看API文档：`https://pexlsj--8000.ap-singapore.cloudstudio.work/docs`
- 查看错误响应中的详细错误信息

## 监控和日志

### 查看云函数日志

1. 在云函数控制台选择"日志"
2. 查看执行日志和错误日志
3. 搜索关键词：`转发请求到`、`健康检查`、`后端API请求失败`

### 监控指标

- 执行次数
- 执行时间
- 错误率
- 超时次数

## 性能优化

### 1. 超时设置

- 云函数代码超时：10分钟（600000毫秒）
- 云函数执行超时：10分钟（600秒）
- 确保两者匹配

### 2. 请求大小

- 限制音频文件大小（建议每个文件小于10MB）
- 使用压缩的音频格式
- 考虑分块上传大文件

### 3. 并发处理

- 云函数支持并发执行
- 注意后端服务器的并发限制
- 监控资源使用情况

## 安全建议

1. **使用APP认证**：
   - 在生产环境中使用APP认证
   - 保护云函数URL不被滥用

2. **环境变量保护**：
   - 不要将敏感信息硬编码在代码中
   - 使用环境变量存储配置

3. **HTTPS连接**：
   - 使用HTTPS连接到Cloud Studio
   - 验证SSL证书（生产环境）

4. **访问控制**：
   - 限制云函数的访问来源
   - 使用IP白名单（如果可能）

## 更新和维护

### 更新云函数代码

1. 修改 `podcast-cloud.js` 文件
2. 在云函数控制台上传新代码
3. 测试新版本
4. 部署到生产环境

### 更新环境变量

1. 在云函数控制台修改环境变量
2. 重新部署云函数
3. 验证配置生效

### 监控后端服务器

1. 定期检查Cloud Studio服务器状态
2. 监控API响应时间
3. 查看错误日志
4. 及时处理问题

## 参考资源

- [Cloud Studio部署指南](../../CLOUD_STUDIO_DEPLOYMENT.md)
- [API文档](https://pexlsj--8000.ap-singapore.cloudstudio.work/docs)
- [华为AGC云函数文档](https://developer.huawei.com/consumer/cn/doc/agconnect-cloud-function)
- [云函数README](./README.md)

## 支持

如有问题，请查看：
- 云函数日志
- Cloud Studio服务器日志
- API文档
- 项目文档

---

最后更新: 2024-01-XX
























