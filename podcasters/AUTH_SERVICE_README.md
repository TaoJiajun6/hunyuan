# 用户认证服务说明

## 概述

`AuthService.ets` 提供了华为账号登录和云存储初始化的功能。在使用云存储上传文件之前，必须先完成用户认证。

## 功能说明

### 1. 用户登录

使用华为账号（HWID）进行登录：

```typescript
await AuthService.initializeCloudStorage();
```

### 2. 自动初始化

- 如果用户已登录，直接使用现有凭据初始化云存储
- 如果用户未登录，自动调用 `auth.signIn()` 进行登录
- 登录成功后，使用用户凭据初始化云存储

### 3. 云存储初始化

登录成功后，使用用户凭据初始化云存储：

```typescript
cloudCommon.init({
  credential: credential
});
```

## 使用流程

### 在FileUtils中使用

```typescript
// 上传文件前，先进行用户认证
const authSuccess = await AuthService.initializeCloudStorage();
if (!authSuccess) {
  // 认证失败，无法上传
  return null;
}
// 认证成功，可以上传文件
```

## 配置要求

### 1. 依赖配置

在 `oh-package.json5` 中添加：

```json5
{
  "dependencies": {
    "@hw-agconnect/auth": "^1.9.0"
  }
}
```

### 2. AppGallery Connect配置

1. **开通认证服务**：
   - 登录 AppGallery Connect
   - 开通"认证服务"
   - 启用"华为账号"登录方式

2. **开通云存储服务**：
   - 开通"云存储"服务
   - 创建存储实例（默认实例或自定义实例）
   - 配置安全规则（允许读写操作）

3. **配置应用**：
   - 确保 `module.json5` 中的 `client_id` 正确
   - 确保应用已关联到 AppGallery Connect 项目

## 错误处理

### 常见错误

1. **登录失败**：
   - 检查认证服务是否已开通
   - 检查华为账号登录方式是否已启用
   - 检查网络连接

2. **获取凭据失败**：
   - 检查用户是否已成功登录
   - 检查认证服务配置

3. **云存储初始化失败**：
   - 检查云存储服务是否已开通
   - 检查用户凭据是否有效
   - 检查网络连接

### 错误日志

所有错误都会记录到日志中，包含：
- 错误代码（code）
- 错误消息（message）
- 详细的错误信息

## 注意事项

1. **首次使用**：
   - 首次使用时，会弹出华为账号登录界面
   - 用户需要授权应用访问华为账号

2. **登录状态**：
   - 登录状态会保存在本地
   - 应用重启后，如果用户已登录，会自动使用现有凭据

3. **登出**：
   - 可以调用 `AuthService.signOut()` 登出用户
   - 登出后，需要重新登录才能使用云存储

4. **并发处理**：
   - 如果多个地方同时调用 `initializeCloudStorage()`，只会执行一次初始化
   - 后续调用会等待初始化完成

## 测试建议

1. **测试登录流程**：
   - 首次使用，验证是否弹出登录界面
   - 登录成功后，验证是否能获取用户信息
   - 验证是否能获取用户凭据

2. **测试云存储初始化**：
   - 登录成功后，验证云存储是否初始化成功
   - 验证是否能正常上传文件

3. **测试错误处理**：
   - 测试网络断开时的错误处理
   - 测试认证失败时的错误处理
   - 测试获取凭据失败时的错误处理

## 相关文档

- [华为认证服务文档](https://developer.huawei.com/consumer/cn/doc/harmonyos-references/cloudfoundation-cloudcommon#section136610231214)
- [云存储服务文档](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/cloudfoundation-storage-upload-file)






















