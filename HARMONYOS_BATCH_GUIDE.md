# 鸿蒙APP批量生成播客使用指南

## 概述

鸿蒙APP现在支持批量生成播客功能，可以一次提交多个播客生成任务，后端会自动并行处理。

## 配置后端并发数

**重要**：如果要同时处理3个或更多任务，需要调整后端并发数配置。

### 方法1：环境变量配置（推荐）

在启动后端服务前设置环境变量：

```bash
# Windows PowerShell
$env:MAX_CONCURRENT_PODCAST_TASKS = "3"

# Linux/Mac
export MAX_CONCURRENT_PODCAST_TASKS=3

# 然后启动服务
python -m hunyuan_podcast.api_server
```

### 方法2：直接修改代码

编辑 `hunyuan_podcast/api_server.py` 第68行：

```python
MAX_CONCURRENT_PODCAST_TASKS = int(os.getenv("MAX_CONCURRENT_PODCAST_TASKS", "3"))  # 改为3
```

**建议配置**：
- GPU显存 < 8GB：设置为 1-2
- GPU显存 8-16GB：设置为 2-3
- GPU显存 > 16GB：可以设置为 3-4

## 使用方式

### 方式1：批量提交（推荐）

使用新增的 `batchGeneratePodcasts` 方法，一次提交多个任务：

```typescript
import { podcastService, BatchRequest, BatchTaskItem } from 'lib_api';

// 构建批量请求
const batchRequest: BatchRequest = {
  tasks: [
    {
      task_type: 'multi_role',
      task_id: 'task_1', // 可选，不提供则自动生成
      request_data: {
        text: '第一个播客的文本内容...',
        role_voice_urls: {
          '角色A': 'https://cloud-storage-url/voice1.wav',
          '角色B': 'https://cloud-storage-url/voice2.wav'
        },
        category: '科技',
        job_id: 'task_1' // 用于进度查询
      }
    },
    {
      task_type: 'multi_role',
      task_id: 'task_2',
      request_data: {
        text: '第二个播客的文本内容...',
        role_voice_urls: {
          '角色A': 'https://cloud-storage-url/voice1.wav',
          '角色B': 'https://cloud-storage-url/voice2.wav'
        },
        category: '商业',
        job_id: 'task_2'
      }
    },
    {
      task_type: 'deep',
      task_id: 'task_3',
      request_data: {
        topic: '人工智能的未来',
        role_voice_urls: {
          '角色A': 'https://cloud-storage-url/voice1.wav',
          '角色B': 'https://cloud-storage-url/voice2.wav'
        },
        num_characters: 2,
        depth_level: '深度',
        category: '科技',
        job_id: 'task_3'
      }
    }
  ]
};

// 提交批量任务
const response = await podcastService.batchGeneratePodcasts(batchRequest);

if (response.success && response.data) {
  console.log(`已提交 ${response.data.total} 个任务`);
  console.log(`任务ID列表: ${response.data.task_ids.join(', ')}`);
  console.log(`当前队列大小: ${response.data.queue_size}`);
  console.log(`活跃任务数: ${response.data.active_tasks}`);
  
  // 轮询每个任务的状态
  for (const taskId of response.data.task_ids) {
    // 启动进度轮询
    const onProgress = (progress: ProgressStatus) => {
      console.log(`任务 ${taskId}: ${progress.percent}% - ${progress.message}`);
      
      if (progress.done) {
        if (progress.audio_url) {
          console.log(`任务 ${taskId} 完成，音频URL: ${progress.audio_url}`);
        } else if (progress.error) {
          console.error(`任务 ${taskId} 失败: ${progress.error}`);
        }
      }
    };
    
    // 使用原有的进度查询接口
    podcastService.startProgressPolling(taskId, onProgress);
  }
}
```

### 方式2：并行调用单个接口

也可以同时调用3次单个生成接口，后端会自动管理并发：

```typescript
// 同时提交3个任务
const task1 = podcastService.generateMultiRolePodcast({
  text: '第一个播客...',
  role_voice_urls: { '角色A': 'url1', '角色B': 'url2' },
  job_id: 'task_1'
}, (progress) => {
  console.log('任务1进度:', progress.percent);
});

const task2 = podcastService.generateMultiRolePodcast({
  text: '第二个播客...',
  role_voice_urls: { '角色A': 'url1', '角色B': 'url2' },
  job_id: 'task_2'
}, (progress) => {
  console.log('任务2进度:', progress.percent);
});

const task3 = podcastService.generateDeepPodcast({
  topic: '人工智能',
  role_voice_urls: { '角色A': 'url1', '角色B': 'url2' },
  num_characters: 2,
  depth_level: '深度',
  job_id: 'task_3'
}, 'task_3', (progress) => {
  console.log('任务3进度:', progress.percent);
});

// 等待所有任务完成
const results = await Promise.all([task1, task2, task3]);
```

## 查询任务状态

可以使用新增的 `getTaskStatus` 方法查询单个任务状态：

