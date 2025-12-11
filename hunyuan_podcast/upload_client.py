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

# 配置日志（支持文件导出）
try:
    from .log_config import setup_logging
    # 只在第一次导入时配置日志（避免重复配置）
    if not logging.getLogger().handlers:
        setup_logging(log_file="upload_client.log")
except ImportError:
    # 如果log_config模块不存在，使用基本配置
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


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
                  backoff_factor: float = 0.5) -> tuple[str, int]:
    """获取 AGC access_token（带缓存与重试）

    返回 (access_token, expires_in) 元组。
    使用 module-level 缓存避免频繁获取。
    
    Returns:
        tuple[str, int]: (access_token, expires_in) 元组，expires_in 单位为秒
    """
    if not client_id or not client_secret:
        raise AGCUploadError('缺少 client_id 或 client_secret，无法获取 token')

    # 根据官方文档，Token 获取接口必须使用 connect-drcn.dbankcloud.cn
    # 如果传入的是其他域名，自动修正（用于缓存key）
    token_domain_for_cache = domain
    if domain == 'connect-api.cloud.huawei.com':
        token_domain_for_cache = 'connect-drcn.dbankcloud.cn'
    
    cache_key = f"{token_domain_for_cache}:{client_id}"
    cached = _TOKEN_CACHE.get(cache_key)
    now = time.time()
    if cached and cached.get('expires_at', 0) > now + 5:
        # 计算剩余的过期时间
        remaining_expires = int(cached.get('expires_at', 0) - now)
        return (cached['token'], remaining_expires if remaining_expires > 0 else 3600)

    # 根据官方文档，Token 获取接口必须使用 connect-drcn.dbankcloud.cn
    # 如果传入的是其他域名，自动修正
    token_domain = domain
    if domain == 'connect-api.cloud.huawei.com':
        logger.warning(f"检测到域名 {domain}，Token 获取需要使用 connect-drcn.dbankcloud.cn，已自动修正")
        token_domain = 'connect-drcn.dbankcloud.cn'
    
    # 根据官方文档，URL是 /agc/apigw/oauth2/v1/token
    url = f"https://{token_domain}/agc/apigw/oauth2/v1/token"
    payload = {
        'useJwt': '1',  # 固定值，表示使用JWT
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
            return (token, expires_in)
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
    
    # 移除重试次数限制，持续重试直到成功
    # 对于慢速网络，上传可能需要很长时间，不应该设置重试次数限制
    retries = float('inf')  # 无限重试，直到成功
    backoff_factor = 0.5
    
    # 移除超时限制，允许上传持续进行直到完成
    # 对于慢速网络，上传可能需要很长时间，不应该设置超时限制
    connect_timeout = 30  # 连接超时30秒（仅用于建立连接）
    read_timeout = None  # 读取/写入超时设置为None，表示无超时限制
    
    attempt = 0
    while True:
        attempt += 1
        try:
            logger.info(f"上传尝试 {attempt}: 连接超时={connect_timeout}秒, 读取超时=无限制 (文件大小: {file_size_mb:.2f} MB)")
            
            # 优化上传：使用Session和连接池（每次重试创建新的session）
            # 在socket层面禁用超时，确保写入操作不会中断
            import socket
            from urllib3.util.connection import create_connection
            
            # 保存原始的create_connection函数
            _original_create_connection = create_connection
            
            def create_connection_without_timeout(address, *args, **kwargs):
                """创建没有超时的socket连接，并优化TCP参数以提高上传速度"""
                sock = _original_create_connection(address, *args, **kwargs)
                try:
                    # 禁用socket超时
                    sock.settimeout(None)
                    # 优化TCP参数以提高上传速度
                    # TCP_NODELAY: 禁用Nagle算法，减少延迟，提高小数据包传输速度
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    # 增大发送缓冲区，提高大文件上传速度
                    # 默认通常是64KB-256KB，我们设置为1MB
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024 * 1024)
                    # 增大接收缓冲区
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024)
                except Exception as e:
                    logger.debug(f"设置socket参数失败（不影响功能）: {e}")
                return sock
            
            # 临时替换urllib3的create_connection函数
            import urllib3.util.connection
            urllib3.util.connection.create_connection = create_connection_without_timeout
            
            session = requests.Session()
            # 优化连接池设置以提高性能
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=20,  # 增加连接池大小
                pool_maxsize=50,  # 增加最大连接数
                max_retries=0  # 禁用urllib3的重试，我们自己处理
            )
            session.mount('http://', adapter)
            session.mount('https://', adapter)
            
            try:
                upload_start = time.time()
                
                # AGC服务器要求必须使用Content-Length头，不能使用Transfer-Encoding: chunked
                # 创建一个支持Content-Length的流式上传类
                # 这个类实现了__iter__和__len__，让requests使用Content-Length而不是chunked编码
                class FileStream:
                    """支持Content-Length的流式文件上传类"""
                    def __init__(self, file_path, chunk_size=1024 * 1024):
                        self.file_path = file_path
                        self.chunk_size = chunk_size
                        self.file_size = os.path.getsize(file_path)
                        self._file = None
                        self._bytes_sent = 0
                        self._last_log_time = upload_start
                    
                    def __len__(self):
                        """返回文件大小，让requests使用Content-Length"""
                        return self.file_size
                    
                    def __iter__(self):
                        """迭代器，分块读取文件"""
                        try:
                            self._file = open(self.file_path, 'rb')
                            while True:
                                chunk = self._file.read(self.chunk_size)
                                if not chunk:
                                    break
                                self._bytes_sent += len(chunk)
                                # 每2秒记录一次进度
                                current_time = time.time()
                                if current_time - self._last_log_time >= 2.0:
                                    elapsed = current_time - upload_start
                                    if elapsed > 0:
                                        speed = (self._bytes_sent / (1024 * 1024)) / elapsed
                                        progress = (self._bytes_sent / self.file_size) * 100
                                        file_size_mb = self.file_size / (1024 * 1024)
                                        logger.info(f"上传进度: {progress:.1f}% ({self._bytes_sent / (1024 * 1024):.2f}/{file_size_mb:.2f} MB), 速度: {speed:.2f} MB/s")
                                    self._last_log_time = current_time
                                yield chunk
                        finally:
                            if self._file:
                                self._file.close()
                
                # 优化chunk_size以提高上传速度
                # 在保证不超时的前提下，使用更大的chunk可以减少网络往返次数，提高速度
                # 由于已经禁用了socket超时，可以使用更大的chunk
                # 针对1MB以上的文件（常见情况），使用更大的chunk_size以提高速度
                if file_size_mb > 50:
                    chunk_size = 4 * 1024 * 1024  # 4MB chunks，超大文件（最大化速度）
                elif file_size_mb > 20:
                    chunk_size = 2 * 1024 * 1024  # 2MB chunks，大文件
                elif file_size_mb > 5:
                    chunk_size = 1024 * 1024  # 1MB chunks，中等文件
                elif file_size_mb > 1:
                    chunk_size = 512 * 1024  # 512KB chunks，1MB以上的文件
                else:
                    chunk_size = 256 * 1024  # 256KB chunks，小于1MB的小文件
                
                logger.info(f"流式上传模式（文件大小: {file_size_mb:.2f} MB, chunk_size: {chunk_size / 1024:.0f} KB）")
                
                file_stream = FileStream(file_path, chunk_size)
                
                resp = session.put(
                    url,
                    data=file_stream,  # 使用支持Content-Length的流式对象
                    headers=headers,
                    timeout=(connect_timeout, read_timeout),
                    allow_redirects=True
                )
            finally:
                session.close()
                # 恢复原始的create_connection函数（在session关闭后）
                urllib3.util.connection.create_connection = _original_create_connection
            
            upload_time = time.time() - upload_start
            upload_speed = (file_size / (1024 * 1024)) / upload_time if upload_time > 0 else 0
            
            logger.info(f"上传响应: status_code={resp.status_code}, 耗时: {upload_time:.2f}秒, 速度: {upload_speed:.2f} MB/s")
            logger.info(f"  响应头: {dict(resp.headers)}")
            if resp.text:
                logger.info(f"上传响应内容: {resp.text[:500]}")
            
            # 如果状态码是成功的（2xx），即使之前有超时警告也认为成功
            if 200 <= resp.status_code < 300:
                logger.info(f"上传成功！")
                return resp
            else:
                # 对于客户端错误（4xx，如403认证失败），直接抛出异常，不重试
                # 因为认证问题不会因为重试而解决
                if 400 <= resp.status_code < 500:
                    error_msg = f"上传失败: HTTP {resp.status_code}"
                    if resp.text:
                        error_msg += f" - {resp.text[:200]}"
                    logger.error(error_msg)
                    raise AGCUploadError(error_msg)
                # 对于服务器错误（5xx），也直接抛出异常，不重试
                # 等待一次性上传完毕，不进行重试
                resp.raise_for_status()
                return resp
        except requests.exceptions.Timeout as e:
            # 超时错误，直接抛出异常，不重试
            # 等待一次性上传完毕，不进行重试
            is_write_timeout = "write operation timed out" in str(e).lower() or "timed out" in str(e).lower()
            logger.error(f"上传超时: {str(e)}")
            logger.error(f"  文件大小: {file_size_mb:.2f} MB")
            logger.error(f"  超时设置: 连接={connect_timeout}秒, 读取={read_timeout}秒")
            if is_write_timeout:
                logger.warning(f"  检测到写入超时")
            raise AGCUploadError(f"上传超时: {e}") from e
        except requests.exceptions.HTTPError as e:
            # HTTP错误（4xx/5xx），直接抛出异常，不重试
            # 等待一次性上传完毕，不进行重试
            if hasattr(e, 'response') and e.response is not None:
                status_code = e.response.status_code
                logger.error(f"上传失败: HTTP {status_code}")
                logger.error(f"  响应头: {dict(e.response.headers)}")
                logger.error(f"  响应内容: {e.response.text[:500] if e.response.text else '(empty)'}")
                error_msg = f"上传失败: HTTP {status_code}"
                if e.response.text:
                    error_msg += f" - {e.response.text[:200]}"
                raise AGCUploadError(error_msg) from e
            else:
                raise AGCUploadError(f"上传失败: {e}") from e
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as e:
            # 对于连接错误，也直接抛出异常，不重试
            # 等待一次性上传完毕，不进行重试
            error_str = str(e).lower()
            logger.error(f"上传失败: {e}")
            if "write operation timed out" in error_str or "connection aborted" in error_str:
                logger.warning(f"  检测到写入超时或连接中断")
            raise AGCUploadError(f"上传失败: {e}") from e
        except Exception as e:
            # 捕获其他未预期的异常，直接抛出，不重试
            # 等待一次性上传完毕，不进行重试
            logger.error(f"上传出现未预期错误: {e}")
            raise AGCUploadError(f"上传失败: {e}") from e


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
    token, _ = get_agc_token(domain, token_client_id, client_secret)

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
    token, _ = get_agc_token(domain, token_client_id, client_secret)

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
