#!/usr/bin/env python
"""
混元AI播客生成系统 - 启动脚本
"""
import sys
import os

# 设置 HuggingFace 镜像（如果未设置）
if "HF_ENDPOINT" not in os.environ:
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    print("💡 已自动设置 HuggingFace 镜像: https://hf-mirror.com")
    print("   如需使用其他镜像，请设置环境变量: HF_ENDPOINT\n")

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 尝试添加 index-tts 到路径（如果使用 uv 环境）
index_tts_path = os.path.join(project_root, "index-tts")
if os.path.exists(index_tts_path) and index_tts_path not in sys.path:
    sys.path.insert(0, index_tts_path)

# 运行WebUI
if __name__ == "__main__":
    try:
        from hunyuan_podcast.webui import create_webui
    except ImportError as e:
        error_msg = str(e)
        print(f"❌ 导入错误: {error_msg}")
        
        # 检查是否是缺少依赖
        missing_deps = []
        if "librosa" in error_msg:
            missing_deps.append("librosa")
        if "gradio" in error_msg:
            missing_deps.append("gradio")
        if "torch" in error_msg:
            missing_deps.append("torch/torchaudio")
        if "openai" in error_msg:
            missing_deps.append("openai")
        if "requests" in error_msg:
            missing_deps.append("requests")
        
        if missing_deps:
            print(f"\n⚠️  缺少依赖: {', '.join(missing_deps)}")
            print("\n💡 解决方案：")
            print("1. 如果使用 uv 环境（推荐）：")
            print("   cd index-tts")
            print("   uv sync --all-extras  # 安装所有依赖")
            print("   或")
            print("   uv pip install " + " ".join(missing_deps))
            print("   然后运行: uv run python ../run_podcast_webui.py")
            print("\n2. 如果使用标准 Python 环境：")
            print("   pip install " + " ".join(missing_deps))
            print("\n3. 激活 uv 环境后运行：")
            print("   cd index-tts")
            print("   source .venv/bin/activate  # Linux/macOS")
            print("   或")
            print("   .venv\\Scripts\\activate  # Windows")
            print("   然后运行: python ../run_podcast_webui.py")
        else:
            print("\n💡 提示：")
            print("1. 如果使用 uv 环境，请先激活环境：")
            print("   cd index-tts")
            print("   source .venv/bin/activate  # Linux/macOS")
            print("   或")
            print("   .venv\\Scripts\\activate  # Windows")
            print("   然后运行: python ../run_podcast_webui.py")
            print("\n2. 或使用 uv run：")
            print("   cd index-tts")
            print("   uv run python ../run_podcast_webui.py")
        
        sys.exit(1)
    
    demo, args = create_webui()
    
    # 获取可用的访问地址
    import socket
    def get_local_ip():
        """获取本机IP地址"""
        try:
            # 连接到一个远程地址来获取本机IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    local_ip = get_local_ip()
    
    # 检测运行环境
    is_cloud_studio = any([
        os.getenv("CLOUD_STUDIO_PORT"),
        os.getenv("TENCENT_CLOUD_STUDIO"),
        "cloudstudio" in os.getenv("USER", "").lower(),
        "cloudstudio" in os.getcwd().lower()
    ])
    
    is_vscode_server = os.getenv("VSCODE_SERVER_PORT") or os.getenv("REMOTE_CONTAINERS")
    is_codespace = os.getenv("CODESPACE_NAME")
    
    print(f"\n🚀 混元AI播客生成系统已启动！")
    print(f"\n📡 访问地址：")
    
    # 优先显示本地访问地址（最常用）
    print(f"   ✅ 本地访问: http://127.0.0.1:{args.port}")
    print(f"   ✅ 或使用: http://localhost:{args.port}")
    
    # 如果是Cloud Studio或其他云平台
    if is_cloud_studio:
        print(f"\n   🌐 Cloud Studio环境检测到:")
        print(f"      • 请在Cloud Studio的端口转发功能中查看访问地址")
        print(f"      • 或使用: http://127.0.0.1:{args.port}")
        print(f"      • 如果配置了公网访问，请使用Cloud Studio提供的公网地址")
    elif is_vscode_server or is_codespace:
        print(f"\n   🌐 云平台环境检测到:")
        print(f"      • 请在平台的端口转发/预览功能中查看访问地址")
        print(f"      • 或使用: http://127.0.0.1:{args.port}")
    elif args.host == "0.0.0.0":
        print(f"   🌐 局域网访问: http://{local_ip}:{args.port}")
        print(f"      (同一局域网内的其他设备可以使用此地址访问)")
    
    print(f"\n💡 提示:")
    print(f"   • 如果使用浏览器访问，优先尝试: http://127.0.0.1:{args.port}")
    print(f"   • 如果在云平台，请查看平台的端口转发或预览功能")
    print(f"   • 如果无法访问，请检查防火墙或安全组设置")
    print(f"\n💡 按 Ctrl+C 停止服务\n")
    
    # 添加输出目录到允许的路径列表
    from hunyuan_podcast.config import OUTPUT_DIR
    import os
    output_dir_abs = os.path.abspath(OUTPUT_DIR)
    print(f"📁 输出目录: {output_dir_abs}\n")
    
    demo.queue(10)
    demo.launch(
        server_name=args.host,
        server_port=args.port,
        share=False,
        allowed_paths=[output_dir_abs]
    )

