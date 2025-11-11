"""
启动混元AI播客生成API服务
"""
import os
import sys
import socket

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


def get_local_ip():
    """获取本机IP地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


def get_cloud_studio_preview_url(port):
    """获取Cloud Studio预览地址"""
    # 方法1: 从环境变量获取
    cloud_studio_key = (
        os.getenv("X_IDE_SPACE_KEY") or 
        os.getenv("CLOUD_STUDIO_SPACE_KEY") or
        os.getenv("WORKSPACE_ID") or
        os.getenv("WORKSPACE_NAME")
    )
    
    cloud_studio_region = (
        os.getenv("REGION") or 
        os.getenv("CLOUD_STUDIO_REGION") or
        os.getenv("CLOUD_STUDIO_REGION_NAME")
    )
    
    # 方法2: 从WORKSPACE_URL中提取
    workspace_url = os.getenv("WORKSPACE_URL") or os.getenv("CLOUD_STUDIO_URL")
    if workspace_url and ".cloudstudio.work" in workspace_url:
        try:
            domain = workspace_url.replace("https://", "").replace("http://", "").split("/")[0]
            domain_part = domain.replace(".cloudstudio.work", "")
            parts = domain_part.split(".")
            if len(parts) >= 2:
                cloud_studio_key = parts[0]
                cloud_studio_region = parts[1]
        except:
            pass
    
    # 方法3: 从CLOUD_STUDIO_DOMAIN环境变量提取
    cloud_studio_domain = os.getenv("CLOUD_STUDIO_DOMAIN")
    if cloud_studio_domain and not cloud_studio_key:
        try:
            domain_part = cloud_studio_domain.replace(".cloudstudio.work", "")
            parts = domain_part.split(".")
            if len(parts) >= 2:
                cloud_studio_key = parts[0]
                cloud_studio_region = parts[1]
        except:
            pass
    
    # 如果找到了key和region，生成预览地址
    if cloud_studio_key and cloud_studio_region:
        preview_url = f"https://{cloud_studio_key}--{port}.{cloud_studio_region}.cloudstudio.work/"
        return preview_url, cloud_studio_key, cloud_studio_region
    
    return None, None, None


def detect_gpu_and_print_info():
    """检测GPU并打印信息"""
    try:
        import torch
        if torch.cuda.is_available():
            print(f"🚀 检测到GPU可用:")
            print(f"   GPU设备数量: {torch.cuda.device_count()}")
            for i in range(torch.cuda.device_count()):
                print(f"   GPU {i}: {torch.cuda.get_device_name(i)}")
            print(f"   💡 建议使用 --fp16 和 --cuda_kernel 参数以加速推理")
            return True
        else:
            print("⚠️  未检测到GPU，将使用CPU模式（速度较慢）")
            return False
    except ImportError:
        print("⚠️  PyTorch未安装，无法检测GPU")
        return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="混元AI播客生成API服务")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="API服务主机")
    parser.add_argument("--port", type=int, default=8000, help="API服务端口")
    parser.add_argument("--fp16", action="store_true", help="使用FP16精度（GPU加速）")
    parser.add_argument("--cuda_kernel", action="store_true", help="使用CUDA内核加速")
    parser.add_argument("--workers", type=int, default=1, help="UVicorn工作进程数（>=2 可并发处理进度查询）")
    args = parser.parse_args()
    
    # 检测GPU
    has_gpu = detect_gpu_and_print_info()
    
    # 设置GPU配置环境变量（传递给api_server.py）
    if args.fp16:
        os.environ["USE_FP16"] = "true"
        print("✅ 已启用FP16精度")
    else:
        os.environ["USE_FP16"] = "false"
        if has_gpu:
            print("💡 提示: 检测到GPU，建议使用 --fp16 参数以加速推理")
    
    if args.cuda_kernel:
        os.environ["USE_CUDA_KERNEL"] = "true"
        print("✅ 已启用CUDA内核加速")
    else:
        os.environ["USE_CUDA_KERNEL"] = "false"
        if has_gpu:
            print("💡 提示: 检测到GPU，建议使用 --cuda_kernel 参数以进一步加速")
    
    # 自动检测设备（如果未指定）
    if has_gpu and not os.getenv("DEVICE"):
        os.environ["DEVICE"] = "cuda:0"
        print(f"✅ 自动设置设备: cuda:0")
    
    # 检测Cloud Studio环境
    is_cloud_studio = any([
        os.getenv("CLOUD_STUDIO_PORT"),
        os.getenv("TENCENT_CLOUD_STUDIO"),
        os.getenv("X_IDE_SPACE_KEY"),
        os.getenv("CLOUD_STUDIO_SPACE_KEY"),
        os.getenv("CLOUD_STUDIO_DOMAIN"),
        "cloudstudio" in os.getenv("USER", "").lower(),
        "cloudstudio" in os.getcwd().lower(),
        ".cloudstudio.work" in str(os.getenv("WORKSPACE_URL", ""))
    ])
    
    # 获取本地IP
    local_ip = get_local_ip()
    
    # 尝试获取Cloud Studio预览地址
    preview_url, space_key, region = get_cloud_studio_preview_url(args.port)
    
    print(f"\n 启动混元AI播客生成API服务")
    print(f"\n 访问地址：")
    print(f"   本地访问: http://127.0.0.1:{args.port}")
    print(f"   或使用: http://localhost:{args.port}")
    
    if args.host == "0.0.0.0":
        print(f" 局域网访问: http://{local_ip}:{args.port}")
    
    # 如果是Cloud Studio环境
    if is_cloud_studio:
        print(f"\n  Cloud Studio环境检测到:")
        if preview_url:
            print(f"      HTTPS预览地址（外部访问）:")
            print(f"         {preview_url}")
            print(f"\n      配置说明:")
            print(f"         • 在鸿蒙应用中配置此地址: {preview_url}")
            print(f"         • Space Key: {space_key}")
            print(f"         • Region: {region}")
            print(f"         • 端口: {args.port}")
        else:
            print(f"      手动构建预览地址:")
            print(f"         1. 查看浏览器地址栏: https://XXXXX.ap-guangzhou.cloudstudio.work/")
            print(f"         2. 提取 Space Key (XXXXX) 和 Region (ap-guangzhou)")
            print(f"         3. 构建地址: https://XXXXX--{args.port}.ap-guangzhou.cloudstudio.work/")
            print(f"         4. 在鸿蒙应用中配置此地址")
    
    print(f"\n API文档: https://pexlsj--{args.port}.ap-singapore.cloudstudio.work/docs")
    print(f" 健康检查: https://pexlsj--{args.port}.ap-singapore.cloudstudio.work/health")
    print(f" API端点:")
    print(f"   • 多角色播客: POST /api/v1/podcast/multi_role")
    print(f"   • 自定义角色: POST /api/v1/podcast/character")
    print(f"   • 主题深度播客: POST /api/v1/podcast/deep")
    print(f"   • 文本分析: POST /api/v1/podcast/analyze")
    print()
    
    # 提示并发建议
    if args.workers and args.workers >= 2:
        print(f" 并发已启用：workers={args.workers}（可在生成时同时响应进度查询）")
    else:
        print("ℹ 当前为单进程模式（workers=1）。如需生成时可查询进度，建议设置 --workers 2。")
    
    # 多进程模式要求以 import string 形式传递 app，单进程可直接传对象
    if args.workers and args.workers > 1:
        uvicorn.run("hunyuan_podcast.api_server:app", host=args.host, port=args.port, workers=args.workers)
    else:
        uvicorn.run(app, host=args.host, port=args.port, workers=1)


