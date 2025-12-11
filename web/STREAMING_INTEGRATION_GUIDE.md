# 流式播客播放前端集成指南

## 概述

本指南展示如何在前端页面中集成流式播客播放功能，实现边生成边播放的效果。

## 核心组件

### 1. StreamingTTSPlayer

位置：`web/src/utils/StreamingTTSPlayer.ts`

使用 MediaSource Extensions (MSE) 技术实现流式音频播放。

### 2. PodcastService.startStreamingProgress

位置：`web/src/services/PodcastService.ts`

通过 Server-Sent Events (SSE) 接收进度更新和音频块。

## 集成步骤

### 步骤 1: 导入必要的模块

```typescript
import { StreamingTTSPlayer } from '../../utils/StreamingTTSPlayer';
import { podcastService } from '../../services/PodcastService';
```

### 步骤 2: 创建状态和引用

```typescript
const [isStreaming, setIsStreaming] = useState(false);
const [isPlaying, setIsPlaying] = useState(false);
const playerRef = useRef<StreamingTTSPlayer | null>(null);
const stopStreamingRef = useRef<(() => void) | null>(null);
```

### 步骤 3: 创建播放器实例

```typescript
const player = new StreamingTTSPlayer({
  onEvent: (event, data) => {
    if (event === 'play') {
      setIsPlaying(true);
    } else if (event === 'pause') {
      setIsPlaying(false);
    } else if (event === 'timeupdate') {
      setCurrentTime(data.currentTime);
      setDuration(data.duration);
    } else if (event === 'ended') {
      setIsStreaming(false);
    }
  }
});

playerRef.current = player;
```

### 步骤 4: 启动流式进度监听

```typescript
const stopStreaming = podcastService.startStreamingProgress(
  jobId,
  (progress) => {
    // 处理进度更新
    setProgressPercent(progress.percent);
    setProgressMessage(progress.message);
    
    if (progress.done) {
      setIsLoading(false);
    }
  },
  (chunk) => {
    // 处理音频块
    if (playerRef.current) {
      const audioBase64 = chunk.audio_base64.startsWith('data:') 
        ? chunk.audio_base64 
        : `data:audio/wav;base64,${chunk.audio_base64}`;
      
      playerRef.current.receiveBase64(audioBase64, true);
      
      if (chunk.is_last) {
        playerRef.current.endOfStream();
        setIsStreaming(false);
      }
    }
  }
);

stopStreamingRef.current = stopStreaming;
```

### 步骤 5: 清理资源

```typescript
useEffect(() => {
  return () => {
    if (playerRef.current) {
      playerRef.current.destroy();
    }
    if (stopStreamingRef.current) {
      stopStreamingRef.current();
    }
  };
}, []);
```

## 完整示例

参考文件：`web/src/pages/podcast/DeepPageWithStreaming.tsx`

这个文件展示了完整的集成示例，包括：
- 播放器创建和配置
- 流式进度监听
- 音频块接收和处理
- 播放控制（播放/暂停/停止）
- 时间显示
- 资源清理

## 注意事项

### 1. 音频格式

当前实现支持 WAV 格式。如果后端发送的是纯 base64 字符串，需要添加 data URL 前缀：

```typescript
const audioBase64 = chunk.audio_base64.startsWith('data:') 
  ? chunk.audio_base64 
  : `data:audio/wav;base64,${chunk.audio_base64}`;
```

### 2. 浏览器兼容性

MediaSource Extensions 需要现代浏览器支持：
- Chrome 23+
- Edge 13+
- Firefox 42+
- Safari 9.1+

### 3. 错误处理

确保处理以下错误情况：
- 播放器初始化失败
- SSE 连接失败
- 音频块解码失败
- 网络中断

### 4. 资源清理

组件卸载时必须清理：
- 停止播放器
- 关闭 SSE 连接
- 释放 MediaSource 资源

## 播放控制

### 播放/暂停

```typescript
const handleTogglePlay = () => {
  if (playerRef.current) {
    if (isPlaying) {
      playerRef.current.pause();
    } else {
      playerRef.current.play();
    }
  }
};
```

### 停止

```typescript
const handleStop = () => {
  if (playerRef.current) {
    playerRef.current.stop();
    setIsStreaming(false);
  }
  if (stopStreamingRef.current) {
    stopStreamingRef.current();
  }
};
```

## UI 示例

```tsx
{isStreaming && (
  <div className="p-4 bg-primary-50 rounded-lg">
    <div className="flex items-center gap-4">
      <button onClick={handleTogglePlay}>
        {isPlaying ? <Pause /> : <Play />}
      </button>
      <div className="flex-1">
        <div>正在流式播放...</div>
        <div>{formatTime(currentTime)} / {formatTime(duration)}</div>
      </div>
      <button onClick={handleStop}>停止</button>
    </div>
  </div>
)}
```

## 调试技巧

1. **查看控制台日志**：播放器会输出详细的事件日志
2. **检查 SSE 连接**：在浏览器开发者工具的 Network 标签中查看 SSE 连接
3. **验证音频格式**：确保 base64 数据格式正确
4. **测试网络中断**：模拟网络中断情况，确保错误处理正确

## 常见问题

### Q: 音频播放不流畅？
A: 检查音频块大小和网络速度，可能需要调整块大小或添加缓冲。

### Q: 播放器无法初始化？
A: 检查浏览器是否支持 MSE，以及音频格式是否正确。

### Q: SSE 连接失败？
A: 检查后端服务是否正常运行，以及 CORS 配置是否正确。

## 后续优化

1. 支持 MP3 格式（更小的文件大小）
2. 添加音频缓冲管理
3. 支持断点续播
4. 添加播放速度控制
5. 支持音量控制






