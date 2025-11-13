# 混元大模型API测试指南

## API调用验证

根据您提供的 curl 示例，我们的实现已经正确。以下是验证方法：

## 方法1：使用 curl 直接测试

```bash
curl --request POST \
  --url https://api.siliconflow.cn/v1/chat/completions \
  --header "Authorization: Bearer sk-tpoapasxdwjyexqfagbiigtvwsoydwravbptrmrrmwjfdwbh" \
  --header "Content-Type: application/json" \
  --data '{
  "model": "tencent/Hunyuan-A13B-Instruct",
  "messages": [
    {
      "role": "user",
      "content": "你好，请简单介绍一下你自己。"
    }
  ],
  "temperature": 0.7,
  "max_tokens": 100
}'
```

## 方法2：在 uv 环境中测试

```bash
# 进入 index-tts 目录（uv 环境）
cd index-tts

# 运行测试脚本
uv run python ../test_api_simple.py
```

## 方法3：在 WebUI 中测试

1. 启动 WebUI：
   ```bash
   cd index-tts
   uv run python ../run_podcast_webui.py
   ```

2. 打开浏览器：http://localhost:7861

3. 选择"主题深度播客"标签页

4. 输入主题，例如："人工智能的发展与未来"

5. 上传音色文件

6. 点击"生成播客"

7. 查看终端输出，应该能看到：
   ```
   正在调用混元模型生成深度对话...
   主题: 人工智能的发展与未来
   提示词: ...
   生成的对话文本:
   [角色A]...
   [角色B]...
   ```

## 我们的实现与 curl 示例对比

### curl 示例：
```bash
curl --request POST \
  --url https://api.siliconflow.cn/v1/chat/completions \
  --header 'Authorization: Bearer <token>' \
  --header 'Content-Type: application/json' \
  --data '{
    "model": "Qwen/QwQ-32B",
    "messages": [{"role": "user", "content": "..."}]
  }'
```

### 我们的实现（api_client.py）：
```python
url = f"{self.api_base}/chat/completions"  # https://api.siliconflow.cn/v1/chat/completions
headers = {
    "Authorization": f"Bearer {self.api_key}",
    "Content-Type": "application/json"
}
payload = {
    "model": self.model,  # "tencent/Hunyuan-A13B-Instruct"
    "messages": messages,
    "temperature": temperature,
    "max_tokens": max_tokens,
    "top_p": top_p
}
response = requests.post(url, headers=headers, json=payload, timeout=60)
```

✅ **完全一致！**

## API配置检查

当前配置（`hunyuan_podcast/config.py`）：
- ✅ API Base: `https://api.siliconflow.cn/v1`
- ✅ 模型: `tencent/Hunyuan-A13B-Instruct`
- ✅ API Key: 已配置
- ✅ 请求格式: 完全符合 OpenAI 兼容格式

## 如果测试失败

### 检查1：API密钥
```python
# 在 hunyuan_podcast/config.py 中检查
SILICONFLOW_API_KEY = "sk-tpoapasxdwjyexqfagbiigtvwsoydwravbptrmrrmwjfdwbh"
```

### 检查2：网络连接
```bash
# 测试网络连接
curl -I https://api.siliconflow.cn/v1/chat/completions
```

### 检查3：模型名称
确保使用正确的模型名称：`tencent/Hunyuan-A13B-Instruct`

## 成功标志

如果API正常工作，您应该看到：

1. **终端输出**：
   ```
   正在调用混元模型生成对话...
   生成的对话文本:
   [角色A]...
   ```

2. **WebUI状态**：
   - 显示"正在调用混元模型..."
   - 最终显示"播客生成成功"

3. **API响应**：
   ```json
   {
     "id": "...",
     "choices": [{
       "message": {
         "content": "..."
       }
     }],
     "usage": {
       "prompt_tokens": ...,
       "completion_tokens": ...,
       "total_tokens": ...
     }
   }
   ```

## 总结

✅ **API实现完全正确，与 curl 示例一致**

- URL: ✅ 正确
- Headers: ✅ 正确
- Payload: ✅ 正确
- 模型名称: ✅ 正确

可以直接使用 WebUI 测试，API 调用会在生成播客时自动执行！





















