"""
启动混元AI播客生成API服务
"""
import os
import sys

# 设置HuggingFace镜像
if "HF_ENDPOINT" not in os.environ:
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    print(f"💡 已自动设置 HuggingFace 镜像: {os.environ['HF_ENDPOINT']}")
    print(f"   如需使用其他镜像，请设置环境变量: HF_ENDPOINT")

try:
    from hunyuan_podcast.api_server import app
    import uvicorn
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("\n解决方案：")
    print("1. 安装FastAPI和uvicorn：")
    print("   pip install fastapi uvicorn python-multipart")
    print("\n2. 如果使用 uv 环境：")
    print("   cd index-tts")
    print("   uv pip install fastapi uvicorn python-multipart")
    sys.exit(1)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="混元AI播客生成API服务")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="API服务主机")
    parser.add_argument("--port", type=int, default=8000, help="API服务端口")
    args = parser.parse_args()
    
    print(f"\n🚀 启动混元AI播客生成API服务")
    print(f"📡 API地址: http://{args.host}:{args.port}")
    print(f"📚 API文档: http://{args.host}:{args.port}/docs")
    print(f"💡 健康检查: http://{args.host}:{args.port}/health")
    print(f"🔄 工作流集成: 使用上述API端点进行集成\n")
    
    uvicorn.run(app, host=args.host, port=args.port)


