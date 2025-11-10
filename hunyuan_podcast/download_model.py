"""
使用 ModelScope 下载 IndexTTS-2 模型

注意：此脚本需要安装 modelscope 包
安装方法: pip install modelscope==1.27.0
"""
import os
import sys

def download_model():
    """下载 IndexTTS-2 模型"""
    try:
        # 运行时导入 modelscope
        # 注意：如果 IDE 显示导入错误，这是正常的，因为 modelscope 需要在运行时安装
        from modelscope.hub.snapshot_download import snapshot_download  # type: ignore[import-untyped]
    except ImportError as e:
        print("❌ 错误：无法导入 modelscope")
        print(f"   错误详情: {e}")
        print("\n💡 解决方案：")
        print("   1. 安装 modelscope:")
        print("      pip install modelscope==1.27.0")
        print("   2. 或者使用命令行工具下载:")
        print("      modelscope download --model IndexTeam/IndexTTS-2 --local_dir checkpoints")
        sys.exit(1)
    
    # 确保输出目录存在
    cache_dir = "checkpoints"
    os.makedirs(cache_dir, exist_ok=True)
    
    print("🚀 开始下载 IndexTTS-2 模型...")
    print(f"   模型ID: IndexTeam/IndexTTS-2")
    print(f"   保存目录: {os.path.abspath(cache_dir)}")
    print("   这可能需要一些时间，请耐心等待...\n")
    
    try:
        snapshot_download(
            model_id="IndexTeam/IndexTTS-2",
            cache_dir=cache_dir,
            revision="master"
        )
        print("\n✅ 模型下载完成！")
        print(f"   模型文件保存在: {os.path.abspath(cache_dir)}")
    except Exception as e:
        print(f"\n❌ 下载失败: {e}")
        print("\n💡 可能的解决方案：")
        print("   1. 检查网络连接")
        print("   2. 尝试使用命令行工具:")
        print("      modelscope download --model IndexTeam/IndexTTS-2 --local_dir checkpoints")
        print("   3. 或使用 HuggingFace CLI:")
        print("      hf download IndexTeam/IndexTTS-2 --local-dir=checkpoints")
        sys.exit(1)


if __name__ == "__main__":
    download_model()
