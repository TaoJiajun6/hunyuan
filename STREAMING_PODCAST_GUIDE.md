# 流式播客生成使用指南

## 概述

本项目已实现流式播客生成功能，支持边生成边播放，大幅减少等待时间。

## 技术实现

### 前端
- **StreamingTTSPlayer**: 使用 MediaSource Extensions (MSE) 技术实现流式音频播放
- 支持接收 Base64 编码的音频块并实时播放
- 兼容所有现代浏览器（Chrome / Edge / Firefox / Safari）

### 后端
- 通过 Server-Sent Events (SSE) 流式发送音频块
- 在音频片段生成后立即编码并发送
- 支持 WAV 格式音频块（可扩展为 MP3）

## 使用方法

### 前端集成示例

```typescript
import { StreamingTTSPlayer } from './utils/StreamingTTSPlayer';
import { podcastService } from './services/PodcastService';

// 创建流式播放器
const player = new StreamingTTSPlayer({
  onEvent: (event, data) => {
    console.log('播放器事件:', event, data);
  }
});

// 启动流式进度监听
const stopStreaming = podcastService.startStreamingProgress(
  jobId,
  (progress) => {
    console.log('进度更新:', progress);
  },
  (chunk) => {
    // 接收音频块并播放
    player.receiveBase64(chunk.audio_base64);
    
    // 如果是最后一个块，结束流
    if (chunk.is_last) {
      player.endOfStream();
    }
  }
);

// 生成播客
const response = await podcastService.generateDeepPodcast({
  topic: 'AI的未来',
  role_voices: { /* ... */ },
  job_id: jobId
});
```

## 注意事项

1. **音频格式**: 当前实现使用 WAV 格式，如需 MP3 格式需要：
   - 安装 `pydub` 库：`pip install pydub`
   - 修改后端编码函数使用 MP3 编码

2. **浏览器兼容性**: MediaSource Extensions 需要现代浏览器支持

3. **网络要求**: SSE 连接需要稳定的网络环境

## 后续优化

1. 支持 MP3 格式（更小的文件大小）
2. 优化音频块大小（平衡延迟和网络开销）
3. 添加音频缓冲管理
4. 支持暂停/恢复播放

## 文件说明

- `web/src/utils/StreamingTTSPlayer.ts`: 流式音频播放器
- `hunyuan_podcast/soulx_tts.py`: TTS 生成逻辑（已支持回调）
- `hunyuan_podcast/api_server.py`: API 服务器（已添加音频块发送功能）








