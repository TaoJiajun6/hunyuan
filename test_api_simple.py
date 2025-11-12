#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单测试混元大模型API
使用 requests 库直接测试，不依赖项目其他模块
"""
import requests
import json
import os

# API配置
API_BASE = "https://api.siliconflow.cn/v1"
API_KEY = "sk-tpoapasxdwjyexqfagbiigtvwsoydwravbptrmrrmwjfdwbh"
MODEL = "tencent/Hunyuan-A13B-Instruct"

print("=" * 60)
print("混元大模型API测试")
print("=" * 60)
print(f"\nAPI配置：")
print(f"  URL: {API_BASE}/chat/completions")
print(f"  模型: {MODEL}")
print(f"  API Key: {API_KEY[:20]}...{API_KEY[-10:]}")

# 准备请求
url = f"{API_BASE}/chat/completions"
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# 测试消息
messages = [
    {
        "role": "user",
        "content": "你好，请简单介绍一下你自己。"
    }
]

payload = {
    "model": MODEL,
    "messages": messages,
    "temperature": 0.7,
    "max_tokens": 100
}

print("\n" + "-" * 60)
print("发送请求...")
print("-" * 60)
print(f"请求URL: {url}")
print(f"请求体: {json.dumps(payload, ensure_ascii=False, indent=2)}")

try:
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    
    print(f"\n响应状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("\n✅ API调用成功！")
        print("\n响应内容:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        if 'choices' in result and len(result['choices']) > 0:
            content = result['choices'][0]['message']['content']
            print(f"\n📝 模型回复：")
            print(f"  {content}")
            
            if 'usage' in result:
                usage = result['usage']
                print(f"\n📊 Token使用：")
                print(f"  输入: {usage.get('prompt_tokens', 'N/A')}")
                print(f"  输出: {usage.get('completion_tokens', 'N/A')}")
                print(f"  总计: {usage.get('total_tokens', 'N/A')}")
    else:
        print(f"\n❌ API调用失败！")
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
        
except requests.exceptions.RequestException as e:
    print(f"\n❌ 请求异常: {str(e)}")
    print("\n💡 可能的原因：")
    print("  1. 网络连接问题")
    print("  2. API服务暂时不可用")
    print("  3. API密钥无效")
except Exception as e:
    print(f"\n❌ 错误: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)


















