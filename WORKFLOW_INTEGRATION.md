# 混元AI播客生成系统 - 工作流集成指南

## 概述

本系统提供REST API接口，可以轻松集成到各种工作流系统中，如：
- FlowSpeech
- ComfyUI
- AutoGPT
- LangChain
- 其他支持HTTP API的工作流系统

## API服务启动

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

启动后访问：
- API文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

## API端点

### 1. 多角色互动播客

**端点**: `POST /api/v1/podcast/multi_role`

**请求体**:
```json
{
  "text": "中科曙光发布640卡超节点，算力密度提升20倍...",
  "role_voices": {
    "角色A": "base64_encoded_audio_data",
    "角色B": "base64_encoded_audio_data"
  },
  "silence_interval": 300
}
```

**响应**:
```json
{
  "success": true,
  "message": "播客生成成功",
  "data": {
    "audio_base64": "base64_encoded_audio",
    "audio_path": "/path/to/output.wav",
    "file_size_mb": 2.5,
    "script": "[角色A]...",
    "roles": ["角色A", "角色B"]
  }
}
```

### 2. 自定义角色播客

**端点**: `POST /api/v1/podcast/character`

**请求体**:
```json
{
  "characters": [
    {
      "name": "托尼老师",
      "identity": "时尚潮人、理发店总监",
      "personality": "自信略带浮夸、热心肠",
      "catchphrase": "喜欢用夸张的赞美和比喻，语速快，充满激情",
      "speaking_style": "清亮有穿透力的声音，语调起伏大",
      "relationship": "与角色B是好友，经常互怼",
      "voice": "base64_encoded_audio_data"
    },
    {
      "name": "程序员阿哲",
      "identity": "资深后端工程师",
      "personality": "逻辑控、内向务实、轻微社恐",
      "catchphrase": "语速平缓，用词精准，喜欢用'从技术实现上讲...'",
      "speaking_style": "低沉温和的声音，语调平稳",
      "relationship": "与角色A是好友，经常被角色A的热情感染",
      "voice": "base64_encoded_audio_data"
    }
  ],
  "topic": "人工智能的发展与未来",
  "silence_interval": 300
}
```

### 3. 主题深度播客

**端点**: `POST /api/v1/podcast/deep`

**请求体**:
```json
{
  "topic": "人工智能对人类社会的影响",
  "role_voices": {
    "角色A": "base64_encoded_audio_data",
    "角色B": "base64_encoded_audio_data"
  },
  "num_characters": 2,
  "depth_level": "深度",
  "silence_interval": 300
}
```

## 工作流插件示例

### Python工作流插件

```python
import requests
import base64
import json

class HunyuanPodcastPlugin:
    """混元AI播客生成工作流插件"""
    
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
    
    def encode_audio_file(self, file_path: str) -> str:
        """将音频文件编码为base64"""
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    
    def generate_multi_role_podcast(
        self,
        text: str,
        role_voice_files: dict,
        silence_interval: int = 300
    ) -> dict:
        """生成多角色互动播客"""
        # 编码音频文件
        role_voices = {
            role: self.encode_audio_file(file_path)
            for role, file_path in role_voice_files.items()
        }
        
        # 发送请求
        response = requests.post(
            f"{self.api_base_url}/api/v1/podcast/multi_role",
            json={
                "text": text,
                "role_voices": role_voices,
                "silence_interval": silence_interval
            }
        )
        
        return response.json()
    
    def generate_character_podcast(
        self,
        characters: list,
        topic: str = None,
        silence_interval: int = 300
    ) -> dict:
        """生成自定义角色播客"""
        # 编码音频文件
        for char in characters:
            char["voice"] = self.encode_audio_file(char["voice_file"])
            del char["voice_file"]
        
        # 发送请求
        response = requests.post(
            f"{self.api_base_url}/api/v1/podcast/character",
            json={
                "characters": characters,
                "topic": topic,
                "silence_interval": silence_interval
            }
        )
        
        return response.json()
    
    def generate_deep_podcast(
        self,
        topic: str,
        role_voice_files: dict,
        num_characters: int = 2,
        depth_level: str = "深度",
        silence_interval: int = 300
    ) -> dict:
        """生成主题深度播客"""
        # 编码音频文件
        role_voices = {
            role: self.encode_audio_file(file_path)
            for role, file_path in role_voice_files.items()
        }
        
        # 发送请求
        response = requests.post(
            f"{self.api_base_url}/api/v1/podcast/deep",
            json={
                "topic": topic,
                "role_voices": role_voices,
                "num_characters": num_characters,
                "depth_level": depth_level,
                "silence_interval": silence_interval
            }
        )
        
        return response.json()
    
    def save_audio_from_response(self, response: dict, output_path: str):
        """从API响应中保存音频文件"""
        if response.get("success") and response.get("data", {}).get("audio_base64"):
            audio_data = base64.b64decode(response["data"]["audio_base64"])
            with open(output_path, "wb") as f:
                f.write(audio_data)
            print(f"✅ 音频已保存到: {output_path}")
        else:
            raise Exception(f"生成失败: {response.get('error', '未知错误')}")


# 使用示例
if __name__ == "__main__":
    plugin = HunyuanPodcastPlugin(api_base_url="http://localhost:8000")
    
    # 示例1：多角色互动播客
    result = plugin.generate_multi_role_podcast(
        text="中科曙光发布640卡超节点，算力密度提升20倍...",
        role_voice_files={
            "角色A": "path/to/voice_a.wav",
            "角色B": "path/to/voice_b.wav"
        }
    )
    
    if result["success"]:
        plugin.save_audio_from_response(result, "output.wav")
        print(f"脚本: {result['data']['script']}")
    
    # 示例2：自定义角色播客
    result = plugin.generate_character_podcast(
        characters=[
            {
                "name": "托尼老师",
                "identity": "时尚潮人",
                "personality": "自信略带浮夸",
                "catchphrase": "喜欢用夸张的赞美",
                "speaking_style": "清亮有穿透力",
                "relationship": "与角色B是好友",
                "voice_file": "path/to/voice_a.wav"
            },
            {
                "name": "程序员阿哲",
                "identity": "资深后端工程师",
                "personality": "逻辑控、内向务实",
                "catchphrase": "从技术实现上讲...",
                "speaking_style": "低沉温和",
                "relationship": "与角色A是好友",
                "voice_file": "path/to/voice_b.wav"
            }
        ],
        topic="人工智能的发展与未来"
    )
    
    # 示例3：主题深度播客
    result = plugin.generate_deep_podcast(
        topic="人工智能对人类社会的影响",
        role_voice_files={
            "角色A": "path/to/voice_a.wav",
            "角色B": "path/to/voice_b.wav"
        },
        depth_level="深度"
    )
```