```typescript
const statusResponse = await podcastService.getTaskStatus('task_1');

if (statusResponse.success && statusResponse.data) {
  const task = statusResponse.data;
  console.log(`任务状态: ${task.status}`);
  console.log(`进度: ${task.progress}%`);
  console.log(`消息: ${task.message}`);
  
  if (task.status === 'completed' && task.result?.audio_url) {
    console.log(`音频URL: ${task.result.audio_url}`);
  } else if (task.status === 'failed') {
    console.error(`错误: ${task.error}`);
  }
}
```

## 完整示例

```typescript
import { podcastService, BatchRequest, ProgressStatus } from 'lib_api';

async function generateThreePodcasts() {
  // 1. 构建批量请求
  const batchRequest: BatchRequest = {
    tasks: [
      {
        task_type: 'multi_role',
        task_id: `podcast_${Date.now()}_1`,
        request_data: {
          text: '第一个播客内容...',
          role_voice_urls: {
            '主持人': 'https://cloud-storage-url/host.wav',
            '嘉宾': 'https://cloud-storage-url/guest.wav'
          },
          category: '科技',
          job_id: `podcast_${Date.now()}_1`
        }
      },
      {
        task_type: 'multi_role',
        task_id: `podcast_${Date.now()}_2`,
        request_data: {
          text: '第二个播客内容...',
          role_voice_urls: {
            '主持人': 'https://cloud-storage-url/host.wav',
            '嘉宾': 'https://cloud-storage-url/guest.wav'
          },
          category: '商业',
          job_id: `podcast_${Date.now()}_2`
        }
      },
      {
        task_type: 'deep',
        task_id: `podcast_${Date.now()}_3`,
        request_data: {
          topic: '人工智能的未来',
          role_voice_urls: {
            '角色A': 'https://cloud-storage-url/voice1.wav',
            '角色B': 'https://cloud-storage-url/voice2.wav'
          },
          num_characters: 2,
          depth_level: '深度',
          category: '科技',
          job_id: `podcast_${Date.now()}_3`
        }
      }
    ]
  };

  // 2. 提交批量任务
  const response = await podcastService.batchGeneratePodcasts(batchRequest);
  
  if (!response.success) {
    console.error('批量提交失败:', response.error);
    return;
  }

  if (!response.data) {
    console.error('响应数据为空');
    return;
  }

  console.log(`✅ 已提交 ${response.data.total} 个任务`);
  console.log(`📋 任务ID: ${response.data.task_ids.join(', ')}`);
  console.log(`⏳ 队列大小: ${response.data.queue_size}`);
  console.log(`🔄 活跃任务: ${response.data.active_tasks}`);

  // 3. 为每个任务启动进度轮询
  const progressCallbacks: Map<string, (progress: ProgressStatus) => void> = new Map();
  
  for (const taskId of response.data.task_ids) {
    const onProgress = (progress: ProgressStatus) => {
      console.log(`[${taskId}] ${progress.percent}% - ${progress.message}`);
      
      if (progress.done) {
        if (progress.audio_url) {
          console.log(`✅ [${taskId}] 完成！音频URL: ${progress.audio_url}`);
          // 这里可以下载或播放音频
        } else if (progress.error) {
          console.error(`❌ [${taskId}] 失败: ${progress.error}`);
        }
      }
    };
    
    progressCallbacks.set(taskId, onProgress);
    
    // 启动进度轮询（使用原有的进度查询接口）
    podcastService.startProgressPolling(taskId, onProgress);
  }

  // 4. 可选：定期查询任务状态
  const checkInterval = setInterval(async () => {
    for (const taskId of response.data.task_ids) {
      const statusResponse = await podcastService.getTaskStatus(taskId);
      if (statusResponse.success && statusResponse.data) {
        const task = statusResponse.data;
        if (task.status === 'completed' || task.status === 'failed') {
          console.log(`任务 ${taskId} 已完成，状态: ${task.status}`);
        }
      }
    }
  }, 5000); // 每5秒查询一次

  // 5. 清理（当所有任务完成时）
  // 注意：实际使用时应该在适当的时机清理定时器
  // clearInterval(checkInterval);
}

// 调用
generateThreePodcasts().catch(console.error);
```

## 注意事项

1. **并发限制**：确保后端 `MAX_CONCURRENT_PODCAST_TASKS` 设置为3或更大，才能同时处理3个任务。

2. **任务队列**：如果提交的任务数超过并发限制，多余的任务会进入队列等待处理。

3. **进度查询**：每个任务都有独立的 `job_id`，可以使用 `startProgressPolling` 方法轮询进度。

4. **错误处理**：如果某个任务失败，不会影响其他任务的处理。

5. **资源管理**：批量提交时注意不要一次性提交过多任务，建议每次10-20个。

## 总结

✅ **是的，鸿蒙APP可以同时执行3个播客生成任务！**

只需要：
1. 将后端并发数配置为3（或更大）
2. 使用 `batchGeneratePodcasts` 方法批量提交任务
3. 或者同时调用3次单个生成接口

后端会自动管理任务队列和并发处理。

