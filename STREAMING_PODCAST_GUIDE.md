# 流式播客生成功能说明

## 功能概述

实现了边生成边播放的流式播客生成功能，可以大幅减少用户等待时间。当第一段音频生成完成后，用户就可以开始播放，而不需要等待整个播客生成完成。

## 实现原理

1. **流式音频生成**：修改了 `soulx_tts.py`，添加了 `infer_multi_speaker_streaming` 方法，使用生成器逐段返回音频片段
2. **流式处理**：在 `podcast_generator.py` 中添加了 `generate_from_text_streaming` 方法，支持流式处理音频片段
3. **实时传输**：在 API 服务器中添加了 `/api/v1/podcast/deep/stream` 端点，使用 Server-Sent Events (SSE) 实时推送音频片段

## API 端点

### POST `/api/v1/podcast/deep/stream`

流式生成主题深度播客，支持边生成边播放。

### POST `/api/v1/podcast/multi_role/stream`

流式生成多角色互动播客，支持边生成边播放。

### POST `/api/v1/podcast/character/stream`

流式生成自定义角色播客，支持边生成边播放。

#### 请求参数

**深度播客 (`/api/v1/podcast/deep/stream`):**
- `topic`: 播客主题（必需）
- `role_voice_urls`: 角色音色映射（必需）
- `num_characters`: 角色数量（可选，默认2）
- `depth_level`: 深度级别（可选，默认"深度"）
- `silence_interval`: 静音间隔（可选，默认800ms）
- `category`: 播客分类（可选）
- `background_volume`: 背景音乐音量（可选，默认0.3）
- `job_id`: 任务ID（可选）

**多角色播客 (`/api/v1/podcast/multi_role/stream`):**
- `text`: 播客文本（可选，如果使用text_file_url或input_url，此字段可为空）
- `text_file_url`: 文本文件云存储URL（可选）
- `input_url`: 输入URL（可选）
- `input_type`: 输入类型（可选）
- `role_voice_urls`: 角色音色映射（必需）
- `silence_interval`: 静音间隔（可选，默认800ms）
- `category`: 播客分类（可选）
- `background_volume`: 背景音乐音量（可选，默认0.3）
- `job_id`: 任务ID（可选）

**自定义角色播客 (`/api/v1/podcast/character/stream`):**
- `characters`: 角色列表（必需，至少2个）
- `text`: 文本素材（必需）
- `topic`: 播客主题（可选）
- `silence_interval`: 静音间隔（可选，默认800ms）
- `category`: 播客分类（可选）
- `background_volume`: 背景音乐音量（可选，默认0.3）
- `job_id`: 任务ID（可选）

#### 响应格式

使用 SSE 格式，每行以 `data: ` 开头，JSON 格式的数据。

**事件类型：**

1. **progress** - 进度更新
```json
{
  "type": "progress",
  "status": "generating_audio",
  "percent": 50,
  "message": "已生成 15 个音频片段..."
}
```

2. **audio_segment** - 音频片段
```json
{
  "type": "audio_segment",
  "segment_index": 0,
  "role_name": "角色A",
  "audio_base64": "base64编码的音频数据",
  "is_final": false,
  "sample_rate": 22050
}
```

3. **script** - 生成的脚本
```json
{
  "type": "script",
  "script": "生成的完整脚本内容"
}
```

4. **done** - 生成完成
```json
{
  "type": "done",
  "total_segments": 30
}
```

5. **error** - 错误信息
```json
{
  "type": "error",
  "message": "错误描述"
}
```

## 前端使用示例

### JavaScript (使用 fetch API)

