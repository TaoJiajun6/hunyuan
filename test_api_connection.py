#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试混元大模型API连接
"""
import sys
import os
import io

# 修复Windows控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加项目路径
sys.path.insert(0, '.')

try:
    from hunyuan_podcast.api_client import get_client
    from hunyuan_podcast.config import SILICONFLOW_API_KEY, SILICONFLOW_API_BASE, SILICONFLOW_MODEL
    
    print("=" * 60)
    print("混元大模型API连接测试")
    print("=" * 60)
    print(f"\n配置信息：")
    print(f"  API Base: {SILICONFLOW_API_BASE}")
    print(f"  模型: {SILICONFLOW_MODEL}")
    print(f"  API Key: {SILICONFLOW_API_KEY[:20]}...{SILICONFLOW_API_KEY[-10:]}")
    
    print("\n" + "-" * 60)
    print("测试1: 创建API客户端")
    print("-" * 60)
    client = get_client()
    print("[OK] API客户端创建成功")
    
    print("\n" + "-" * 60)
    print("测试2: 发送简单测试请求")
    print("-" * 60)
    
    test_prompt = "你好，请用一句话介绍你自己。"
    print(f"测试提示词: {test_prompt}")
    
    try:
        print("\n正在发送请求...")
        result = client.generate_text(
            prompt=test_prompt,
            max_tokens=50
        )
        
        print(f"\n[OK] API调用成功！")
        print(f"返回内容: {result}")
        print(f"内容长度: {len(result)}")
        
        if len(result) == 0:
            print("\n[WARNING] 警告：返回内容为空！")
        else:
            print("\n[OK] API工作正常！")
            
    except Exception as e:
        print(f"\n[ERROR] API调用失败：{str(e)}")
        import traceback
        print("\n详细错误信息：")
        traceback.print_exc()
        
        print("\n" + "-" * 60)
        print("故障排除建议：")
        print("-" * 60)
        print("1. 检查API密钥是否正确")
        print("2. 检查网络连接")
        print("3. 检查API服务是否可用")
        print("4. 查看上面的详细错误信息")
    
    print("\n" + "=" * 60)
    
except ImportError as e:
    print(f"[ERROR] 导入错误: {e}")
    print("\n请确保在项目根目录运行此脚本")
    sys.exit(1)

