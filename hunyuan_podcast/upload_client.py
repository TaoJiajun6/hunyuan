"""
轻量 AGC 上传客户端（模块化）

该模块提供一个可编程接口，用于在服务端把已生成的播客文件上传到华为 AGC 存储。
- 优先从 `hunyuan_podcast/agc-apiclient-*.json`（仓库内）读取 client_id/client_secret/project_id
- 支持通过参数或环境变量覆盖配置

依赖：requests
安装：pip install requests

示例（在服务端的 Python 进程中直接调用）：
from hunyuan_podcast.upload_client import upload_generated_podcast
res = upload_generated_podcast(
    output_path=r"d:\Develop\hunyuan\outputs\podcasts\podcast_1762840888.wav",
    storage_url="https://ops-server-drcn.agcstorage.link/v0/",
    bucket="podcasters-y0qig",
    product_id="461323198430936564"
)
print(res)

注意：请妥善保管 client_secret，避免在公开仓库中暴露。
"""

import glob
import json
import logging
import mimetypes
import os
import time
import math
from typing import Optional, Dict, Any

import requests
from requests import RequestException

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# Simple module-level token cache to avoid fetching token repeatedly within its lifetime
_TOKEN_CACHE: Dict[str, Dict[str, Any]] = {}


class AGCUploadError(RuntimeError):
    """表示 AGC 上传相关的错误（可被上层捕获）"""
    pass


def _find_agc_client_json() -> Optional[str]:
    """查找仓库或模块目录下的 agc-apiclient-*.json 文件"""
    # 优先在当前模块目录下找
    base_dir = os.path.dirname(__file__)
    patterns = [os.path.join(base_dir, 'agc-apiclient-*.json'), os.path.join(os.getcwd(), 'agc-apiclient-*.json')]
    for pat in patterns:
        matches = glob.glob(pat)
        if matches:
            return matches[0]
    return None


def _load_agc_credentials_from_file(path: str) -> Dict[str, Optional[str]]:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            j = json.load(f)
        return {
            'client_id': j.get('client_id'),
            'client_secret': j.get('client_secret'),
            'project_id': j.get('project_id') or j.get('projectId') or j.get('project_id')
        }
    except Exception as e:
        logger.warning(f"读取 AGC 凭证文件失败: {e}")
        return {'client_id': None, 'client_secret': None, 'project_id': None}


def get_agc_token(domain: str, client_id: str, client_secret: str, timeout: int = 30, retries: int = 3,
                  backoff_factor: float = 0.5) -> str:
    """获取 AGC access_token（带缓存与重试）

    返回 access_token。使用 module-level 缓存避免频繁获取。
    """
    if not client_id or not client_secret:
        raise AGCUploadError('缺少 client_id 或 client_secret，无法获取 token')

    cache_key = f"{domain}:{client_id}"
    cached = _TOKEN_CACHE.get(cache_key)
    now = time.time()
    if cached and cached.get('expires_at', 0) > now + 5:
        return cached['token']

    url = f"https://{domain}/api/oauth2/v1/token"
    payload = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret
    }
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            logger.info(f"请求 AGC token (attempt {attempt}): {url}")
            logger.info(f"  Payload: grant_type={payload.get('grant_type')}, client_id={'已设置' if payload.get('client_id') else '未设置'}")
            resp = requests.post(url, json=payload, timeout=timeout)
            logger.info(f"Token 响应: status_code={resp.status_code}")
            resp.raise_for_status()
            data = resp.json()
            token = data.get('access_token')
            if not token:
                logger.error(f"获取 access_token 失败，响应: {data}")
                raise AGCUploadError(f"获取 access_token 失败，响应: {data}")
            expires_in = int(data.get('expires_in', 3600))
            _TOKEN_CACHE[cache_key] = {'token': token, 'expires_at': now + expires_in - 10}
            logger.info(f"Token 获取成功，有效期: {expires_in}秒")
            return token
        except RequestException as e:
            last_exc = e
            wait = backoff_factor * (2 ** (attempt - 1))
            logger.warning(f"请求 token 失败 (attempt {attempt}): {e}; retry in {wait}s")
            time.sleep(wait)
    raise AGCUploadError(f"无法获取 AGC token: {last_exc}")