```javascript
async function streamPodcast(requestData) {
    const response = await fetch('/api/v1/podcast/deep/stream', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData)
    });
    
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    const audioQueue = []; // 音频片段队列
    
    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');
        
        for (const line of lines) {
            if (line.startsWith('data: ')) {
                try {
                    const data = JSON.parse(line.slice(6));
                    
                    switch (data.type) {
                        case 'progress':
                            // 更新进度条
                            updateProgressBar(data.percent, data.message);
                            break;
                            
                        case 'audio_segment':
                            // 将音频片段加入播放队列
                            audioQueue.push({
                                base64: data.audio_base64,
                                role: data.role_name,
                                isFinal: data.is_final
                            });
                            
                            // 如果播放器空闲，开始播放
                            if (audioPlayer.paused) {
                                playNextSegment();
                            }
                            break;
                            
                        case 'script':
                            // 显示脚本
                            displayScript(data.script);
                            break;
                            
                        case 'done':
                            // 生成完成
                            console.log(`生成完成，共 ${data.total_segments} 个片段`);
                            break;
                            
                        case 'error':
                            // 错误处理
                            console.error('生成错误:', data.message);
                            break;
                    }
                } catch (e) {
                    console.error('解析数据失败:', e);
                }
            }
        }
    }
}

// 播放音频片段
function playNextSegment() {
    if (audioQueue.length === 0) return;
    
    const segment = audioQueue.shift();
    const audioData = base64ToArrayBuffer(segment.base64);
    
    // 创建音频对象并播放
    const audio = new Audio();
    audio.src = URL.createObjectURL(new Blob([audioData], { type: 'audio/wav' }));
    
    audio.onended = () => {
        // 播放下一段
        if (audioQueue.length > 0) {
            playNextSegment();
        }
    };
    
    audio.play();
}

// Base64 转 ArrayBuffer
function base64ToArrayBuffer(base64) {
    const binaryString = atob(base64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes.buffer;
}
```

## 优势

1. **减少等待时间**：用户可以在第一段音频生成后立即开始播放，无需等待整个播客生成完成
2. **更好的用户体验**：实时反馈生成进度，用户可以随时了解生成状态
3. **资源利用**：可以边生成边播放，充分利用时间

## 注意事项

1. **背景音乐**：流式模式下已支持背景音乐混合，包括：
   - Intro阶段（5秒）：背景音乐淡入，正常音量
   - 对话阶段：背景音乐压低（ducking效果，降低到15%音量）
   - Outro阶段（5秒）：背景音乐淡出
2. **网络要求**：需要稳定的网络连接，确保音频片段能够及时传输
3. **播放器实现**：前端需要实现音频片段队列管理，确保连续播放

## 技术细节

- 音频采样率：22050 Hz
- 音频格式：WAV
- 传输格式：Base64 编码的 WAV 数据
- 传输协议：Server-Sent Events (SSE)
- 编码方式：JSON

## 鸿蒙前端适配

由于鸿蒙的 `http` 模块不支持 Server-Sent Events (SSE) 流式读取，需要特殊处理。详细适配指南请参考：[HARMONYOS_STREAMING_GUIDE.md](./HARMONYOS_STREAMING_GUIDE.md)

### 主要适配点

1. **流式数据读取**：使用 HTTP 请求的完整响应，然后解析 SSE 格式数据
2. **音频片段播放**：实现音频片段队列管理，使用 `media.AVPlayer` 连续播放
3. **Base64 转换**：将接收到的 Base64 音频数据转换为临时文件后播放

### 关键代码示例

```typescript
// 在 PodcastService 中添加流式生成方法
async generateDeepPodcastStreaming(
  request: DeepPodcastRequest,
  onProgress?: (progress: ProgressStatus) => void,
  onAudioSegment?: (segment: AudioSegment) => void,
  onScript?: (script: string) => void
): Promise<ApiResponse<void>>

// 在页面中实现音频片段队列播放
private audioSegmentQueue: AudioSegment[] = [];
private async playNextAudioSegment(): Promise<void>
```

## 后续优化方向

1. ✅ 支持背景音乐的流式混合（已实现）
2. 优化音频片段大小，减少传输延迟
3. 支持音频压缩（如 MP3）以减少传输数据量
4. 添加音频缓冲机制，确保播放流畅
5. 完善鸿蒙前端的流式读取支持（如果鸿蒙API更新）

