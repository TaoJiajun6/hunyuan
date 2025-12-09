# 流式播客生成与播放指南

## 概述

本功能实现了**边生成边播放**的流式播客生成，大幅减少用户等待时间。系统会在生成每一段对话音频后立即推送给前端，前端可以实时解码并播放，实现"边加载边听"的流畅体验。

## 技术实现

### 后端实现

1. **流式TTS生成** (`hunyuan_podcast/soulx_tts.py`)
   - 新增 `infer_multi_speaker_streaming()` 方法
   - 逐段生成音频并yield音频片段
   - 支持静音间隔插入

2. **流式播客生成器** (`hunyuan_podcast/podcast_generator.py`)
   - 新增 `generate_from_text_streaming()` 方法
   - 封装流式TTS调用，提供统一的流式接口

3. **流式API端点** (`hunyuan_podcast/api_server.py`)
   - 新增 `/api/v1/podcast/stream` 端点
   - 使用 Server-Sent Events (SSE) 推送音频流
   - 每个音频片段以base64编码的WAV格式推送

### 前端实现

- 使用 Fetch API 的流式读取功能接收SSE数据
- 使用 Web Audio API 解码和播放音频
- 实现音频队列管理，确保连续播放
- 支持暂停、继续、停止等控制功能

## API 使用说明

### 端点

```
POST /api/v1/podcast/stream
```

### 请求参数

与 `/api/v1/podcast/multi_role` 接口相同：

```json
{
    "text": "播客文本内容（支持角色标记）",
    "role_voice_urls": {
        "角色A": "https://example.com/voice1.wav",
        "角色B": "https://example.com/voice2.wav"
    },
    "silence_interval": 800,
    "input_type": "文字",
    "instruction": "可选指令"
}
```

### 响应格式（SSE流）

每个事件包含一个JSON对象：

```json
{
    "type": "audio_segment" | "progress" | "error" | "complete",
    "segment_index": 0,
    "audio_base64": "base64编码的WAV音频数据",
    "is_silence": false,
    "role_name": "角色A",
    "progress": 50,
    "message": "正在生成第3段对话...",
    "error": "错误信息"
}
```

### 事件类型说明

- **audio_segment**: 音频片段数据
  - `segment_index`: 片段索引
  - `audio_base64`: base64编码的WAV音频（24000Hz采样率，单声道）
  - `is_silence`: 是否为静音片段
  - `role_name`: 角色名称（静音片段为null）

- **progress**: 进度更新
  - `progress`: 进度百分比（0-100）
  - `message`: 进度消息

- **error**: 错误信息
  - `error`: 错误描述

- **complete**: 生成完成
  - `message`: 完成消息

## 前端集成示例

### 使用 Fetch API + Web Audio API

```javascript
// 初始化AudioContext
const audioContext = new AudioContext();
let audioQueue = [];
let isPlaying = false;

// 发送请求并处理流
const response = await fetch('/api/v1/podcast/stream', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        text: "播客文本",
        role_voice_urls: {
            "角色A": "https://...",
            "角色B": "https://..."
        }
    })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();
let buffer = '';

while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';
    
    for (const line of lines) {
        if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6));
            
            if (data.type === 'audio_segment') {
                // 解码base64音频
                const audioData = atob(data.audio_base64);
                const arrayBuffer = new ArrayBuffer(audioData.length);
                const view = new Uint8Array(arrayBuffer);
                for (let i = 0; i < audioData.length; i++) {
                    view[i] = audioData.charCodeAt(i);
                }
                
                // 解码音频并添加到队列
                const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
                audioQueue.push(audioBuffer);
                
                // 如果当前没有播放，开始播放
                if (!isPlaying) {
                    playAudioQueue();
                }
            }
        }
    }
}

// 播放音频队列
async function playAudioQueue() {
    if (audioQueue.length === 0) {
        isPlaying = false;
        return;
    }
    
    isPlaying = true;
    const audioBuffer = audioQueue.shift();
    const source = audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContext.destination);
    source.onended = () => playAudioQueue();
    source.start();
}
```

### 使用 EventSource（仅GET请求）

如果后端支持GET请求，可以使用EventSource：

```javascript
const eventSource = new EventSource('/api/v1/podcast/stream?text=...');
eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    // 处理数据...
};
```

## 完整示例

查看 `streaming_audio_example.html` 获取完整的前端示例代码，包括：
- 表单输入
- 流式数据接收
- 音频队列管理
- 播放控制（播放/暂停/停止）
- 进度显示
- 错误处理

## 优势

1. **大幅减少等待时间**
   - 传统方式：需要等待完整音频生成（可能5-10分钟）
   - 流式方式：第一段音频生成后即可开始播放（通常10-30秒）

2. **更好的用户体验**
   - 用户可以立即听到播客内容
   - 实时反馈生成进度
   - 支持暂停、继续等控制

3. **资源利用优化**
   - 音频片段可以边生成边播放边清理
   - 减少内存占用
   - 支持长时间播客生成

## 注意事项

1. **音频格式**
   - 采样率：24000Hz
   - 声道：单声道
   - 格式：WAV（PCM编码）
   - 每个片段独立编码，需要前端拼接播放

2. **网络要求**
   - 需要稳定的网络连接
   - 建议使用HTTPS
   - 支持断线重连（需要前端实现）

3. **浏览器兼容性**
   - 需要支持 Fetch API 和 Web Audio API
   - 现代浏览器（Chrome、Firefox、Safari、Edge）均支持

4. **性能考虑**
   - 音频解码需要CPU资源
   - 建议限制并发播放的音频数量
   - 长时间播客建议实现音频缓存机制

## 故障排查

### 问题：音频播放不连续

**解决方案**：
- 确保音频队列管理正确
- 检查AudioContext状态（可能需要用户交互后激活）
- 增加音频缓冲区大小

### 问题：SSE连接断开

**解决方案**：
- 实现自动重连机制
- 检查服务器超时设置
- 使用心跳保持连接

### 问题：音频解码失败

**解决方案**：
- 检查base64编码是否正确
- 验证WAV格式是否有效
- 检查浏览器Web Audio API支持

## 未来改进

1. **支持HLS/HTTP-FLV流式传输**
   - 更标准的流式音频协议
   - 更好的浏览器兼容性

2. **音频压缩**
   - 使用MP3或AAC格式减少传输量
   - 自适应码率

3. **断点续传**
   - 支持从断点继续生成
   - 缓存已生成的音频片段

4. **多客户端同步**
   - 支持多个客户端同步播放
   - 实时协作功能

