#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试混元大模型API是否打通
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, '.')

try:
    from hunyuan_podcast.api_client import SiliconFlowClient, get_client
    from hunyuan_podcast.config import SILICONFLOW_API_KEY, SILICONFLOW_API_BASE, SILICONFLOW_MODEL
    
    print("=" * 60)
    print("混元大模型API连接测试")
    print("=" * 60)
    print(f"\nAPI配置：")
    print(f"  API Base: {SILICONFLOW_API_BASE}")
    print(f"  模型名称: {SILICONFLOW_MODEL}")
    print(f"  API Key: {SILICONFLOW_API_KEY[:20]}...{SILICONFLOW_API_KEY[-10:]}")
    
    print("\n" + "-" * 60)
    print("测试1: 创建API客户端")
    print("-" * 60)
    client = get_client()
    print("✅ API客户端创建成功")
    
    print("\n" + "-" * 60)
    print("测试2: 发送简单测试请求")
    print("-" * 60)
    
    test_messages = [
        {"role": "user", "content": "你好，请简单介绍一下你自己。"}
    ]
    
    try:
        print("正在发送请求...")
        response = client.chat_completion(
            messages=test_messages,
            temperature=0.7,
            max_tokens=100,
            top_p=0.9,
            stream=False
        )
        
        print("\n✅ API调用成功！")
        print(f"\n响应结构：")
        print(f"  - 包含 'choices': {'choices' in response}")
        print(f"  - 包含 'model': {'model' in response}")
        print(f"  - 包含 'usage': {'usage' in response}")
        
        if 'choices' in response and len(response['choices']) > 0:
            content = response['choices'][0]['message']['content']
            print(f"\n📝 模型回复：")
            print(f"  {content}")
            
            if 'usage' in response:
                usage = response['usage']
                print(f"\n📊 Token使用情况：")
                print(f"  - 输入tokens: {usage.get('prompt_tokens', 'N/A')}")
                print(f"  - 输出tokens: {usage.get('completion_tokens', 'N/A')}")
                print(f"  - 总计tokens: {usage.get('total_tokens', 'N/A')}")
        else:
            print("\n⚠️  警告：响应格式异常")
            print(f"响应内容: {response}")
            
    except Exception as e:
        print(f"\n❌ API调用失败：{str(e)}")
        import traceback
        traceback.print_exc()
        print("\n💡 可能的原因：")
        print("  1. API密钥无效或过期")
        print("  2. 网络连接问题")
        print("  3. API服务暂时不可用")
        print("  4. 模型名称不正确")
        sys.exit(1)
    
    print("\n" + "-" * 60)
    print("测试3: 使用便捷方法生成文本")
    print("-" * 60)
    
    try:
        result = client.generate_text(
            prompt="用一句话介绍人工智能",
            max_tokens=50
        )
        print(f"✅ 文本生成成功：{result}")
    except Exception as e:
        print(f"❌ 文本生成失败：{str(e)}")
    
    print("\n" + "=" * 60)
    print("✅ 混元大模型API已成功打通！")
    print("=" * 60)
    
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("\n💡 请确保：")
    print("  1. 在项目根目录运行此脚本")
    print("  2. 已安装所有依赖（requests等）")
    sys.exit(1)
























