"""
混元AI播客生成系统 - 主入口
"""
import os
from .webui import create_webui
from .config import OUTPUT_DIR

if __name__ == "__main__":
    demo, args = create_webui()
    
    # 添加输出目录到允许的路径列表
    output_dir_abs = os.path.abspath(OUTPUT_DIR)
    
    demo.queue(10)
    demo.launch(
        server_name=args.host,
        server_port=args.port,
        share=False,
        allowed_paths=[output_dir_abs]
    )