def upload_file_to_agc(storage_url: str, bucket: str, object_name: str, file_path: str,
                       client_id: str, product_id: str, token: str, timeout: int = 300) -> requests.Response:
    """将本地文件通过 PUT 上传到 AGC 存储

    Args:
        storage_url: 基础存储 URL，例如 https://ops-server-drcn.agcstorage.link/v0/
        bucket: 存储实例名
        object_name: 上传到存储的路径/文件名，例如 outputs/podcasts/podcast.wav
        file_path: 本地文件绝对路径
        client_id: AGC API client_id（header）
        product_id: AGC 项目 ID（header productId）
        token: access_token

    Returns:
        requests.Response
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)

    if not storage_url.endswith('/'):
        storage_url = storage_url + '/'

    url = f"{storage_url}{bucket}/{object_name}"
    file_size = os.path.getsize(file_path)
    content_type, _ = mimetypes.guess_type(file_path)
    if not content_type:
        content_type = 'application/octet-stream'

    headers = {
        'productId': product_id or '',
        'client_id': client_id,
        'Authorization': f'Bearer {token}',
        'Content-Length': str(file_size),  # AGC服务器要求必须设置Content-Length头
        'X-Agc-File-Size': str(file_size),
        'X-Agc-Content-Type': content_type,
    }

    logger.info(f"上传到 AGC: {url}")
    logger.info(f"  文件大小: {file_size} bytes ({file_size / (1024 * 1024):.2f} MB)")
    logger.info(f"  Content-Length: {file_size}")
    logger.info(f"  X-Agc-Content-Type: {content_type}")
    logger.info(f"  Headers: productId={'已设置' if product_id else '未设置'}, client_id={'已设置' if client_id else '未设置'}, Authorization={'已设置' if token else '未设置'}")

    last_exc = None
    file_size_mb = file_size / (1024 * 1024)
    
    # 根据文件大小决定重试次数：小文件（<10MB）只重试1次，大文件重试2次
    if file_size_mb < 10:
        retries = 1  # 小文件只重试1次
    else:
        retries = 2  # 大文件重试2次
    
    backoff_factor = 0.5
    
    # 根据文件大小动态调整超时时间（在循环外计算，避免重复计算）
    # 对于上传操作，需要考虑写入超时，假设最小上传速度为0.1 MB/s（考虑慢速网络）
    min_upload_speed_mbps = 0.1  # 最小上传速度（MB/s），考虑慢速网络
    # 计算所需时间：文件大小(MB) / 最小速度(MB/s) + 缓冲时间
    calculated_timeout = int((file_size_mb / min_upload_speed_mbps) + 300)  # 至少300秒缓冲
    # 使用传入的timeout和计算出的timeout中的较大值，但不超过3600秒（60分钟）
    base_read_timeout = max(timeout, min(calculated_timeout, 3600))
    connect_timeout = 30  # 连接超时30秒
    
    for attempt in range(1, retries + 1):
        try:
            # 每次重试时增加超时时间
            read_timeout = int(base_read_timeout * (1 + (attempt - 1) * 0.5))  # 每次重试增加50%
            
            logger.info(f"上传尝试 {attempt}/{retries}: 连接超时={connect_timeout}秒, 读取超时={read_timeout}秒 (文件大小: {file_size_mb:.2f} MB)")
            
            # 优化上传：使用Session和连接池（每次重试创建新的session）
            session = requests.Session()
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=10,
                pool_maxsize=20,
                max_retries=0  # 禁用urllib3的重试，我们自己处理
            )
            session.mount('http://', adapter)
            session.mount('https://', adapter)
            
            try:
                upload_start = time.time()
                
                # AGC服务器要求必须使用Content-Length头，不能使用Transfer-Encoding: chunked
                # 使用字节数据或文件对象时，如果手动设置了Content-Length，requests会使用它
                # 对于小于100MB的文件，直接读取到内存（最简单可靠）
                # 对于大文件，也使用直接读取（确保Content-Length被正确使用）
                logger.info(f"直接上传模式（文件大小: {file_size_mb:.2f} MB）")
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                
                # 验证读取的数据大小
                if len(file_data) != file_size:
                    raise AGCUploadError(f"文件读取大小不匹配: 期望 {file_size} 字节，实际 {len(file_data)} 字节")
                
                resp = session.put(
                    url,
                    data=file_data,  # 使用字节数据，配合手动设置的Content-Length头
                    headers=headers,
                    timeout=(connect_timeout, read_timeout),
                    allow_redirects=True
                )
            finally:
                session.close()
            
            upload_time = time.time() - upload_start
            upload_speed = (file_size / (1024 * 1024)) / upload_time if upload_time > 0 else 0
            
            logger.info(f"上传响应: status_code={resp.status_code}, 耗时: {upload_time:.2f}秒, 速度: {upload_speed:.2f} MB/s")
            logger.info(f"  响应头: {dict(resp.headers)}")
            if resp.text:
                logger.info(f"上传响应内容: {resp.text[:500]}")
            resp.raise_for_status()
            logger.info(f"上传成功！")
            return resp
        except requests.exceptions.Timeout as e:
            last_exc = e
            logger.error(f"上传超时 (attempt {attempt}/{retries}): {str(e)}")
            logger.error(f"  文件大小: {file_size_mb:.2f} MB")
            logger.error(f"  超时设置: 连接={connect_timeout}秒, 读取={read_timeout}秒")
            if attempt < retries:
                wait = backoff_factor * (2 ** (attempt - 1))
                logger.warning(f"  {wait}s 后重试（下次将使用更长的超时时间）...")
                time.sleep(wait)
            else:
                raise AGCUploadError(f"文件上传超时（已重试{retries}次）: {str(e)}")
        except RequestException as e:
            last_exc = e
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"上传失败 (attempt {attempt}/{retries}): HTTP {e.response.status_code}")
                logger.error(f"  响应头: {dict(e.response.headers)}")
                logger.error(f"  响应内容: {e.response.text[:500] if e.response.text else '(empty)'}")
            else:
                logger.error(f"上传失败 (attempt {attempt}/{retries}): {e}")
            if attempt < retries:
                wait = backoff_factor * (2 ** (attempt - 1))
                logger.warning(f"  {wait}s 后重试...")
                time.sleep(wait)
            else:
                raise AGCUploadError(f"文件上传失败（已重试{retries}次）: {str(e)}")
    raise AGCUploadError(f"文件上传失败: {last_exc}")


def upload_generated_podcast(
    output_path: str,
    storage_url: Optional[str] = None,
    bucket: Optional[str] = None,
    object_name: Optional[str] = None,
    domain: Optional[str] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    product_id: Optional[str] = None,
    # 注意：上传时使用的client_id可能与获取token时不同
    upload_client_id: Optional[str] = None,
) -> Dict[str, Any]:
    """高层封装：读取配置、获取 token、上传文件，返回结果字典

    优先级：函数参数 > 环境变量 > 仓库 agc-apiclient-*.json
    
    注意：根据Java参考代码，获取token和上传可能使用不同的client_id：
    - token_client_id: 用于获取token的client_id
    - upload_client_id: 用于上传时的client_id（如果未提供，则使用token_client_id）
    """
    # 从环境变量读取（可覆盖）
    storage_url = storage_url or os.getenv('AGC_STORAGE_URL')
    bucket = bucket or os.getenv('AGC_BUCKET')
    domain = domain or os.getenv('AGC_DOMAIN', 'connect-api.cloud.huawei.com')
    token_client_id = client_id or os.getenv('AGC_CLIENT_ID')
    client_secret = client_secret or os.getenv('AGC_CLIENT_SECRET')
    product_id = product_id or os.getenv('AGC_PRODUCT_ID')
    # 上传时使用的client_id（如果未指定，使用token_client_id）
    upload_client_id = upload_client_id or token_client_id

    # 如果缺少 client_id/secret，尝试从文件读取
    if not token_client_id or not client_secret:
        cfg = _find_agc_client_json()
        if cfg:
            cred = _load_agc_credentials_from_file(cfg)
            token_client_id = token_client_id or cred.get('client_id')
            client_secret = client_secret or cred.get('client_secret')
            product_id = product_id or cred.get('project_id')
            # 如果未指定upload_client_id，使用从文件读取的client_id
            if not upload_client_id:
                upload_client_id = token_client_id

    if not storage_url or not bucket:
        raise ValueError('需要提供 storage_url 和 bucket （参数或环境变量 AGC_STORAGE_URL/AGC_BUCKET）')

    if not token_client_id or not client_secret:
        raise ValueError('需要提供 client_id 和 client_secret （参数、环境变量或 agc-apiclient-*.json 文件）')

    # 默认 object_name 使用 POSIX 风格路径，避免 windows 反斜杠
    object_name = object_name or ('outputs/podcasts/' + os.path.basename(output_path))

    logger.info(f"准备上传文件: {output_path}")
    logger.info(f"  Token client_id: {'已设置' if token_client_id else '未设置'}")
    logger.info(f"  上传 client_id: {'已设置' if upload_client_id else '未设置'}")
    logger.info(f"  product_id: {'已设置' if product_id else '未设置'}")

    # 获取 token（使用token_client_id和client_secret）
    token = get_agc_token(domain, token_client_id, client_secret)

    # 上传（使用upload_client_id，可能与token_client_id不同）
    resp = upload_file_to_agc(storage_url, bucket, object_name, output_path,
                              client_id=upload_client_id, product_id=product_id or '', token=token)

    return {
        'status': 'uploaded',
        'bucket': bucket,
        'object': object_name,
        'http_status': resp.status_code,
        'response_text': resp.text
    }


def download_file_from_agc(storage_url: str, bucket: str, object_name: str, output_path: str,
                           client_id: str, product_id: str, token: str, timeout: int = 300) -> requests.Response:
    """从 AGC 存储下载文件

    Args:
        storage_url: 基础存储 URL，例如 https://ops-server-drcn.agcstorage.link/v0/
        bucket: 存储实例名
        object_name: 要下载的文件路径/文件名，例如 outputs/podcasts/podcast.wav
        output_path: 本地保存文件路径
        client_id: AGC API client_id（header）
        product_id: AGC 项目 ID（header productId）
        token: access_token
        timeout: 超时时间（秒）

    Returns:
        requests.Response
    """
    if not storage_url.endswith('/'):
        storage_url = storage_url + '/'

    url = f"{storage_url}{bucket}/{object_name}"

    headers = {
        'productId': product_id or '',
        'client_id': client_id,
        'Authorization': f'Bearer {token}',
    }

    logger.info(f"从 AGC 下载文件: {url}")
    logger.info(f"  保存到: {output_path}")
    logger.info(f"  Headers: productId={'已设置' if product_id else '未设置'}, client_id={'已设置' if client_id else '未设置'}, Authorization={'已设置' if token else '未设置'}")

    # 确保输出目录存在
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"创建输出目录: {output_dir}")

    # 使用Session和连接池
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=10,
        pool_maxsize=20,
        max_retries=0
    )
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    try:
        download_start = time.time()
        
        # 使用GET请求，流式下载
        resp = session.get(
            url,
            headers=headers,
            timeout=timeout,
            stream=True  # 启用流式下载
        )
        
        resp.raise_for_status()
        
        # 使用1024字节缓冲区，将响应流写入本地文件
        file_size = 0
        buffer_size = 1024
        
        with open(output_path, 'wb') as output_stream:
            for chunk in resp.iter_content(chunk_size=buffer_size):
                if chunk:
                    output_stream.write(chunk)
                    file_size += len(chunk)
        
        
        download_time = time.time() - download_start
        download_speed = (file_size / (1024 * 1024)) / download_time if download_time > 0 else 0
        
        logger.info(f"下载成功！")
        logger.info(f"  文件大小: {file_size} bytes ({file_size / (1024 * 1024):.2f} MB)")
        logger.info(f"  耗时: {download_time:.2f}秒, 速度: {download_speed:.2f} MB/s")
        logger.info(f"  保存路径: {output_path}")
        
        return resp
    finally:
        session.close()


def download_generated_podcast(
    object_name: str,
    output_path: str,
    storage_url: Optional[str] = None,
    bucket: Optional[str] = None,
    domain: Optional[str] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    product_id: Optional[str] = None,
    download_client_id: Optional[str] = None,
) -> Dict[str, Any]:
    """高层封装：读取配置、获取 token、下载文件，返回结果字典

    优先级：函数参数 > 环境变量 > 仓库 agc-apiclient-*.json
    
    Args:
        object_name: 要下载的文件路径/文件名，例如 outputs/podcasts/podcast.wav
        output_path: 本地保存文件路径
        storage_url: 存储URL（可选）
        bucket: 存储实例名（可选）
        domain: AGC域名（可选）
        client_id: 客户端ID（可选）
        client_secret: 客户端密钥（可选）
        product_id: 项目ID（可选）
        download_client_id: 下载时使用的client_id（可选，如果未提供则使用token_client_id）

    Returns:
        结果字典
    """
    # 从环境变量读取（可覆盖）
    storage_url = storage_url or os.getenv('AGC_STORAGE_URL')
    bucket = bucket or os.getenv('AGC_BUCKET')
    domain = domain or os.getenv('AGC_DOMAIN', 'connect-api.cloud.huawei.com')
    token_client_id = client_id or os.getenv('AGC_CLIENT_ID')
    client_secret = client_secret or os.getenv('AGC_CLIENT_SECRET')
    product_id = product_id or os.getenv('AGC_PRODUCT_ID')
    # 下载时使用的client_id（如果未指定，使用token_client_id）
    download_client_id = download_client_id or token_client_id

    # 如果缺少 client_id/secret，尝试从文件读取
    if not token_client_id or not client_secret:
        cfg = _find_agc_client_json()
        if cfg:
            cred = _load_agc_credentials_from_file(cfg)
            token_client_id = token_client_id or cred.get('client_id')
            client_secret = client_secret or cred.get('client_secret')
            product_id = product_id or cred.get('project_id')
            # 如果未指定download_client_id，使用从文件读取的client_id
            if not download_client_id:
                download_client_id = token_client_id

    if not storage_url or not bucket:
        raise ValueError('需要提供 storage_url 和 bucket （参数或环境变量 AGC_STORAGE_URL/AGC_BUCKET）')

    if not token_client_id or not client_secret:
        raise ValueError('需要提供 client_id 和 client_secret （参数、环境变量或 agc-apiclient-*.json 文件）')

    if not object_name:
        raise ValueError('需要提供 object_name（要下载的文件路径/文件名）')

    if not output_path:
        raise ValueError('需要提供 output_path（本地保存文件路径）')

    logger.info(f"准备下载文件: {object_name}")
    logger.info(f"  Token client_id: {'已设置' if token_client_id else '未设置'}")
    logger.info(f"  下载 client_id: {'已设置' if download_client_id else '未设置'}")
    logger.info(f"  product_id: {'已设置' if product_id else '未设置'}")

    # 获取 token（使用token_client_id和client_secret）
    token = get_agc_token(domain, token_client_id, client_secret)

    # 下载（使用download_client_id，可能与token_client_id不同）
    resp = download_file_from_agc(storage_url, bucket, object_name, output_path,
                                  client_id=download_client_id, product_id=product_id or '', token=token)

    return {
        'status': 'downloaded',
        'bucket': bucket,
        'object': object_name,
        'output_path': output_path,
        'http_status': resp.status_code,
    }


if __name__ == '__main__':
    # 简单的脚本入口（方便在服务端直接运行），从环境或参数读取
    import argparse

    parser = argparse.ArgumentParser(description='Upload/Download files to/from Huawei AGC Storage')
    subparsers = parser.add_subparsers(dest='action', help='操作类型')
    
    # 上传子命令
    upload_parser = subparsers.add_parser('upload', help='上传文件到AGC存储')
    upload_parser.add_argument('--output-path', required=True, help='本地文件路径')
    upload_parser.add_argument('--storage-url', required=False, help='AGC storage base URL')
    upload_parser.add_argument('--bucket', required=False, help='AGC bucket name')
    upload_parser.add_argument('--object-name', required=False, help='目标 object name in bucket')
    upload_parser.add_argument('--domain', required=False, help='AGC domain for token')
    upload_parser.add_argument('--client-id', required=False)
    upload_parser.add_argument('--client-secret', required=False)
    upload_parser.add_argument('--product-id', required=False)
    
    # 下载子命令
    download_parser = subparsers.add_parser('download', help='从AGC存储下载文件')
    download_parser.add_argument('--object-name', required=True, help='要下载的文件路径/文件名')
    download_parser.add_argument('--output-path', required=True, help='本地保存文件路径')
    download_parser.add_argument('--storage-url', required=False, help='AGC storage base URL')
    download_parser.add_argument('--bucket', required=False, help='AGC bucket name')
    download_parser.add_argument('--domain', required=False, help='AGC domain for token')
    download_parser.add_argument('--client-id', required=False)
    download_parser.add_argument('--client-secret', required=False)
    download_parser.add_argument('--product-id', required=False)

    args = parser.parse_args()

    if args.action == 'upload':
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
        print(res)
    elif args.action == 'download':
        res = download_generated_podcast(
            object_name=args.object_name,
            output_path=args.output_path,
            storage_url=args.storage_url,
            bucket=args.bucket,
            domain=args.domain,
            client_id=args.client_id,
            client_secret=args.client_secret,
            product_id=args.product_id,
        )
        print(res)
    else:
        parser.print_help()
