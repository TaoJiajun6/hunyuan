# ⚠️ 本地模式已废弃

**重要提示**: 本地模式（使用base64编码）已不再支持。所有API接口现在**仅支持云存储URL方式**。

## 变更说明

### 为什么移除base64支持？

1. **请求体过大**: base64编码会增加约33%的数据量，导致请求体过大（1-2MB），容易导致请求超时
2. **传输效率低**: 大请求体在网络传输时容易失败，影响用户体验
3. **服务器压力**: 大请求体增加服务器处理压力，可能导致内存问题

### 现在必须使用云存储URL

所有音色文件必须先上传到云存储，然后使用URL：

```typescript
{
  text: "播客文本内容",
  role_voice_urls: {          // 必须使用云存储URL
    "角色A": "https://your-cloud-storage.com/voices/voice_a.wav",
    "角色B": "https://your-cloud-storage.com/voices/voice_b.wav"
  }
}
```

## 迁移指南

### 前端修改

1. **移除base64编码逻辑**: 不再需要将文件转换为base64
2. **添加上传功能**: 需要先将音色文件上传到云存储
3. **使用URL**: 上传后获取URL，在API请求中使用 `role_voice_urls`

### 示例代码

```typescript
// 1. 上传音色文件到云存储
const uploadVoice = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch('/api/upload', {
    method: 'POST',
    body: formData
  });
  
  const { url } = await response.json();
  return url;
};

// 2. 使用URL生成播客
const generatePodcast = async (text: string, voiceFiles: File[]) => {
  // 上传所有音色文件
  const voiceUrls: Record<string, string> = {};
  for (const [role, file] of Object.entries(voiceFiles)) {
    voiceUrls[role] = await uploadVoice(file);
  }
  
  // 使用URL请求API
  const response = await fetch('/api/v1/podcast/multi_role', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text,
      role_voice_urls: voiceUrls
    })
  });
  
  return response.json();
};
```

## 优势

使用云存储URL方式具有以下优势：

1. **请求体小**: 只传输URL字符串，请求体通常只有几KB
2. **传输稳定**: 不会因为请求体过大导致超时
3. **可复用**: 上传一次，可以多次使用
4. **性能好**: 减少服务器内存压力

## 相关文档

- [云存储配置指南](../CLOUDDB_SETUP.md)
- [API快速开始](../API_QUICKSTART.md)
- [上传客户端文档](../tools/UPLOAD_MUSIC_README.md)