### Node.js工作流插件

```javascript
const axios = require('axios');
const fs = require('fs');

class HunyuanPodcastPlugin {
    constructor(apiBaseUrl = 'http://localhost:8000') {
        this.apiBaseUrl = apiBaseUrl;
    }
    
    encodeAudioFile(filePath) {
        const fileBuffer = fs.readFileSync(filePath);
        return fileBuffer.toString('base64');
    }
    
    async generateMultiRolePodcast(text, roleVoiceFiles, silenceInterval = 300) {
        const roleVoices = {};
        for (const [role, filePath] of Object.entries(roleVoiceFiles)) {
            roleVoices[role] = this.encodeAudioFile(filePath);
        }
        
        const response = await axios.post(
            `${this.apiBaseUrl}/api/v1/podcast/multi_role`,
            {
                text,
                role_voices: roleVoices,
                silence_interval: silenceInterval
            }
        );
        
        return response.data;
    }
    
    async generateCharacterPodcast(characters, topic = null, silenceInterval = 300) {
        const processedCharacters = characters.map(char => ({
            ...char,
            voice: this.encodeAudioFile(char.voice_file),
            voice_file: undefined
        }));
        
        const response = await axios.post(
            `${this.apiBaseUrl}/api/v1/podcast/character`,
            {
                characters: processedCharacters,
                topic,
                silence_interval: silenceInterval
            }
        );
        
        return response.data;
    }
    
    async generateDeepPodcast(topic, roleVoiceFiles, numCharacters = 2, depthLevel = '深度', silenceInterval = 300) {
        const roleVoices = {};
        for (const [role, filePath] of Object.entries(roleVoiceFiles)) {
            roleVoices[role] = this.encodeAudioFile(filePath);
        }
        
        const response = await axios.post(
            `${this.apiBaseUrl}/api/v1/podcast/deep`,
            {
                topic,
                role_voices: roleVoices,
                num_characters: numCharacters,
                depth_level: depthLevel,
                silence_interval: silenceInterval
            }
        );
        
        return response.data;
    }
    
    saveAudioFromResponse(response, outputPath) {
        if (response.success && response.data.audio_base64) {
            const audioBuffer = Buffer.from(response.data.audio_base64, 'base64');
            fs.writeFileSync(outputPath, audioBuffer);
            console.log(`✅ 音频已保存到: ${outputPath}`);
        } else {
            throw new Error(`生成失败: ${response.error || '未知错误'}`);
        }
    }
}

// 使用示例
(async () => {
    const plugin = new HunyuanPodcastPlugin('http://localhost:8000');
    
    // 生成多角色互动播客
    const result = await plugin.generateMultiRolePodcast(
        '中科曙光发布640卡超节点，算力密度提升20倍...',
        {
            '角色A': 'path/to/voice_a.wav',
            '角色B': 'path/to/voice_b.wav'
        }
    );
    
    if (result.success) {
        plugin.saveAudioFromResponse(result, 'output.wav');
        console.log('脚本:', result.data.script);
    }
})();
```

## FlowSpeech集成示例

### 1. 创建工作流节点

