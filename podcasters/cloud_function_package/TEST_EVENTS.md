# 云函数测试事件

本文档提供华为AGC云函数控制台测试界面使用的测试事件JSON。

## 测试事件格式

在华为AGC云函数控制台的测试界面中，需要提供完整的事件对象。以下是各种测试场景的事件JSON。

## 1. 健康检查测试

测试后端API服务器连接是否正常。

```json
{
  "httpMethod": "GET",
  "path": "health",
  "queryStringParameters": {
    "path": "health"
  }
}
```

**或者更简单的格式**：

```json
{
  "httpMethod": "GET",
  "path": "health"
}
```

**预期响应**：
```json
{
  "statusCode": 200,
  "body": "{\"success\":true,\"data\":{\"status\":\"healthy\",\"service\":\"混元AI播客生成API\"}}"
}
```

## 2. 多角色互动播客测试

**注意**：base64音频数据很长，这里使用占位符。实际测试时需要使用真实的base64编码音频数据。

```json
{
  "httpMethod": "POST",
  "path": "api/v1/podcast/multi_role",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": "{\"text\":\"[角色A]你好，欢迎收听我们的播客。\\n[角色B]你好，今天我们要聊一个很有意思的话题。\\n[角色A]是的，关于人工智能的发展。\\n[角色B]这个话题确实很有意思。\",\"role_voices\":{\"角色A\":\"UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=\",\"角色B\":\"UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=\"},\"silence_interval\":300}"
}
```

**简化版本（如果body可以直接是对象）**：

```json
{
  "httpMethod": "POST",
  "path": "api/v1/podcast/multi_role",
  "body": {
    "text": "[角色A]你好，欢迎收听我们的播客。\n[角色B]你好，今天我们要聊一个很有意思的话题。\n[角色A]是的，关于人工智能的发展。\n[角色B]这个话题确实很有意思。",
    "role_voices": {
      "角色A": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=",
      "角色B": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA="
    },
    "silence_interval": 300
  }
}
```

## 3. 自定义角色播客测试

```json
{
  "httpMethod": "POST",
  "path": "api/v1/podcast/character",
  "body": {
    "characters": [
      {
        "name": "小明",
        "identity": "AI研究员",
        "personality": "严谨、专业",
        "catchphrase": "从技术角度来说",
        "speaking_style": "逻辑清晰，用词准确",
        "relationship": "与小红是同事关系",
        "voice": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA="
      },
      {
        "name": "小红",
        "identity": "科技记者",
        "personality": "活泼、好奇",
        "catchphrase": "真的吗？",
        "speaking_style": "轻松幽默，喜欢提问",
        "relationship": "与小明的同事关系",
        "voice": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA="
      }
    ],
    "topic": "人工智能的未来发展",
    "silence_interval": 300
  }
}
```

## 4. 主题深度播客测试

```json
{
  "httpMethod": "POST",
  "path": "api/v1/podcast/deep",
  "body": {
    "topic": "人工智能对社会的影响",
    "role_voices": {
      "角色A": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=",
      "角色B": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA="
    },
    "num_characters": 2,
    "depth_level": "深度",
    "silence_interval": 300
  }
}
```

## 5. 使用查询参数指定类型

如果路径不能明确指定类型，可以使用查询参数：

```json
{
  "httpMethod": "POST",
  "queryStringParameters": {
    "type": "multi_role"
  },
  "body": {
    "text": "[角色A]你好 [角色B]你好啊",
    "role_voices": {
      "角色A": "base64音频数据...",
      "角色B": "base64音频数据..."
    }
  }
}
```

## 测试步骤

1. **打开测试界面**
   - 在华为AGC云函数控制台，找到您的云函数
   - 点击"测试"或"事件测试"按钮

2. **选择测试事件**
   - 在测试界面中，选择"创建新测试事件"或"编辑测试事件"
   - 将上面的JSON复制到输入框中

3. **格式化JSON**
   - 点击"format"按钮格式化JSON（如果可用）
   - 确保JSON格式正确

4. **执行测试**
   - 点击"测试"按钮
   - 等待测试结果

5. **查看结果**
   - 查看返回的响应
   - 检查状态码和响应体
   - 查看日志输出

## 注意事项

### 1. Base64音频数据

- 测试事件中的base64数据是占位符，实际测试需要使用真实的音频文件base64编码
- 音频文件应该小于10MB
- 可以使用在线工具将音频文件转换为base64

### 2. 环境变量

确保云函数已配置环境变量：
- `BACKEND_API_URL`: Cloud Studio API地址
- 例如：`https://pexlsj--8000.ap-singapore.cloudstudio.work`

### 3. 超时设置

- 播客生成可能需要较长时间（1-5分钟）
- 确保云函数执行超时时间设置足够长（建议10分钟）

### 4. Body格式

- 如果云函数期望body是字符串，使用 `"body": "{\"key\":\"value\"}"`
- 如果云函数期望body是对象，使用 `"body": {"key": "value"}`
- 根据实际云函数实现调整

## 获取真实的Base64音频数据

### 方法1：使用在线工具

1. 访问在线base64编码工具
2. 上传音频文件（WAV格式推荐）
3. 复制base64编码结果

### 方法2：使用命令行

```bash
# Linux/Mac
base64 -i audio.wav

# Windows PowerShell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("audio.wav"))
```

### 方法3：使用Node.js

```javascript
const fs = require('fs');
const audioData = fs.readFileSync('audio.wav');
const base64 = audioData.toString('base64');
console.log(base64);
```

## 常见错误

### 1. 连接失败

**错误**：`无法连接到后端服务器`

**解决方案**：
- 检查 `BACKEND_API_URL` 环境变量是否正确
- 检查Cloud Studio服务器是否运行
- 检查网络连接

### 2. 超时错误

**错误**：`请求超时`

**解决方案**：
- 增加云函数执行超时时间
- 使用较小的音频文件测试
- 检查后端服务器性能

### 3. 参数错误

**错误**：`Missing required parameters`

**解决方案**：
- 检查请求体格式是否正确
- 确保所有必需字段都已提供
- 查看API文档确认参数格式

### 4. Base64解码失败

**错误**：`音频解码失败`

**解决方案**：
- 检查base64数据是否完整
- 确保base64数据格式正确
- 尝试使用真实的音频文件

## 测试建议

1. **先测试健康检查**
   - 确保后端服务器连接正常
   - 验证环境变量配置正确

2. **使用小文件测试**
   - 使用较小的音频文件（<1MB）
   - 减少测试时间
   - 快速验证功能

3. **查看日志**
   - 查看云函数执行日志
   - 查看后端服务器日志
   - 诊断问题

4. **逐步测试**
   - 先测试简单的请求
   - 再测试复杂的请求
   - 逐步增加复杂度

## 参考

- [API文档](https://pexlsj--8000.ap-singapore.cloudstudio.work/docs)
- [云函数README](./README.md)
- [部署指南](./DEPLOYMENT_CLOUD_STUDIO.md)

