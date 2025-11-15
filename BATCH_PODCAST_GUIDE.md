# 批量播客生成使用指南

## 概述

后端现在支持批量生成播客，并且可以并行处理多个任务。系统会自动管理任务队列，控制并发数量，避免GPU资源竞争。

## 功能特性

1. **批量提交**：一次可以提交最多50个播客生成任务
2. **并行处理**：支持同时处理多个任务（默认2个，可配置）
3. **任务队列**：自动管理任务队列，按顺序处理
4. **进度跟踪**：每个任务都有独立的进度跟踪
5. **状态查询**：可以查询单个任务或列出所有任务

## 配置

### 并发控制

通过环境变量 `MAX_CONCURRENT_PODCAST_TASKS` 控制最大并发任务数：

```bash
# 默认值为2，可以根据GPU显存调整
export MAX_CONCURRENT_PODCAST_TASKS=2
```

**建议值**：
- GPU显存 < 8GB：设置为 1
- GPU显存 8-16GB：设置为 2
- GPU显存 > 16GB：可以设置为 3-4

## API接口

### 1. 批量生成播客

**接口**：`POST /api/v1/podcast/batch`

**请求体**：
```json
{
  "tasks": [
    {
      "task_type": "multi_role",
      "task_id": "可选的任务ID，不提供则自动生成",
      "request_data": {
        "text": "播客文本内容",
        "role_voice_urls": {
          "角色A": "https://cloud-storage-url/voice1.wav",
          "角色B": "https://cloud-storage-url/voice2.wav"
        },
        "silence_interval": 800,
        "category": "科技",
        "background_volume": 0.3
      }
    },
    {
      "task_type": "deep",
      "request_data": {
        "topic": "人工智能的未来",
        "role_voice_urls": {
          "角色A": "https://cloud-storage-url/voice1.wav",
          "角色B": "https://cloud-storage-url/voice2.wav"
        },
        "num_characters": 2,
        "depth_level": "深度",
        "category": "科技"
      }
    }
  ]
}
```

**响应**：
```json
{
  "success": true,
  "message": "批量任务已提交，共 2 个任务",
  "data": {
    "task_ids": ["task_id_1", "task_id_2"],
    "total": 2,
    "queue_size": 0,
    "active_tasks": 2
  }
}
```

### 2. 查询任务状态

**接口**：`GET /api/v1/podcast/task/{task_id}`

**响应**：
```json
{
  "success": true,
  "message": "任务信息",
  "data": {
    "task_id": "task_id_1",
    "task_type": "multi_role",
    "status": "processing",
    "progress": 60,
    "message": "正在生成播客音频...",
    "created_at": 1234567890.0,
    "started_at": 1234567891.0,
    "completed_at": null,
    "result": {
      "file_size_mb": 5.2,
      "output_path": "/path/to/output.wav",
      "audio_url": "https://cloud-storage-url/output.wav"
    }
  }
}
```

**任务状态**：
- `pending`：等待处理
- `processing`：处理中
- `completed`：已完成
- `failed`：失败

### 3. 列出所有任务

**接口**：`GET /api/v1/podcast/tasks?status=processing&limit=20`

**查询参数**：
- `status`：过滤状态（可选，pending/processing/completed/failed）
- `limit`：返回数量限制（默认20）

**响应**：
```json
{
  "success": true,
  "message": "共找到 5 个任务",
  "data": {
    "tasks": [
      {
        "task_id": "task_id_1",
        "task_type": "multi_role",
        "status": "processing",
        "progress": 60,
        "message": "正在生成播客音频...",
        "created_at": 1234567890.0
      }
    ],
    "total": 10,
    "active": 2,
    "queue_size": 3
  }
}
```

### 4. 查询任务进度（兼容原有接口）

**接口**：`GET /api/v1/podcast/progress/{job_id}`

这个接口与批量生成接口兼容，可以使用相同的 `job_id` 查询进度。

## 使用示例

