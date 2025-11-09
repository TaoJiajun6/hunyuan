# 混元AI播客生成云函数

## 概述

这是一个华为AGC云函数，作为代理层转发播客生成请求到后端API服务器。该云函数提供统一的API接口，客户端只需要知道云函数的URL，无需关心后端服务器的具体地址。

## 功能特性

1. **多角色互动播客**：将文本素材转化为多角色自然互动的播客音频
2. **自定义角色播客**：根据用户自定义的角色人设和音色生成契合风格的播客音频
3. **主题深度播客**：基于指定主题生成有深度、引发思考的播客音频
4. **健康检查**：检查后端服务器状态

## 文件结构

```
cloud_function_package/
├── podcast-cloud.js          # 主云函数文件
├── package.json              # 包配置文件
├── node_modules/            # 依赖包（需要npm install）
├── node_modules.zip         # 依赖包压缩文件（可选）
└── README.md                # 本说明文件
```

## 配置说明

### 环境变量

在华为AGC云函数控制台中配置以下环境变量：

- `BACKEND_API_URL`: 后端API服务器地址（例如：`http://10.10.210.52:8000`）

如果不设置环境变量，将使用默认值 `http://10.10.210.52:8000`。

## 部署步骤

### 1. 准备文件

1. 将 `podcast-cloud.js` 和 `package.json` 上传到云函数
2. 安装依赖：在云函数控制台执行 `npm install`，或上传 `node_modules.zip` 并解压

### 2. 配置环境变量

在云函数控制台中设置环境变量：
- `BACKEND_API_URL`: 您的后端API服务器地址

### 3. 配置触发器

配置HTTP触发器，设置：
- 触发方式：HTTP请求
- 认证方式：根据需要选择（建议使用APP认证）

### 4. 获取云函数URL

部署完成后，在云函数控制台获取云函数的HTTP触发URL。

## API接口说明

### 1. 健康检查

**请求方式**: GET

**路径**: `/health` 或根路径 `/`

**响应**:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "service": "混元AI播客生成API"
  }
}
```

### 2. 多角色互动播客

**请求方式**: POST

**路径**: `/api/v1/podcast/multi_role`

**请求体**:
```json
{
  "text": "播客文本内容（支持角色标记如[角色A]你好 [角色B]你好啊）",
  "role_voices": {
    "角色A": "base64编码的音频数据",
    "角色B": "base64编码的音频数据"
  },
  "silence_interval": 300
}
```

**响应**:
```json
{
  "success": true,
  "message": "播客生成成功",
  "data": {
    "audio_base64": "base64编码的音频数据",
    "audio_path": "输出文件路径",
    "file_size_mb": 2.5,
    "script": "生成的播客脚本",
    "roles": ["角色A", "角色B"]
  }
}
```

### 3. 自定义角色播客

**请求方式**: POST

**路径**: `/api/v1/podcast/character`

**请求体**:
```json
{
  "characters": [
    {
      "name": "角色A",
      "identity": "身份/职业",
      "personality": "核心性格",
      "catchphrase": "口头禅",
      "speaking_style": "说话风格",
      "relationship": "与其他角色的关系",
      "voice": "base64编码的音频数据"
    },
    {
      "name": "角色B",
      "identity": "身份/职业",
      "personality": "核心性格",
      "voice": "base64编码的音频数据"
    }
  ],
  "topic": "播客主题（可选）",
  "silence_interval": 300
}
```

**响应**:
```json
{
  "success": true,
  "message": "播客生成成功",
  "data": {
    "audio_base64": "base64编码的音频数据",
    "audio_path": "输出文件路径",
    "file_size_mb": 2.5,
    "script": "生成的播客脚本",
    "characters": ["角色A", "角色B"]
  }
}
```

### 4. 主题深度播客

**请求方式**: POST

**路径**: `/api/v1/podcast/deep`

**请求体**:
```json
{
  "topic": "播客主题",
  "role_voices": {
    "角色A": "base64编码的音频数据",
    "角色B": "base64编码的音频数据"
  },
  "num_characters": 2,
  "depth_level": "深度",
  "silence_interval": 300
}
```

**响应**:
```json
{
  "success": true,
  "message": "播客生成成功",
  "data": {
    "audio_base64": "base64编码的音频数据",
    "audio_path": "输出文件路径",
    "file_size_mb": 2.5,
    "script": "生成的播客脚本",
    "topic": "播客主题",
    "depth_level": "深度"
  }
}
```

## 测试方法

### 1. 本地测试

```bash
# 安装依赖
npm install

# 设置环境变量
export BACKEND_API_URL="http://10.10.210.52:8000"

# 测试云函数
node -e "
const { myHandler } = require('./podcast-cloud.js');
const event = {
  body: JSON.stringify({
    text: '[角色A]你好 [角色B]你好啊',
    role_voices: {
      '角色A': 'base64音频数据...',
      '角色B': 'base64音频数据...'
    }
  })
};
myHandler(event, {}, (result) => console.log(JSON.stringify(result, null, 2)));
"
```

### 2. 云函数控制台测试

在华为AGC云函数控制台中，使用以下测试事件：

**健康检查测试**:
```json
{
  "path": "health",
  "httpMethod": "GET"
}
```

**多角色播客测试**:
```json
{
  "path": "api/v1/podcast/multi_role",
  "httpMethod": "POST",
  "body": "{\"text\":\"[角色A]你好 [角色B]你好啊\",\"role_voices\":{\"角色A\":\"base64音频数据...\",\"角色B\":\"base64音频数据...\"}}"
}
```

## 错误处理

云函数会返回统一的错误格式：

```json
{
  "success": false,
  "message": "错误描述",
  "error": "详细错误信息"
}
```

常见错误：
- `400`: 请求参数错误
- `503`: 无法连接到后端服务器
- `500`: 服务器内部错误

## 注意事项

1. **超时设置**：播客生成可能需要较长时间（1-5分钟），确保云函数超时时间设置足够长（建议5分钟以上）
2. **请求大小限制**：音频文件base64编码后可能较大，注意云函数的请求大小限制
3. **后端服务器**：确保后端API服务器正常运行且可以访问
4. **CORS配置**：云函数已配置CORS，允许跨域请求

## 在HarmonyOS APP中使用

在 `PodcastService.ets` 中配置云函数URL：

```typescript
export class PodcastConfig {
  // 使用云函数URL
  static readonly API_BASE_URL: string = 'https://your-cloud-function-url.com';
  static readonly API_TIMEOUT: number = 300000; // 5分钟超时
}
```

## 许可证

本项目基于混元AI播客生成系统开发，请遵循相应的许可证要求。