```python
# flowspeech_plugin.py
from flowspeech import Node, Input, Output
import requests
import base64

class HunyuanPodcastNode(Node):
    """混元AI播客生成节点"""
    
    def __init__(self):
        super().__init__(
            name="混元AI播客生成",
            inputs=[
                Input(name="text", type=str, description="播客文本"),
                Input(name="role_voices", type=dict, description="角色音色文件路径字典"),
                Input(name="api_url", type=str, default="http://localhost:8000", description="API服务地址")
            ],
            outputs=[
                Output(name="audio_path", type=str, description="生成的音频文件路径"),
                Output(name="script", type=str, description="生成的脚本")
            ]
        )
    
    def execute(self, text, role_voices, api_url):
        # 编码音频文件
        encoded_voices = {}
        for role, file_path in role_voices.items():
            with open(file_path, "rb") as f:
                encoded_voices[role] = base64.b64encode(f.read()).decode("utf-8")
        
        # 调用API
        response = requests.post(
            f"{api_url}/api/v1/podcast/multi_role",
            json={
                "text": text,
                "role_voices": encoded_voices,
                "silence_interval": 300
            }
        )
        
        result = response.json()
        
        if result["success"]:
            # 保存音频文件
            audio_data = base64.b64decode(result["data"]["audio_base64"])
            output_path = f"output_{int(time.time())}.wav"
            with open(output_path, "wb") as f:
                f.write(audio_data)
            
            return {
                "audio_path": output_path,
                "script": result["data"]["script"]
            }
        else:
            raise Exception(f"生成失败: {result.get('error', '未知错误')}")
```

### 2. 在工作流中使用

```python
from flowspeech import Workflow
from flowspeech_plugin import HunyuanPodcastNode

# 创建工作流
workflow = Workflow()

# 添加节点
text_input = workflow.add_node("TextInput", text="中科曙光发布640卡超节点...")
podcast_node = workflow.add_node(HunyuanPodcastNode())
audio_output = workflow.add_node("AudioOutput")

# 连接节点
workflow.connect(text_input, "text", podcast_node, "text")
workflow.connect(podcast_node, "audio_path", audio_output, "file_path")

# 运行工作流
workflow.run()
```

## ComfyUI集成

### 1. 创建自定义节点

```python
# ComfyUI节点文件: nodes/hunyuan_podcast.py
import requests
import base64
import folder_paths

class HunyuanPodcastNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True}),
                "role_a_voice": ("STRING", {"default": ""}),
                "role_b_voice": ("STRING", {"default": ""}),
                "api_url": ("STRING", {"default": "http://localhost:8000"})
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("audio_path", "script")
    FUNCTION = "generate"
    CATEGORY = "混元AI播客"
    
    def generate(self, text, role_a_voice, role_b_voice, api_url):
        # 编码音频文件
        role_voices = {}
        if role_a_voice:
            with open(role_a_voice, "rb") as f:
                role_voices["角色A"] = base64.b64encode(f.read()).decode("utf-8")
        if role_b_voice:
            with open(role_b_voice, "rb") as f:
                role_voices["角色B"] = base64.b64encode(f.read()).decode("utf-8")
        
        # 调用API
        response = requests.post(
            f"{api_url}/api/v1/podcast/multi_role",
            json={
                "text": text,
                "role_voices": role_voices,
                "silence_interval": 300
            }
        )
        
        result = response.json()
        
        if result["success"]:
            # 保存音频文件
            audio_data = base64.b64decode(result["data"]["audio_base64"])
            output_path = os.path.join(folder_paths.get_output_directory(), f"podcast_{int(time.time())}.wav")
            with open(output_path, "wb") as f:
                f.write(audio_data)
            
            return (output_path, result["data"]["script"])
        else:
            raise Exception(f"生成失败: {result.get('error', '未知错误')}")
```

## 错误处理

所有API端点都会返回统一的响应格式：

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

## 性能优化建议

1. **并发处理**: API服务支持并发请求，可以同时处理多个播客生成任务
2. **缓存机制**: 对于相同的输入，可以考虑缓存生成的音频文件
3. **异步处理**: 对于长时间运行的任务，可以考虑实现异步处理机制
4. **资源管理**: 注意管理TTS模型的加载和卸载，避免内存泄漏

## 安全建议

1. **API密钥**: 在生产环境中，建议添加API密钥认证
2. **文件大小限制**: 限制上传的音频文件大小
3. **请求频率限制**: 实现请求频率限制，防止滥用
4. **输入验证**: 验证所有输入参数，防止恶意输入

## 故障排查

1. **检查API服务**: 访问 `http://localhost:8000/health` 确认服务正常运行
2. **查看日志**: 检查API服务的日志输出，了解错误详情
3. **测试端点**: 使用 `/docs` 页面的交互式API文档进行测试
4. **检查依赖**: 确保所有依赖已正确安装

## 更多信息

- API文档: http://localhost:8000/docs
- 项目仓库: [GitHub链接]
- 问题反馈: [Issues链接]



























