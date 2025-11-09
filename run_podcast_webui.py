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
    print(f"\n🚀 混元AI播客生成系统已启动！")
    print(f"📡 访问地址: http://{args.host}:{args.port}")
    print(f"💡 按 Ctrl+C 停止服务\n")
    
    # 添加输出目录到允许的路径列表
    from hunyuan_podcast.config import OUTPUT_DIR
    import os
    output_dir_abs = os.path.abspath(OUTPUT_DIR)
    print(f"📁 输出目录: {output_dir_abs}")
    
    demo.queue(10)
    demo.launch(
        server_name=args.host,
        server_port=args.port,
        share=False,
        allowed_paths=[output_dir_abs]
    )

