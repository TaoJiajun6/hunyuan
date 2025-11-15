"""
批量上传 music 目录到云存储

使用方法（三种方式，按优先级）：

方式1：直接运行，交互式输入配置（推荐）
   python tools/upload_music_to_cloud.py

方式2：使用配置文件（推荐，避免每次输入）
   在 hunyuan_podcast/agc-apiclient-*.json 文件中配置：
   {
     "client_id": "your-client-id",
     "client_secret": "your-client-secret",
     "project_id": "your-product-id"
   }
   然后运行：
   python tools/upload_music_to_cloud.py --bucket your-bucket

方式3：命令行参数（适合脚本调用）
   python tools/upload_music_to_cloud.py \\
     --music-dir ./music \\
     --storage-url https://ops-server-drcn.agcstorage.link/v0/ \\
     --bucket your-bucket \\
     --client-id your-client-id \\
     --client-secret your-client-secret \\
     --product-id your-product-id
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Tuple

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from hunyuan_podcast.upload_client import (
    get_agc_token,
    upload_file_to_agc,
    _find_agc_client_json,
    _load_agc_credentials_from_file,
    AGCUploadError
)


def get_audio_files(music_dir: str) -> List[Tuple[str, str]]:
    """
    递归获取 music 目录下的所有音频文件
    
    Args:
        music_dir: music 目录路径
    
    Returns:
        [(本地文件路径, 云存储路径), ...]
        云存储路径格式：music/子目录/文件名.mp3
    """
    audio_extensions = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac'}
    files = []
    music_path = Path(music_dir)
    
    if not music_path.exists():
        print(f"错误：音乐目录不存在: {music_dir}")
        return files
    
    # 遍历所有文件
    for file_path in music_path.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in audio_extensions:
            # 计算相对路径（相对于 music 目录）
            relative_path = file_path.relative_to(music_path)
            # 转换为云存储路径（使用正斜杠）
            cloud_path = f"music/{relative_path.as_posix()}"
            files.append((str(file_path), cloud_path))
    
    return files


def upload_music_directory(
    music_dir: str,
    storage_url: str,
    bucket: str,
    client_id: str,
    client_secret: str,
    product_id: str,
    domain: str = "connect-api.cloud.huawei.com",
    skip_existing: bool = False
) -> dict:
    """
    批量上传 music 目录到云存储
    
    Args:
        music_dir: 本地 music 目录路径
        storage_url: 云存储URL
        bucket: 存储桶名称
        client_id: AGC客户端ID
        client_secret: AGC客户端密钥
        product_id: AGC项目ID
        domain: AGC域名
        skip_existing: 是否跳过已存在的文件（暂不支持，所有文件都会上传）
    
    Returns:
        上传结果统计
    """
    # 获取所有音频文件
    print("=" * 60)
    print("正在扫描音乐文件...")
    print(f"音乐目录: {music_dir}")
    print("=" * 60)
    
    files = get_audio_files(music_dir)
    
    if not files:
        print("⚠️ 未找到任何音频文件")
        return {
            'total': 0,
            'success': 0,
            'failed': 0,
            'failed_files': []
        }
    
    print(f"✓ 找到 {len(files)} 个音频文件")
    print()
    
    # 获取 token
    print("正在获取 AGC access token...")
    try:
        token = get_agc_token(domain, client_id, client_secret)
        print("✓ Token 获取成功")
    except Exception as e:
        print(f"✗ 获取 token 失败: {e}")
        raise
    
    print()
    print("=" * 60)
    print("开始批量上传...")
    print("=" * 60)
    
    # 统计信息
    total = len(files)
    success_count = 0
    failed_count = 0
    failed_files = []
    
    # 上传每个文件
    for idx, (local_path, cloud_path) in enumerate(files, 1):
        file_name = os.path.basename(local_path)
        file_size_mb = os.path.getsize(local_path) / (1024 * 1024)
        
        print(f"[{idx}/{total}] 上传: {cloud_path}")
        print(f"  文件: {file_name} ({file_size_mb:.2f} MB)")
        
        try:
            upload_file_to_agc(
                storage_url=storage_url,
                bucket=bucket,
                object_name=cloud_path,
                file_path=local_path,
                client_id=client_id,
                product_id=product_id,
                token=token,
                timeout=300  # 5分钟超时，适合大文件
            )
            success_count += 1
            print(f"  ✓ 上传成功")
        except Exception as e:
            failed_count += 1
            failed_files.append((cloud_path, str(e)))
            print(f"  ✗ 上传失败: {e}")
        
        print()
    
    # 输出统计信息
    print("=" * 60)
    print("上传完成！")
    print("=" * 60)
    print(f"总计: {total} 个文件")
    print(f"成功: {success_count} 个")
    print(f"失败: {failed_count} 个")
    
    if failed_files:
        print()
        print("失败的文件列表:")
        for cloud_path, error in failed_files:
            print(f"  - {cloud_path}: {error}")
    
    return {
        'total': total,
        'success': success_count,
        'failed': failed_count,
        'failed_files': failed_files
    }


def get_config_interactive():
    """交互式获取配置"""
    config = {}
    
    print("=" * 60)
    print("配置云存储信息")
    print("=" * 60)
    print("提示：可以直接按回车使用默认值或从配置文件读取")
    print()
    
    # 存储URL
    default_storage_url = "https://ops-server-drcn.agcstorage.link/v0/"
    storage_url = input(f"云存储URL [{default_storage_url}]: ").strip()
    config['storage_url'] = storage_url or default_storage_url
    
    # 存储桶
    bucket = input("存储桶名称 (必填): ").strip()
    if not bucket:
        print("错误：存储桶名称不能为空")
        return None
    config['bucket'] = bucket
    
    # 客户端ID
    client_id = input("AGC客户端ID (必填): ").strip()
    if not client_id:
        print("错误：客户端ID不能为空")
        return None
    config['client_id'] = client_id
    
    # 客户端密钥
    import getpass
    client_secret = getpass.getpass("AGC客户端密钥 (必填，输入时不会显示): ").strip()
    if not client_secret:
        print("错误：客户端密钥不能为空")
        return None
    config['client_secret'] = client_secret
    
    # 项目ID
    product_id = input("AGC项目ID (可选): ").strip()
    config['product_id'] = product_id or ''
    
    # 域名
    default_domain = "connect-api.cloud.huawei.com"
    domain = input(f"AGC域名 [{default_domain}]: ").strip()
    config['domain'] = domain or default_domain
    
    return config


def main():
    parser = argparse.ArgumentParser(description='批量上传 music 目录到云存储')
    parser.add_argument('--music-dir', type=str, default='music',
                        help='本地 music 目录路径（默认: music）')
    parser.add_argument('--storage-url', type=str,
                        help='云存储URL')
    parser.add_argument('--bucket', type=str,
                        help='存储桶名称')
    parser.add_argument('--client-id', type=str,
                        help='AGC客户端ID')
    parser.add_argument('--client-secret', type=str,
                        help='AGC客户端密钥')
    parser.add_argument('--product-id', type=str,
                        help='AGC项目ID')
    parser.add_argument('--domain', type=str, default='connect-api.cloud.huawei.com',
                        help='AGC域名（默认: connect-api.cloud.huawei.com）')
    parser.add_argument('--interactive', action='store_true',
                        help='交互式输入配置信息')
    
    args = parser.parse_args()
    
    # 优先从命令行参数读取
    storage_url = args.storage_url
    bucket = args.bucket
    client_id = args.client_id
    client_secret = args.client_secret
    product_id = args.product_id
    domain = args.domain
    
    # 如果缺少配置，尝试从文件读取
    cfg_path = _find_agc_client_json()
    if cfg_path:
        print(f"✓ 找到配置文件: {cfg_path}")
        cred = _load_agc_credentials_from_file(cfg_path)
        client_id = client_id or cred.get('client_id')
        client_secret = client_secret or cred.get('client_secret')
        product_id = product_id or cred.get('project_id')
    
    # 如果仍然缺少配置，尝试从环境变量读取（可选）
    if not storage_url:
        storage_url = os.getenv('AGC_STORAGE_URL', 'https://ops-server-drcn.agcstorage.link/v0/')
    if not bucket:
        bucket = os.getenv('AGC_BUCKET')
    if not client_id:
        client_id = os.getenv('AGC_CLIENT_ID')
    if not client_secret:
        client_secret = os.getenv('AGC_CLIENT_SECRET')
    if not product_id:
        product_id = os.getenv('AGC_PRODUCT_ID', '')
    if not domain:
        domain = os.getenv('AGC_DOMAIN', 'connect-api.cloud.huawei.com')
    
    # 如果仍然缺少必需配置，使用交互式输入
    if args.interactive or not storage_url or not bucket or not client_id or not client_secret:
        print()
        print("缺少必需的配置信息，将使用交互式输入")
        print("提示：可以将配置保存在 hunyuan_podcast/agc-apiclient-*.json 文件中")
        print("      格式：{\"client_id\": \"...\", \"client_secret\": \"...\", \"project_id\": \"...\"}")
        print()
        
        config = get_config_interactive()
        if not config:
            print("配置失败，退出")
            sys.exit(1)
        
        storage_url = storage_url or config['storage_url']
        bucket = bucket or config['bucket']
        client_id = client_id or config['client_id']
        client_secret = client_secret or config['client_secret']
        product_id = product_id or config.get('product_id', '')
        domain = domain or config.get('domain', 'connect-api.cloud.huawei.com')
    
    # 最终验证
    if not storage_url or not bucket:
        print("错误：需要提供 storage_url 和 bucket")
        print("  可以通过参数 --storage-url 和 --bucket 提供")
        print("  或使用 --interactive 交互式输入")
        sys.exit(1)
    
    if not client_id or not client_secret:
        print("错误：需要提供 client_id 和 client_secret")
        print("  可以通过参数 --client-id 和 --client-secret 提供")
        print("  或在 hunyuan_podcast/agc-apiclient-*.json 文件中配置")
        print("  或使用 --interactive 交互式输入")
        sys.exit(1)
    
    # 确保 music_dir 是绝对路径
    music_dir = os.path.abspath(args.music_dir)
    
    # 显示配置信息
    print("=" * 60)
    print("批量上传音乐文件到云存储")
    print("=" * 60)
    print(f"音乐目录: {music_dir}")
    print(f"存储URL: {storage_url}")
    print(f"存储桶: {bucket}")
    print(f"客户端ID: {'已设置' if client_id else '未设置'}")
    print(f"项目ID: {'已设置' if product_id else '未设置'}")
    print("=" * 60)
    print()
    
    # 确认
    response = input("确认开始上传？(y/n): ")
    if response.lower() != 'y':
        print("已取消")
        sys.exit(0)
    
    # 执行上传
    try:
        result = upload_music_directory(
            music_dir=music_dir,
            storage_url=storage_url,
            bucket=bucket,
            client_id=client_id,
            client_secret=client_secret,
            product_id=product_id or '',
            domain=domain
        )
        
        # 输出最终结果
        print()
        if result['failed'] == 0:
            print("🎉 所有文件上传成功！")
        else:
            print(f"⚠️ 有 {result['failed']} 个文件上传失败，请检查上面的错误信息")
        
        sys.exit(0 if result['failed'] == 0 else 1)
        
    except KeyboardInterrupt:
        print("\n\n上传已中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 上传过程出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