### Python示例

```python
import requests
import time

# 批量提交任务
batch_request = {
    "tasks": [
        {
            "task_type": "multi_role",
            "request_data": {
                "text": "这是第一个播客的文本内容...",
                "role_voice_urls": {
                    "角色A": "https://cloud-storage-url/voice1.wav",
                    "角色B": "https://cloud-storage-url/voice2.wav"
                },
                "category": "科技"
            }
        },
        {
            "task_type": "multi_role",
            "request_data": {
                "text": "这是第二个播客的文本内容...",
                "role_voice_urls": {
                    "角色A": "https://cloud-storage-url/voice1.wav",
                    "角色B": "https://cloud-storage-url/voice2.wav"
                },
                "category": "商业"
            }
        }
    ]
}

response = requests.post("http://localhost:8000/api/v1/podcast/batch", json=batch_request)
result = response.json()

if result["success"]:
    task_ids = result["data"]["task_ids"]
    print(f"已提交 {len(task_ids)} 个任务")
    
    # 轮询任务状态
    for task_id in task_ids:
        while True:
            status_response = requests.get(f"http://localhost:8000/api/v1/podcast/task/{task_id}")
            status = status_response.json()
            
            task_data = status["data"]
            print(f"任务 {task_id}: {task_data['status']} - {task_data['progress']}%")
            
            if task_data["status"] in ["completed", "failed"]:
                break
            
            time.sleep(2)  # 每2秒查询一次
```

### cURL示例

```bash
# 批量提交任务
curl -X POST "http://localhost:8000/api/v1/podcast/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "tasks": [
      {
        "task_type": "multi_role",
        "request_data": {
          "text": "播客文本内容",
          "role_voice_urls": {
            "角色A": "https://cloud-storage-url/voice1.wav",
            "角色B": "https://cloud-storage-url/voice2.wav"
          },
          "category": "科技"
        }
      }
    ]
  }'

# 查询任务状态
curl "http://localhost:8000/api/v1/podcast/task/{task_id}"

# 列出所有任务
curl "http://localhost:8000/api/v1/podcast/tasks?status=processing&limit=10"
```

## 注意事项

1. **并发限制**：系统默认最多同时处理2个任务，避免GPU内存溢出。可以根据实际情况调整 `MAX_CONCURRENT_PODCAST_TASKS` 环境变量。

2. **任务队列**：如果提交的任务数超过并发限制，多余的任务会进入队列等待处理。

3. **任务ID**：如果不提供 `task_id`，系统会自动生成UUID。建议在批量提交时提供有意义的任务ID，方便后续查询和管理。

4. **进度查询**：可以使用原有的进度查询接口 `/api/v1/podcast/progress/{job_id}`，也可以使用新的任务状态接口 `/api/v1/podcast/task/{task_id}`。

5. **错误处理**：如果某个任务失败，不会影响其他任务的处理。可以通过任务状态接口查询失败原因。

6. **资源管理**：系统会自动管理GPU资源，避免同时运行过多任务导致显存不足。

## 性能优化建议

1. **批量大小**：建议每次批量提交10-20个任务，避免队列过长。

2. **并发数调整**：根据GPU显存大小调整并发数，确保不会出现OOM错误。

3. **任务优先级**：目前系统按FIFO（先进先出）顺序处理任务。如果需要优先级功能，可以后续扩展。

4. **监控**：定期查询任务列表，清理已完成或失败的任务，避免内存占用过多。

## 故障排查

1. **任务一直处于pending状态**：
   - 检查是否有其他任务正在处理
   - 检查并发限制是否设置过小
   - 查看日志确认工作线程是否正常启动

2. **任务失败**：
   - 查询任务状态获取错误信息
   - 检查输入参数是否正确
   - 检查音色文件URL是否可访问

3. **GPU内存不足**：
   - 降低 `MAX_CONCURRENT_PODCAST_TASKS` 的值
   - 检查是否有其他进程占用GPU

