#!/usr/bin/env python
"""
Cloud Studio 环境检测工具
用于检测和显示 Cloud Studio 环境信息，帮助构建预览地址
"""
import os
import sys

def check_cloud_studio_env():
    """检测Cloud Studio环境变量"""
    print("=" * 60)
    print("Cloud Studio 环境检测工具")
    print("=" * 60)
    print()
    
    # 检查所有可能的环境变量
    env_vars = [
        "X_IDE_SPACE_KEY",
        "CLOUD_STUDIO_SPACE_KEY",
        "CLOUD_STUDIO_REGION",
        "REGION",
        "CLOUD_STUDIO_REGION_NAME",
        "WORKSPACE_ID",
        "WORKSPACE_NAME",
        "WORKSPACE_URL",
        "CLOUD_STUDIO_URL",
        "CLOUD_STUDIO_DOMAIN",
        "CLOUD_STUDIO_PORT",
        "TENCENT_CLOUD_STUDIO",
        "USER",
        "PWD",
    ]
    
    print("📋 环境变量检查:")
    print("-" * 60)
    found_vars = {}
    for var in env_vars:
        value = os.getenv(var)
        if value:
            # 隐藏敏感信息的部分内容
            if "KEY" in var or "ID" in var:
                display_value = value[:8] + "..." if len(value) > 8 else value
            else:
                display_value = value
            print(f"  ✅ {var:30s} = {display_value}")
            found_vars[var] = value
        else:
            print(f"  ❌ {var:30s} = (未设置)")
    print()
    
    # 尝试提取 Space Key 和 Region
    space_key = None
    region = None
    
    # 方法1: 直接从环境变量获取
    space_key = (
        os.getenv("X_IDE_SPACE_KEY") or 
        os.getenv("CLOUD_STUDIO_SPACE_KEY") or
        os.getenv("WORKSPACE_ID") or
        os.getenv("WORKSPACE_NAME")
    )
    
    region = (
        os.getenv("REGION") or 
        os.getenv("CLOUD_STUDIO_REGION") or
        os.getenv("CLOUD_STUDIO_REGION_NAME")
    )
    
    # 方法2: 从URL中提取
    workspace_url = os.getenv("WORKSPACE_URL") or os.getenv("CLOUD_STUDIO_URL")
    if workspace_url and ".cloudstudio.work" in workspace_url:
        try:
            domain = workspace_url.replace("https://", "").replace("http://", "").split("/")[0]
            domain_part = domain.replace(".cloudstudio.work", "")
            parts = domain_part.split(".")
            if len(parts) >= 2:
                space_key = parts[0]
                region = parts[1]
                print(f"📌 从 URL 中提取:")
                print(f"   Space Key: {space_key}")
                print(f"   Region: {region}")
                print()
        except Exception as e:
            print(f"⚠️  从 URL 提取失败: {e}")
            print()
    
    # 显示结果
    print("=" * 60)
    print("🎯 检测结果:")
    print("=" * 60)
    
    if space_key and region:
        print(f"✅ 成功检测到 Cloud Studio 环境!")
        print(f"   Space Key: {space_key}")
        print(f"   Region: {region}")
        print()
        print("🌐 预览地址格式:")
        print(f"   https://{space_key}--<PORT>.{region}.cloudstudio.work/")
        print()
        print("📝 示例（端口 7861）:")
        print(f"   https://{space_key}--7861.{region}.cloudstudio.work/")
        print()
    else:
        print("❌ 未能自动检测到 Space Key 或 Region")
        print()
        print("💡 手动查找方法:")
        print("   1. 查看浏览器地址栏")
        print("   2. 找到类似这样的地址:")
        print("      https://XXXXX.ap-guangzhou.cloudstudio.work/")
        print("   3. XXXXX 就是 Space Key")
        print("   4. ap-guangzhou 就是 Region")
        print()
        print("📝 然后手动构建预览地址:")
        print("   https://<SPACE_KEY>--<PORT>.<REGION>.cloudstudio.work/")
        print()
        print("   例如:")
        print("   https://hfrsgm--7861.ap-guangzhou.cloudstudio.work/")
        print()
    
    # 显示当前工作目录
    print("=" * 60)
    print("📁 当前工作目录:")
    print(f"   {os.getcwd()}")
    print()
    
    # 检查是否在Cloud Studio环境中
    is_cloud_studio = any([
        os.getenv("CLOUD_STUDIO_PORT"),
        os.getenv("TENCENT_CLOUD_STUDIO"),
        os.getenv("X_IDE_SPACE_KEY"),
        "cloudstudio" in os.getenv("USER", "").lower(),
        "cloudstudio" in os.getcwd().lower(),
        ".cloudstudio.work" in str(os.getenv("WORKSPACE_URL", ""))
    ])
    
    if is_cloud_studio:
        print("✅ 检测到 Cloud Studio 环境")
    else:
        print("⚠️  未检测到明确的 Cloud Studio 环境特征")
    
    print("=" * 60)

if __name__ == "__main__":
    check_cloud_studio_env()

























