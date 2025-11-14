# SSE 实时进度推送指南

## 概述

为了避免轮询请求覆盖日志，我们实现了基于 **Server-Sent Events (SSE)** 的实时进度推送功能。前端可以通过 SSE 连接实时接收进度更新，无需轮询。

## 实现方案

### 1. 后端实现

#### SSE 端点
- **URL**: `/api/v1/podcast/progress/{job_id}/stream`
- **方法**: `GET`
- **响应类型**: `text/event-stream`

#### 功能特点
- ✅ 实时推送进度更新（无需轮询）
- ✅ 自动发送心跳保持连接
- ✅ 任务完成后自动关闭连接
- ✅ 支持多个客户端同时连接（每个 job_id 一个队列）

### 2. 日志过滤

为了避免轮询请求覆盖日志，我们过滤了以下请求的日志：
- `GET /api/v1/podcast/progress/{job_id}` （轮询请求，已过滤）
- `GET /api/v1/podcast/progress/{job_id}/stream` （SSE 请求，保留日志）

## 前端使用示例

### JavaScript (Web)

```javascript
// 创建 SSE 连接
const jobId = "your_job_id";
const eventSource = new EventSource(`/api/v1/podcast/progress/${jobId}/stream`);

// 监听进度更新
eventSource.onmessage = (event) => {
    const progress = JSON.parse(event.data);
    console.log('进度更新:', progress);
    
    // 更新 UI
    updateProgressBar(progress.percent);
    updateStatusMessage(progress.message);
    
    // 检查是否完成
    if (progress.done) {
        if (progress.error) {
            console.error('任务失败:', progress.error);
        } else {
            console.log('任务完成!');
            if (progress.audio_url) {
                console.log('音频URL:', progress.audio_url);
            }
        }
        eventSource.close(); // 关闭连接
    }
};

// 监听错误
eventSource.onerror = (error) => {
    console.error('SSE连接错误:', error);
    eventSource.close();
};

// 手动关闭连接（如果需要）
// eventSource.close();
```

### ArkTS (HarmonyOS)

```typescript
import http from '@ohos.net.http';

class ProgressSSEClient {
    private requestTask: http.HttpRequest | null = null;
    private jobId: string;
    private onProgress: (progress: ProgressData) => void;
    private onError: (error: Error) => void;

    constructor(
        jobId: string,
        onProgress: (progress: ProgressData) => void,
        onError: (error: Error) => void
    ) {
        this.jobId = jobId;
        this.onProgress = onProgress;
        this.onError = onError;
    }

    connect() {
        const url = `http://your-api-server/api/v1/podcast/progress/${this.jobId}/stream`;
        const request = http.createHttp();
        
        request.request(url, {
            method: http.RequestMethod.GET,
            header: {
                'Accept': 'text/event-stream',
                'Cache-Control': 'no-cache'
            },
            readTimeout: 60000,
            connectTimeout: 60000
        }, (err, data) => {
            if (err) {
                this.onError(new Error(err.message || 'SSE连接失败'));
                return;
            }
            
            if (data.responseCode === 200) {
                // 处理 SSE 数据流
                this.processSSEStream(data.result.toString());
            } else {
                this.onError(new Error(`HTTP ${data.responseCode}`));
            }
        });
        
        this.requestTask = request;
    }

    private processSSEStream(stream: string) {
        // 解析 SSE 格式的数据
        const lines = stream.split('\n');
        let currentData = '';
        
        for (const line of lines) {
            if (line.startsWith('data: ')) {
                currentData = line.substring(6); // 移除 "data: " 前缀
            } else if (line === '' && currentData) {
                // 空行表示一个完整的事件
                try {
                    const progress = JSON.parse(currentData) as ProgressData;
                    this.onProgress(progress);
                    
                    // 如果任务完成，关闭连接
                    if (progress.done) {
                        this.close();
                    }
                } catch (e) {
                    console.error('解析进度数据失败:', e);
                }
                currentData = '';
            }
        }
    }

    close() {
        if (this.requestTask) {
            this.requestTask.destroy();
            this.requestTask = null;
        }
    }
}

interface ProgressData {
    job_id: string;
    phase: string;
    percent: number;
    message: string;
    done: boolean;
    error?: string;
    audio_url?: string;
    ts: number;
}

// 使用示例
const client = new ProgressSSEClient(
    jobId,
    (progress) => {
        console.log('进度更新:', progress);
        // 更新 UI
    },
    (error) => {
        console.error('SSE错误:', error);
    }
);

client.connect();
```

## 进度数据结构

```typescript
interface ProgressData {
    job_id: string;        // 任务ID
    phase: string;         // 当前阶段（如：queued, processing_input, generating, completed）
    percent: number;        // 进度百分比 (0-100)
    message: string;       // 进度消息
    done: boolean;         // 是否完成
    error?: string;        // 错误信息（如果有）
    audio_url?: string;    // 音频云存储URL（完成时提供）
    ts: number;            // 时间戳
}
```

## 进度阶段说明

| 阶段 | 百分比 | 说明 |
|------|--------|------|
| `queued` | 1 | 任务已排队 |
| `processing_input` | 3 | 正在处理输入 |
| `downloading_text` | 3 | 正在下载文本文件 |
| `downloading_voices` | 5-20 | 正在下载角色音色文件 |
| `selecting_music` | 22 | 正在选择背景音乐 |
| `generating` | 25-80 | 正在生成语音与合成音频 |
| `saving` | 85 | 保存音频文件 |
| `uploading` | 90-95 | 正在上传到云存储 |
| `completed` | 100 | 生成完成 |
| `failed` | 100 | 生成失败 |

## 兼容性说明

### 保留轮询接口

为了向后兼容，我们保留了原有的轮询接口：
- `GET /api/v1/podcast/progress/{job_id}`

但**不推荐使用**，因为：
1. 会产生大量日志，覆盖重要信息
2. 增加服务器负载
3. 实时性不如 SSE

### 日志过滤

轮询请求的日志已被过滤，不会出现在日志中：
- ✅ 轮询请求：`GET /api/v1/podcast/progress/{job_id}` - **已过滤**
- ✅ SSE 请求：`GET /api/v1/podcast/progress/{job_id}/stream` - **保留日志**

## 优势

1. **实时性更好**：进度更新立即推送，无需等待轮询间隔
2. **减少日志噪音**：轮询请求不再产生日志
3. **降低服务器负载**：无需频繁的 HTTP 请求
4. **更好的用户体验**：进度更新更及时、流畅

## 注意事项

1. **连接超时**：SSE 连接会在 30 秒无更新时发送心跳，保持连接活跃
2. **自动关闭**：任务完成或失败后，连接会自动关闭
3. **错误处理**：前端应监听 `onerror` 事件，处理连接错误
4. **多客户端**：同一个 `job_id` 可以有多个 SSE 连接，每个连接都会收到进度更新

