# 本地模式说明

Web端已修改为**本地模式**，所有内容不再上传到云存储，而是通过本地处理。

## 主要变更

### 1. 音色文件处理

- **之前**: 音色文件上传到云存储，使用URL
- **现在**: 音色文件转换为base64编码，直接发送到API

**实现方式**:
- 从 `public/voices/` 目录读取音色文件
- 使用 `FileReader` 转换为base64编码
- 在API请求中使用 `role_voices` 字段（base64数据）而不是 `role_voice_urls`

### 2. 文本文件处理

- **之前**: 文本文件上传到云存储，使用URL
- **现在**: 文本文件内容直接读取，合并到 `text` 字段

**实现方式**:
- 使用 `file.text()` 读取文件内容
- 多个文件内容合并后放入 `text` 字段
- 不再使用 `text_file_url` 字段

### 3. API请求格式

#### 多角色播客请求

```typescript
{
  text: "播客文本内容",  // 直接文本或从文件读取
  role_voices: {          // base64编码的音色数据
    "角色A": "base64...",
    "角色B": "base64..."
  },
  // 不再使用 role_voice_urls
  // 不再使用 text_file_url
}
```

#### 自定义角色播客请求

```typescript
{
  characters: [
    {
      name: "角色A",
      voice_base64: "base64...",  // base64编码的音色数据
      // 不再使用 voice_url
    }
  ],
  text: "文本素材内容"
}
```

#### 主题深度播客请求

```typescript
{
  topic: "播客主题",
  role_voices: {          // base64编码的音色数据
    "角色A": "base64...",
    "角色B": "base64..."
  },
  // 不再使用 role_voice_urls
}
```

## 优势

1. **无需云存储配置**: 不需要配置云存储服务
2. **更快的响应**: 无需等待文件上传
3. **更简单的部署**: 减少外部依赖
4. **更好的隐私**: 数据不经过云存储

## 注意事项

1. **文件大小限制**: 
   - base64编码会增加约33%的数据量
   - 建议音色文件不超过5MB
   - 文本文件建议不超过10MB

2. **网络传输**:
   - 请求体可能较大，需要确保网络稳定
   - API服务器需要支持较大的请求体

3. **浏览器兼容性**:
   - 使用 `FileReader` API，现代浏览器都支持
   - 需要支持ES6+语法

## 后端支持情况

### 已支持base64的接口

1. **多角色播客** (`/api/v1/podcast/multi_role`)
   - ✅ 支持 `role_voices`: base64编码的音频数据
   - ✅ 支持 `role_voice_urls`: 云存储URL（兼容）
   - ✅ 支持直接文本内容

### 需要后端修改的接口

2. **自定义角色播客** (`/api/v1/podcast/character`)
   - ❌ 当前仅支持 `voice_url`（云存储URL）
   - ⚠️ 需要后端添加 `voice_base64` 字段支持

3. **主题深度播客** (`/api/v1/podcast/deep`)
   - ❌ 当前仅支持 `role_voice_urls`（云存储URL）
   - ⚠️ 需要后端添加 `role_voices` 字段支持

### 后端修改建议

如果需要完全支持本地模式，需要在后端添加：

1. **CharacterInfo** 模型添加 `voice_base64` 字段
2. **DeepPodcastRequest** 模型添加 `role_voices` 字段
3. 处理逻辑中检测base64并使用 `decode_base64_audio` 函数

参考 `api_server.py` 中多角色播客的处理方式（约1788行）。

## 回退到云存储模式

如果需要回退到云存储模式，可以：
1. 恢复 `uploadFile` 相关代码
2. 使用 `role_voice_urls` 和 `text_file_url` 字段
3. 修改 `VoiceSelector` 组件恢复上传逻辑

