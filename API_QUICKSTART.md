# 混元AI播客生成API - 快速开始

## 安装依赖

```bash
pip install fastapi uvicorn[standard] python-multipart
```

或使用 uv：

```bash
uv pip install fastapi uvicorn[standard] python-multipart
```

## 启动API服务

### 方式1：使用启动脚本（推荐）

```bash
python run_api_server.py --host 0.0.0.0 --port 8000
```

### 方式2：直接运行模块

```bash
python -m hunyuan_podcast.api_server --host 0.0.0.0 --port 8000
```

### 方式3：使用uvicorn

```bash
uvicorn hunyuan_podcast.api_server:app --host 0.0.0.0 --port 8000
```

## 访问API文档

启动服务后，访问以下地址：

- **API文档（Swagger）**: http://localhost:8000/docs
- **API文档（ReDoc）**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/health

## 快速测试

### 使用curl测试

```bash
# 健康检查
curl http://localhost:8000/health

# 获取API信息
curl http://localhost:8000/
```

### 使用Python测试

```python
import requests
import base64

# 健康检查
response = requests.get("http://localhost:8000/health")
print(response.json())

# 读取音频文件并编码
with open("path/to/voice.wav", "rb") as f:
    audio_base64 = base64.b64encode(f.read()).decode("utf-8")

# 生成多角色播客
response = requests.post(
    "http://localhost:8000/api/v1/podcast/multi_role",
    json={
        "text": "中科曙光发布640卡超节点，算力密度提升20倍...",
        "role_voices": {
            "角色A": audio_base64,
            "角色B": audio_base64
        },
        "silence_interval": 300
    }
)

result = response.json()
if result["success"]:
    # 保存音频文件
    audio_data = base64.b64decode(result["data"]["audio_base64"])
    with open("output.wav", "wb") as f:
        f.write(audio_data)
    print("✅ 播客生成成功！")
else:
    print(f"❌ 生成失败: {result.get('error')}")
```

### 使用工作流插件

```python
from workflow_plugin import HunyuanPodcastPlugin

# 创建插件实例
plugin = HunyuanPodcastPlugin(api_base_url="http://localhost:8000")

# 生成多角色播客
result = plugin.generate_multi_role_podcast(
    text="中科曙光发布640卡超节点，算力密度提升20倍...",
    role_voice_files={
        "角色A": "path/to/voice_a.wav",
        "角色B": "path/to/voice_b.wav"
    },
    output_path="output.wav"
)

if result["success"]:
    print(f"✅ 生成成功！音频文件: {result['data']['audio_path']}")
    print(f"脚本: {result['data']['script']}")
else:
    print(f"❌ 生成失败: {result.get('error')}")
```

## API端点说明

### 1. 多角色互动播客

**端点**: `POST /api/v1/podcast/multi_role`

**功能**: 将文本素材转化为多角色自然互动的播客音频

**请求体**:
```json
{
  "text": "播客文本（支持角色标记或普通文本）",
  "role_voices": {
    "角色A": "base64编码的音频数据",
    "角色B": "base64编码的音频数据"
  },
  "silence_interval": 300
}
```

### 2. 自定义角色播客

**端点**: `POST /api/v1/podcast/character`

**功能**: 根据用户自定义的角色人设和音色生成契合风格的播客音频

**请求体**:
```json
{
  "characters": [
    {
      "name": "角色名称",
      "identity": "身份/职业",
      "personality": "核心性格",
      "catchphrase": "口头禅/说话习惯",
      "speaking_style": "说话风格",
      "relationship": "与其他角色的关系",
      "voice": "base64编码的音频数据"
    }
  ],
  "topic": "播客主题（可选）",
  "silence_interval": 300
}
```

### 3. 主题深度播客

**端点**: `POST /api/v1/podcast/deep`

**功能**: 基于指定主题生成有深度、引发思考的播客音频

**请求体**:
```json
{
  "topic": "播客主题",
  "role_voices": {
    "角色A": "base64编码的音频数据",
    "角色B": "base64编码的音频数据"
  },
  "num_characters": 2,
  "depth_level": "深度",
  "silence_interval": 300
}
```

## 响应格式

所有API端点都返回统一的响应格式：

```json
{
  "success": true,
  "message": "播客生成成功",
  "data": {
    "audio_base64": "base64编码的音频数据",
    "audio_path": "/path/to/output.wav",
    "file_size_mb": 2.5,
    "script": "生成的脚本内容",
    ...
  }
}
```

如果失败：

```json
{
  "success": false,
  "message": "播客生成失败",
  "error": "错误详细信息",
  "data": {
    "traceback": "错误堆栈信息（开发模式）"
  }
}
```

## 错误处理

所有API端点都包含错误处理：

1. **400 Bad Request**: 请求参数错误
2. **404 Not Found**: 资源不存在
3. **500 Internal Server Error**: 服务器内部错误

## 性能优化

1. **并发处理**: API服务支持并发请求
2. **超时设置**: 默认超时时间为5分钟（300秒）
3. **资源管理**: 自动清理临时文件

## 安全建议

1. **生产环境**: 建议添加API密钥认证
2. **文件大小**: 限制上传的音频文件大小
3. **请求频率**: 实现请求频率限制
4. **输入验证**: 验证所有输入参数

## 更多信息

- 详细文档: [WORKFLOW_INTEGRATION.md](WORKFLOW_INTEGRATION.md)
- API文档: http://localhost:8000/docs
- 项目仓库: [GitHub链接]


















