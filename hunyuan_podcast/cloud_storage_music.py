"""
云存储音乐访问模块
从华为AGC云存储读取音乐文件列表并下载
"""
import os
import re
import json
import requests
import tempfile
from typing import List, Optional, Dict
from .config import MUSIC_DIR

# 尝试导入上传客户端以获取token
try:
    from .upload_client import get_agc_token, _find_agc_client_json, _load_agc_credentials_from_file
    HAS_UPLOAD_CLIENT = True
except ImportError:
    HAS_UPLOAD_CLIENT = False


class CloudStorageMusicClient:
    """云存储音乐客户端"""
    
    def __init__(
        self,
        storage_url: Optional[str] = None,
        bucket: Optional[str] = None,
        music_path: str = "music/"
    ):
        """
        初始化云存储音乐客户端
        
        Args:
            storage_url: 云存储服务URL，如果为None则从环境变量读取
            bucket: 存储桶名称，如果为None则从环境变量读取
            music_path: 音乐文件夹路径，默认为 "music/"
        """
        self.storage_url = storage_url or os.getenv('AGC_STORAGE_URL', 'https://ops-server-drcn.agcstorage.link/v0/')
        self.bucket = bucket or os.getenv('AGC_BUCKET', 'podcasters-y0qig')
        self.music_path = music_path.rstrip('/') + '/' if music_path else "music/"
        
        # 确保URL以/结尾
        if not self.storage_url.endswith('/'):
            self.storage_url += '/'
        
        # 临时下载目录
        self.temp_dir = os.path.join(tempfile.gettempdir(), 'hunyuan_music_cache')
        os.makedirs(self.temp_dir, exist_ok=True)
        
        self._music_cache: Optional[List[Dict[str, str]]] = None
        
        # AGC认证信息（用于API调用）
        self.client_id = os.getenv('AGC_CLIENT_ID')
        self.client_secret = os.getenv('AGC_CLIENT_SECRET')
        self.product_id = os.getenv('AGC_PRODUCT_ID') or os.getenv('AGC_PRODUCT_ID')
        self.domain = os.getenv('AGC_DOMAIN', 'connect-api.cloud.huawei.com')
        
        # 如果没有从环境变量获取，尝试从文件读取
        if not self.client_id or not self.client_secret:
            agc_json_path = _find_agc_client_json() if HAS_UPLOAD_CLIENT else None
            if agc_json_path:
                creds = _load_agc_credentials_from_file(agc_json_path)
                self.client_id = self.client_id or creds.get('client_id')
                self.client_secret = self.client_secret or creds.get('client_secret')
                self.product_id = self.product_id or creds.get('project_id')
    
    def list_music_files(self, music_urls: Optional[List[str]] = None) -> List[Dict[str, str]]:
        """
        列出云存储中的音乐文件
        
        Args:
            music_urls: 可选的音乐文件URL列表，如果提供则使用这些URL
        
        Returns:
            音乐文件列表，每个元素包含 {'path': 本地路径, 'name': 文件名, 'style': 推断的风格, 'cloud_path': 云存储路径, 'url': 下载URL}
        """
        if self._music_cache is not None:
            print(f"使用缓存的音乐文件列表: {len(self._music_cache)} 个文件")
            return self._music_cache
        
        music_files = []
        
        # 如果提供了URL列表，使用这些URL
        if music_urls:
            print(f"从URL列表处理 {len(music_urls)} 个音乐文件")
            for url in music_urls:
                try:
                    # 从URL中提取文件名
                    filename = os.path.basename(url.split('?')[0])  # 移除查询参数
                    
                    # 提取云存储路径
                    cloud_path = self._extract_cloud_path_from_url(url)
                    
                    # 从文件名推断风格
                    style = self._infer_style_from_filename(filename)
                    
                    music_files.append({
                        'path': None,  # 稍后下载时填充
                        'name': filename,
                        'style': style,
                        'cloud_path': cloud_path,
                        'url': url
                    })
                    print(f"  - 添加音乐文件: {filename} (路径: {cloud_path})")
                except Exception as e:
                    print(f"处理音乐URL失败 {url}: {str(e)}")
            
            if music_files:
                self._music_cache = music_files
                print(f"✓ 从URL列表获取到 {len(music_files)} 个音乐文件")
                return music_files
        
        # 尝试从环境变量读取音乐URL列表
        music_urls_str = os.getenv('CLOUD_MUSIC_URLS')
        if music_urls_str:
            print(f"从环境变量 CLOUD_MUSIC_URLS 读取音乐文件列表")
            try:
                import json
                env_urls = json.loads(music_urls_str)
                if isinstance(env_urls, list):
                    return self.list_music_files(music_urls=env_urls)
            except json.JSONDecodeError:
                # 如果不是JSON，尝试按逗号分割
                env_urls = [url.strip() for url in music_urls_str.split(',') if url.strip()]
                if env_urls:
                    print(f"从环境变量解析到 {len(env_urls)} 个URL")
                    return self.list_music_files(music_urls=env_urls)
        
        # 尝试通过云存储API获取文件列表（需要认证）
        if HAS_UPLOAD_CLIENT and self.client_id and self.client_secret:
            try:
                print(f"尝试通过API获取云存储文件列表 (bucket: {self.bucket}, path: {self.music_path})")
                api_files = self._list_files_via_api()
                if api_files:
                    self._music_cache = api_files
                    print(f"✓ 通过API获取到 {len(api_files)} 个音乐文件")
                    return api_files
                else:
                    print(f"⚠️ API返回空文件列表")
            except RuntimeError as e:
                # RuntimeError表示API功能不可用，继续尝试其他方式
                print(f"⚠️ API列表功能不可用: {str(e)}")
                print(f"  将尝试其他方式获取文件列表")
            except Exception as e:
                print(f"⚠️ 通过API获取文件列表失败: {str(e)}")
                import traceback
                print(f"  错误详情: {traceback.format_exc()}")
                print(f"  将尝试其他方式获取文件列表")
        
        # 如果API获取失败，提示用户
        print("⚠️ 提示：云存储文件列表获取需要配置访问权限")
        print(f"   当前配置: bucket={self.bucket}, music_path={self.music_path}")
        if not HAS_UPLOAD_CLIENT:
            print("   缺少 upload_client 模块，无法使用API方式")
        elif not self.client_id or not self.client_secret:
            print("   缺少 AGC_CLIENT_ID 或 AGC_CLIENT_SECRET 环境变量")
        print("   建议：通过环境变量 CLOUD_MUSIC_URLS 提供音乐文件URL列表，或使用本地音乐文件")
        print("   格式: CLOUD_MUSIC_URLS='[\"url1\", \"url2\"]' 或 CLOUD_MUSIC_URLS='url1,url2'")
        return []
    
    def _extract_cloud_path_from_url(self, url: str) -> str:
        """
        从URL中提取云存储路径
        
        Args:
            url: 下载URL
        
        Returns:
            云存储路径（相对于bucket）
        """
        # 尝试从URL中提取路径
        # 格式：https://ops-server-drcn.agcstorage.link/v0/{bucket}/{path}
        try:
            # 查找 bucket 名称后的路径
            bucket_index = url.find(self.bucket)
            if bucket_index != -1:
                path_start = bucket_index + len(self.bucket) + 1
                path = url[path_start:].split('?')[0]  # 移除查询参数
                return path
        except:
            pass
        
        # 如果无法提取，返回文件名
        return os.path.basename(url.split('?')[0])
    
    def download_music_file(self, cloud_path: str) -> Optional[str]:
        """
        从云存储下载音乐文件到本地临时目录
        
        Args:
            cloud_path: 云存储文件路径（相对于bucket的路径）
        
        Returns:
            本地文件路径，如果下载失败则返回None
        """
        try:
            # 构建下载URL（根据华为AGC云存储API文档）
            # 格式：https://{domain}/{bucket_name}/{object_name}
            # 注意：storage_url已经包含了/v0/，所以不需要再加
            download_url = f"{self.storage_url}{self.bucket}/{cloud_path}"
            
            # 生成本地文件名
            filename = os.path.basename(cloud_path)
            local_path = os.path.join(self.temp_dir, filename)
            
            # 如果文件已存在，直接返回
            if os.path.exists(local_path):
                print(f"使用缓存的音乐文件: {local_path}")
                return local_path
            
            print(f"正在从云存储下载音乐文件: {download_url}")
            
            # 根据华为AGC云存储API文档，下载文件需要以下Header：
            # - Authorization: Bearer ${access_token} (必需)
            # - client_id (必需)
            # - productId (必需)
            headers = {
                'Content-Type': 'application/json'
            }
            
            if not HAS_UPLOAD_CLIENT or not self.client_id or not self.client_secret:
                print(f"  ✗ 缺少认证信息，无法下载")
                print(f"  请配置 AGC_CLIENT_ID, AGC_CLIENT_SECRET, AGC_PRODUCT_ID")
                return None
            
            try:
                # 获取access_token
                token = get_agc_token(
                    domain=self.domain,
                    client_id=self.client_id,
                    client_secret=self.client_secret
                )
                
                # 添加必需的Header（按照API文档要求）
                headers['Authorization'] = f'Bearer {token}'
                headers['client_id'] = self.client_id
                headers['productId'] = self.product_id or ''
                
            except Exception as e:
                print(f"  ✗ 获取token失败: {str(e)}")
                return None
            
            # 下载文件（使用流式下载）
            response = requests.get(download_url, timeout=60, stream=True, headers=headers)
            response.raise_for_status()
            
            # 检查Content-Length
            content_length = response.headers.get("content-length")
            if content_length:
                file_size = int(content_length)
                file_size_mb = file_size / (1024 * 1024)
                print(f"  文件大小: {file_size_mb:.2f} MB")
            
            # 流式下载
            downloaded_size = 0
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
            
            print(f"✓ 音乐文件下载完成: {local_path} ({downloaded_size / (1024 * 1024):.2f} MB)")
            return local_path
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                print(f"✗ 下载音乐文件失败: 403 Forbidden - 可能是云存储安全规则限制或认证失败")
                print(f"  请检查认证信息是否正确")
            elif e.response.status_code == 400:
                print(f"✗ 下载音乐文件失败: 400 Bad Request - URL格式可能不正确")
                print(f"  URL: {download_url}")
            else:
                print(f"✗ 下载音乐文件失败: HTTP {e.response.status_code} - {str(e)}")
            return None
        except Exception as e:
            print(f"✗ 下载音乐文件失败: {str(e)}")
            import traceback
            print(f"  错误详情: {traceback.format_exc()}")
            return None
    
    def get_music_by_url(self, music_url: str) -> Optional[str]:
        """
        通过下载URL获取音乐文件
        
        Args:
            music_url: 音乐文件的下载URL
        
        Returns:
            本地文件路径，如果下载失败则返回None
        """
        try:
            # 从URL中提取文件名
            filename = os.path.basename(music_url.split('?')[0])  # 移除查询参数
            local_path = os.path.join(self.temp_dir, filename)
            
            # 如果文件已存在，直接返回
            if os.path.exists(local_path):
                print(f"使用缓存的音乐文件: {local_path}")
                return local_path
            
            print(f"正在从URL下载音乐文件: {music_url}")
            
            # 根据华为AGC云存储API文档，下载文件需要以下Header：
            # - Authorization: Bearer ${access_token} (必需)
            # - client_id (必需)
            # - productId (必需)
            # URL格式：https://{domain}/{bucket_name}/{object_name}
            
            # 检查URL是否是华为AGC云存储的URL
            is_agc_url = 'agcstorage.link' in music_url or 'ops-server' in music_url
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Content-Type': 'application/json'
            }
            
            # 如果是AGC云存储URL，必须添加认证头
            if is_agc_url:
                if not HAS_UPLOAD_CLIENT or not self.client_id or not self.client_secret:
                    print(f"  ⚠️ AGC云存储URL需要认证，但缺少认证信息")
                    print(f"  请配置 AGC_CLIENT_ID, AGC_CLIENT_SECRET, AGC_PRODUCT_ID")
                    return None
                
                try:
                    # 获取access_token
                    token = get_agc_token(
                        domain=self.domain,
                        client_id=self.client_id,
                        client_secret=self.client_secret
                    )
                    
                    # 添加必需的Header（按照API文档要求）
                    headers['Authorization'] = f'Bearer {token}'
                    headers['client_id'] = self.client_id
                    headers['productId'] = self.product_id or ''
                    
                    print(f"  使用认证方式下载（client_id: {self.client_id[:8]}..., productId: {self.product_id or '(empty)'}）")
                except Exception as e:
                    print(f"  ✗ 获取token失败: {str(e)}")
                    return None
            else:
                # 非AGC URL，尝试添加认证（如果配置了）
                if HAS_UPLOAD_CLIENT and self.client_id and self.client_secret:
                    try:
                        token = get_agc_token(
                            domain=self.domain,
                            client_id=self.client_id,
                            client_secret=self.client_secret
                        )
                        headers['Authorization'] = f'Bearer {token}'
                        headers['productId'] = self.product_id or ''
                        headers['client_id'] = self.client_id
                    except Exception as e:
                        print(f"  获取token失败，使用无认证方式下载: {str(e)}")
            
            response = requests.get(music_url, timeout=60, stream=True, headers=headers)
            response.raise_for_status()
            
            # 检查Content-Length
            content_length = response.headers.get("content-length")
            if content_length:
                file_size = int(content_length)
                file_size_mb = file_size / (1024 * 1024)
                print(f"  文件大小: {file_size_mb:.2f} MB")
            
            # 流式下载
            downloaded_size = 0
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
            
            print(f"✓ 音乐文件下载完成: {local_path} ({downloaded_size / (1024 * 1024):.2f} MB)")
            return local_path
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                print(f"✗ 下载音乐文件失败: 403 Forbidden - 可能是云存储安全规则限制或需要认证")
                print(f"  请检查华为AGC云存储的安全规则配置，确保下载URL可以公开访问")
            elif e.response.status_code == 400:
                print(f"✗ 下载音乐文件失败: 400 Bad Request - URL格式可能不正确")
                print(f"  尝试通过getDownloadURL API获取正确的下载URL")
            else:
                print(f"✗ 下载音乐文件失败: HTTP {e.response.status_code} - {str(e)}")
            return None
        except Exception as e:
            print(f"✗ 从URL下载音乐文件失败: {str(e)}")
            import traceback
            print(f"  错误详情: {traceback.format_exc()}")
            return None
    
    def _list_files_via_api(self) -> List[Dict[str, str]]:
        """
        通过AGC REST API列出云存储中的文件
        
        Returns:
            音乐文件列表，每个元素包含 {'path': 本地路径, 'name': 文件名, 'style': 推断的风格, 'cloud_path': 云存储路径, 'url': 下载URL}
        """
        if not HAS_UPLOAD_CLIENT:
            raise RuntimeError("upload_client 模块不可用")
        
        if not self.client_id or not self.client_secret:
            raise RuntimeError("缺少 AGC_CLIENT_ID 或 AGC_CLIENT_SECRET")
        
        # 获取access_token
        print(f"正在获取AGC access_token...")
        token = get_agc_token(
            domain=self.domain,
            client_id=self.client_id,
            client_secret=self.client_secret
        )
        print(f"✓ Token获取成功")
        
        # 构建API请求URL
        # 尝试多种API格式：
        # 1. GET {storage_url}{bucket}?prefix={path}&list=true
        # 2. GET {storage_url}{bucket}/{path}?list=true
        # 3. GET {storage_url}{bucket}?list=true&prefix={path}
        
        # 规范化路径（移除开头的/，确保以/结尾）
        normalized_path = self.music_path.lstrip('/')
        if normalized_path and not normalized_path.endswith('/'):
            normalized_path += '/'
        
        # 尝试第一种格式：GET {storage_url}{bucket}?prefix={path}&list=true
        list_url = f"{self.storage_url}{self.bucket}"
        params = {}
        if normalized_path:
            params['prefix'] = normalized_path
        params['list'] = 'true'
        
        # 构建请求头
        headers = {
            'productId': self.product_id or '',
            'client_id': self.client_id,
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        print(f"正在请求文件列表: {list_url} (path: {normalized_path})")
        print(f"  查询参数: {params}")
        print(f"  请求头: productId={self.product_id or '(empty)'}, client_id={self.client_id[:8] if self.client_id else '(empty)'}...")
        
        # 发送GET请求
        try:
            response = requests.get(list_url, params=params, headers=headers, timeout=30)
            print(f"  HTTP状态码: {response.status_code}")
            print(f"  响应头 Content-Type: {response.headers.get('Content-Type', 'unknown')}")
            print(f"  响应内容长度: {len(response.text)} 字符")
            
            # 检查响应状态
            if response.status_code != 200:
                print(f"  ⚠️ API请求失败，状态码: {response.status_code}")
                print(f"  完整响应内容: {response.text[:1000]}")
                response.raise_for_status()
            
            # 打印响应内容预览（用于调试）
            print(f"  响应内容预览: {response.text[:500]}")
        except requests.exceptions.HTTPError as e:
            print(f"  ✗ API请求HTTP错误: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  响应状态码: {e.response.status_code}")
                print(f"  响应内容: {e.response.text[:1000]}")
            # 如果API不支持，尝试使用备选方案：直接构建已知文件的URL
            print(f"  ⚠️ API列表功能可能不可用，尝试使用备选方案...")
            raise RuntimeError(f"API列表功能不可用: HTTP {e.response.status_code if hasattr(e, 'response') and e.response else 'unknown'}")
        except requests.exceptions.RequestException as e:
            print(f"  ✗ API请求异常: {str(e)}")
            raise
        
        # 解析响应
        # 注意：AGC API可能返回XML或JSON格式，需要根据实际响应格式解析
        try:
            result = response.json()
            print(f"  ✓ 成功解析JSON响应")
            print(f"  响应结构: {list(result.keys())}")
        except json.JSONDecodeError:
            print(f"  ⚠️ 响应不是JSON格式，尝试解析为XML...")
            # 如果返回的是XML，尝试解析XML
            try:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.text)
                # 解析XML格式的响应（根据实际API响应格式调整）
                files = []
                for item in root.findall('.//Contents') or root.findall('.//File'):
                    key_elem = item.find('Key') or item.find('key')
                    if key_elem is not None:
                        file_path = key_elem.text
                        if file_path and file_path.startswith(normalized_path):
                            files.append(file_path)
                result = {'files': files, 'directories': []}
                print(f"  ✓ 成功解析XML响应，找到 {len(files)} 个文件")
            except Exception as e:
                print(f"  ✗ 解析响应失败: {str(e)}")
                print(f"  完整响应内容: {response.text}")
                raise
        
        # 处理文件列表
        music_files = []
        
        # 支持的音频格式
        audio_extensions = ['.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac']
        
        # 处理文件列表
        # 注意：HarmonyOS SDK返回的格式是 {files: [], directories: []}
        # 但REST API可能返回不同的格式，需要适配
        files_list = result.get('files', [])
        
        # 如果files_list为空，尝试其他可能的字段名
        if not files_list:
            # 尝试其他可能的字段名
            for key in ['items', 'objects', 'contents', 'fileList', 'keys']:
                if key in result:
                    files_list = result[key]
                    print(f"  使用字段 '{key}' 作为文件列表")
                    break
        
        print(f"  原始文件列表数量: {len(files_list) if isinstance(files_list, list) else 0}")
        
        if isinstance(files_list, list):
            for file_item in files_list:
                # 处理不同的响应格式
                # 可能是字符串（文件路径），也可能是对象（包含文件信息）
                if isinstance(file_item, str):
                    file_path = file_item
                elif isinstance(file_item, dict):
                    # 尝试从对象中提取路径
                    file_path = file_item.get('key') or file_item.get('path') or file_item.get('name') or file_item.get('filePath') or file_item.get('fileName')
                    if not file_path:
                        continue
                else:
                    continue
                
                # 确保是字符串类型
                if not isinstance(file_path, str):
                    continue
                
                # 规范化路径（移除开头的/）
                file_path = file_path.lstrip('/')
                
                # 检查是否在music目录下
                if normalized_path:
                    # normalized_path 已经是 music/ 格式（没有开头的/）
                    if not file_path.startswith(normalized_path):
                        # 如果文件路径是 music/filename.mp3 格式，需要检查
                        if not file_path.startswith(normalized_path.lstrip('/')):
                            continue
                
                # 检查是否是音频文件
                filename = os.path.basename(file_path)
                if not any(filename.lower().endswith(ext) for ext in audio_extensions):
                    continue
                
                # 直接构建下载URL（不再通过API获取）
                if file_path.startswith('music/'):
                    download_url = f"{self.storage_url}{self.bucket}/{file_path}"
                else:
                    download_url = f"{self.storage_url}{self.bucket}/{normalized_path}{filename}"
                
                # 从文件名推断风格
                style = self._infer_style_from_filename(filename)
                
                music_files.append({
                    'path': None,  # 稍后下载时填充
                    'name': filename,
                    'style': style,
                    'cloud_path': file_path,
                    'url': download_url
                })
                print(f"  ✓ 找到音乐文件: {filename} (路径: {file_path})")
        
        print(f"  处理后的音乐文件数量: {len(music_files)}")
        
        # 处理子目录（递归获取，但限制深度避免无限循环）
        directories = result.get('directories', [])
        if isinstance(directories, list) and directories:
            print(f"发现 {len(directories)} 个子目录，递归获取...")
            for subdir in directories:
                if not isinstance(subdir, str):
                    continue
                # 规范化子目录路径
                subdir_path = subdir.rstrip('/') + '/'
                if subdir_path.startswith(normalized_path):
                    # 递归获取子目录文件（使用新的客户端实例避免状态冲突）
                    sub_client = CloudStorageMusicClient(
                        storage_url=self.storage_url,
                        bucket=self.bucket,
                        music_path=subdir_path
                    )
                    sub_client.client_id = self.client_id
                    sub_client.client_secret = self.client_secret
                    sub_client.product_id = self.product_id
                    sub_client.domain = self.domain
                    try:
                        print(f"  正在获取子目录: {subdir_path}")
                        sub_files = sub_client._list_files_via_api()
                        print(f"  ✓ 从子目录 {subdir_path} 获取到 {len(sub_files)} 个音乐文件")
                        music_files.extend(sub_files)
                    except Exception as e:
                        print(f"  ✗ 获取子目录 {subdir_path} 失败: {str(e)}")
        
        # 如果files_list中包含子目录中的文件（扁平化列表），也需要处理
        # 有些API可能直接返回所有文件（包括子目录），而不是返回目录结构
        # 这种情况下，files_list中已经包含了所有文件，不需要递归
        
        print(f"✓ 总共从云存储 music/ 目录获取到 {len(music_files)} 个音乐文件（包括所有子目录）")
        return music_files
    
    def _get_download_url(self, cloud_path: str) -> Optional[str]:
        """
        通过AGC REST API获取文件的下载URL
        
        Args:
            cloud_path: 云存储文件路径（相对于bucket的路径）
        
        Returns:
            下载URL，如果获取失败则返回None
        """
        if not HAS_UPLOAD_CLIENT:
            return None
        
        if not self.client_id or not self.client_secret:
            return None
        
        try:
            # 获取access_token
            token = get_agc_token(
                domain=self.domain,
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            
            # 构建获取下载URL的API请求
            # 根据华为AGC云存储API，getDownloadURL接口格式可能为:
            # GET {storage_url}{bucket}/{path}?getDownloadURL=true
            # 或者 POST {storage_url}{bucket}/{path} 带特定参数
            
            # 尝试GET方式
            get_url = f"{self.storage_url}{self.bucket}/{cloud_path}"
            params = {'getDownloadURL': 'true'}
            
            headers = {
                'productId': self.product_id or '',
                'client_id': self.client_id,
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            print(f"  正在获取下载URL: {cloud_path}")
            response = requests.get(get_url, params=params, headers=headers, timeout=30)
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    # 尝试从响应中提取URL
                    download_url = result.get('downloadURL') or result.get('download_url') or result.get('url') or result.get('downloadUrl')
                    if download_url:
                        print(f"  ✓ 获取下载URL成功")
                        return download_url
                except json.JSONDecodeError:
                    # 如果响应是纯文本URL
                    if response.text.startswith('http://') or response.text.startswith('https://'):
                        print(f"  ✓ 获取下载URL成功（文本格式）")
                        return response.text.strip()
            
            # 如果GET方式失败，尝试POST方式
            post_url = f"{self.storage_url}{self.bucket}/{cloud_path}"
            post_data = {'action': 'getDownloadURL'}
            
            response = requests.post(post_url, json=post_data, headers=headers, timeout=30)
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    download_url = result.get('downloadURL') or result.get('download_url') or result.get('url') or result.get('downloadUrl')
                    if download_url:
                        print(f"  ✓ 获取下载URL成功（POST方式）")
                        return download_url
                except json.JSONDecodeError:
                    if response.text.startswith('http://') or response.text.startswith('https://'):
                        print(f"  ✓ 获取下载URL成功（POST方式，文本格式）")
                        return response.text.strip()
            
            print(f"  ⚠️ 获取下载URL失败: HTTP {response.status_code}")
            return None
            
        except Exception as e:
            print(f"  ⚠️ 获取下载URL异常: {str(e)}")
            return None
    
    def _infer_style_from_filename(self, filename: str) -> str:
        """
        从文件名推断音乐风格
        
        Args:
            filename: 文件名
        
        Returns:
            推断的风格名称
        """
        filename_lower = filename.lower()
        
        # 音乐风格关键词映射
        style_keywords = {
            "chill": ["轻松", "放松", "休闲", "chill", "lofi", "lo-fi"],
            "corporate": ["商务", "企业", "正式", "corporate", "business", "professional"],
            "interview": ["访谈", "采访", "对话", "interview", "podcast"],
            "jazz": ["爵士", "优雅", "时尚", "jazz", "stylish", "fashion"],
            "storytelling": ["故事", "叙述", "讲述", "storytelling", "narrative"],
            "upbeat": ["积极", "成功", "正能量", "upbeat", "successful", "positive"],
            "intro": ["开场", "介绍", "intro", "opening"]
        }
        
        # 检查每个风格的关键词
        for style, keywords in style_keywords.items():
            for keyword in keywords:
                if keyword.lower() in filename_lower:
                    return style
        
        # 默认风格
        return "general"


def get_cloud_music_client() -> Optional[CloudStorageMusicClient]:
    """
    获取云存储音乐客户端实例
    
    Returns:
        CloudStorageMusicClient实例，如果配置不完整则返回None
    """
    storage_url = os.getenv('AGC_STORAGE_URL')
    bucket = os.getenv('AGC_BUCKET')
    music_path = os.getenv('CLOUD_STORAGE_MUSIC_PATH', 'music/')
    
    if not storage_url or not bucket:
        return None
    
    client = CloudStorageMusicClient(storage_url=storage_url, bucket=bucket, music_path=music_path)
    
    # 如果提供了音乐URL列表，初始化文件列表
    music_urls_str = os.getenv('CLOUD_MUSIC_URLS')
    if music_urls_str:
        try:
            import json
            music_urls = json.loads(music_urls_str)
            if isinstance(music_urls, list):
                client.list_music_files(music_urls=music_urls)
        except:
            # 如果不是JSON，尝试按逗号分割
            music_urls = [url.strip() for url in music_urls_str.split(',') if url.strip()]
            if music_urls:
                client.list_music_files(music_urls=music_urls)
    
    return client

