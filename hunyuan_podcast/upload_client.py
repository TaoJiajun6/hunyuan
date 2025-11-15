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

    # 注意：Headers顺序和Java参考代码保持一致
    headers = {
        'productId': product_id or '',
        'client_id': client_id,
        'Authorization': f'Bearer {token}',
        'X-Agc-File-Size': str(file_size),
        'Content-Type': content_type,
        'Connection': 'keep-alive',  # 保持连接，提高上传速度
        'Cache-Control': 'no-cache'  # 禁用缓存
    }
    # 注意：Java参考代码中没有X-Agc-Content-Type，只有Content-Type

    logger.info(f"上传到 AGC: {url}")
    logger.info(f"  文件大小: {file_size} bytes ({file_size / (1024 * 1024):.2f} MB)")
    logger.info(f"  Content-Type: {content_type}")
    logger.info(f"  Headers: productId={'已设置' if product_id else '未设置'}, client_id={'已设置' if client_id else '未设置'}, Authorization={'已设置' if token else '未设置'}")

    last_exc = None
    retries = 3
    backoff_factor = 0.5
    current_timeout = timeout  # 当前使用的超时时间，重试时会增加
    
    # 根据文件大小动态调整超时时间（在循环外计算，避免重复计算）
    file_size_mb = file_size / (1024 * 1024)
    # 对于大文件（几MB到几十MB），假设最小上传速度为0.2 MB/s（比0.1 MB/s更合理）
    # 这样可以减少不必要的超时时间，同时仍为慢速网络预留足够时间
    min_upload_speed_mbps = 0.2  # 最小上传速度（MB/s），适合大文件
    # 计算所需时间：文件大小(MB) / 最小速度(MB/s) + 缓冲时间
    calculated_timeout = int((file_size_mb / min_upload_speed_mbps) + 120)  # 至少120秒缓冲
    # 使用传入的timeout和计算出的timeout中的较大值，但不超过1800秒（30分钟）
    base_read_timeout = max(timeout, min(calculated_timeout, 1800))
    connect_timeout = 15  # 连接超时15秒
    
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
                # 根据文件大小动态调整chunk_size：大文件使用更大的chunk以提高上传速度
                # 对于几MB到几十MB的文件，使用更大的chunk_size可以显著提高上传速度
                if file_size_mb > 20:
                    chunk_size = 2 * 1024 * 1024  # 2MB chunks，超大文件（>20MB）
                elif file_size_mb > 10:
                    chunk_size = 1024 * 1024  # 1MB chunks，大文件（10-20MB）
                elif file_size_mb > 5:
                    chunk_size = 512 * 1024  # 512KB chunks，中等文件（5-10MB）
                else:
                    chunk_size = 256 * 1024  # 256KB chunks，小文件（<5MB）
                
                logger.info(f"使用chunk_size: {chunk_size / 1024:.0f} KB (文件大小: {file_size_mb:.2f} MB)")
                upload_start = time.time()
                
                def file_stream():
                    """生成器函数，用于流式读取文件"""
                    try:
                        with open(file_path, 'rb') as f:
                            bytes_sent = 0
                            last_log_time = upload_start
                            while True:
                                chunk = f.read(chunk_size)
                                if not chunk:
                                    break
                                bytes_sent += len(chunk)
                                # 每2秒记录一次进度（避免日志过多，同时提供实时反馈）
                                current_time = time.time()
                                if current_time - last_log_time >= 2.0:
                                    elapsed = current_time - upload_start
                                    if elapsed > 0:
                                        speed = (bytes_sent / (1024 * 1024)) / elapsed
                                        progress = (bytes_sent / file_size) * 100
                                        logger.info(f"上传进度: {progress:.1f}% ({bytes_sent / (1024 * 1024):.2f}/{file_size_mb:.2f} MB), 速度: {speed:.2f} MB/s")
                                    last_log_time = current_time
                                yield chunk
                    except Exception as e:
                        logger.error(f"读取文件流失败: {str(e)}")
                        raise
                
                resp = session.put(
                    url, 
                    data=file_stream(),  # 使用生成器进行流式上传
                    headers=headers, 
                    timeout=(connect_timeout, read_timeout),  # (连接超时, 读取超时)
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
    # 注意：上传时使用的client_id可能与获取token时不同（参考Java代码）
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


if __name__ == '__main__':
    # 简单的脚本入口（方便在服务端直接运行），从环境或参数读取
    import argparse

    parser = argparse.ArgumentParser(description='Upload generated podcast to Huawei AGC')
    parser.add_argument('--output-path', required=True, help='本地文件路径')
    parser.add_argument('--storage-url', required=False, help='AGC storage base URL')
    parser.add_argument('--bucket', required=False, help='AGC bucket name')
    parser.add_argument('--object-name', required=False, help='目标 object name in bucket')
    parser.add_argument('--domain', required=False, help='AGC domain for token')
    parser.add_argument('--client-id', required=False)
    parser.add_argument('--client-secret', required=False)
    parser.add_argument('--product-id', required=False)

    args = parser.parse_args()

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
