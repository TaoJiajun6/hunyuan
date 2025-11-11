"""
在服务端运行的上传脚本（直接调用库接口，不走终端交互）

用法（在服务端 Python 环境中运行）：
python tools/run_upload_server_side.py \
  --output-path /workspace/hunyuan/outputs/podcasts/podcast_1762840888.wav \
  --storage-url https://ops-server-drcn.agcstorage.link/v0/ \
  --bucket podcasters-y0qig \
  --product-id 461323198430936564

脚本会优先使用命令行参数，其次环境变量，最后尝试读取仓库内的 agc-apiclient-*.json。
"""

import argparse
import json
import os
import sys

# Ensure project root is on sys.path so we can import hunyuan_podcast when script
# is executed from /workspace or other working directories.
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from hunyuan_podcast.upload_client import upload_generated_podcast


def main():
    parser = argparse.ArgumentParser(description='Upload a server-side generated podcast to AGC')
    parser.add_argument('--output-path', required=True, help='服务端生成的文件绝对路径')
    parser.add_argument('--storage-url', required=True, help='AGC storage base URL, e.g. https://ops-server-drcn.agcstorage.link/v0/')
    parser.add_argument('--bucket', required=True, help='AGC bucket name')
    parser.add_argument('--object-name', required=False, help='目标 object name in bucket (默认 outputs/podcasts/<basename>)')
    parser.add_argument('--domain', required=False, default='connect-api.cloud.huawei.com', help='AGC domain for token')
    parser.add_argument('--client-id', required=False)
    parser.add_argument('--client-secret', required=False)
    parser.add_argument('--product-id', required=False)

    args = parser.parse_args()

    try:
        res = upload_generated_podcast(
            output_path=args.output_path,
            storage_url=args.storage_url,
            bucket=args.bucket,
            object_name=args.object_name,
            domain=args.domain,
            client_id=args.client_id,
            client_secret=args.client_secret,
            product_id=args.product_id,
        )
        print(json.dumps(res, ensure_ascii=False, indent=2))
        sys.exit(0)
    except Exception as e:
        print(f"上传失败: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()
