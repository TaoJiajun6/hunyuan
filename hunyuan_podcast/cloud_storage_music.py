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
    
    def list_music_files(self, music_urls: Optional[List[str]] = None) -> List[Dict[str, str]]:
        """
        列出云存储中的音乐文件
        
        Args:
            music_urls: 可选的音乐文件URL列表，如果提供则使用这些URL
        
        Returns:
            音乐文件列表，每个元素包含 {'path': 本地路径, 'name': 文件名, 'style': 推断的风格, 'cloud_path': 云存储路径, 'url': 下载URL}
        """
        if self._music_cache is not None:
            return self._music_cache
        
        music_files = []
        
        # 如果提供了URL列表，使用这些URL
        if music_urls:
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
                except Exception as e:
                    print(f"处理音乐URL失败 {url}: {str(e)}")
            
            if music_files:
                self._music_cache = music_files
                print(f"从URL列表获取到 {len(music_files)} 个音乐文件")
                return music_files
        
        # 尝试通过云存储API获取文件列表（需要认证）
        # 注意：这可能需要配置访问令牌
        try:
            # 这里可以扩展为通过API获取文件列表
            # 目前先返回空列表，提示使用URL列表或本地文件
            print("提示：云存储文件列表获取需要配置访问权限")
            print("建议：通过环境变量 CLOUD_MUSIC_URLS 提供音乐文件URL列表，或使用本地音乐文件")
            return []
        except Exception as e:
            print(f"从云存储获取音乐文件列表失败: {str(e)}")
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
            # 构建下载URL
            # 格式：https://ops-server-drcn.agcstorage.link/v0/{bucket}/{path}
            download_url = f"{self.storage_url}{self.bucket}/{cloud_path}"
            
            # 生成本地文件名
            filename = os.path.basename(cloud_path)
            local_path = os.path.join(self.temp_dir, filename)
            
            # 如果文件已存在，直接返回
            if os.path.exists(local_path):
                print(f"使用缓存的音乐文件: {local_path}")
                return local_path
            
            print(f"正在从云存储下载音乐文件: {download_url}")
            
            # 下载文件
            response = requests.get(download_url, timeout=30)
            response.raise_for_status()
            
            # 保存到本地
            with open(local_path, 'wb') as f:
                f.write(response.content)
            
            print(f"音乐文件下载完成: {local_path}")
            return local_path
            
        except Exception as e:
            print(f"下载音乐文件失败: {str(e)}")
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
                return local_path
            
            print(f"正在从URL下载音乐文件: {music_url}")
            
            # 下载文件
            response = requests.get(music_url, timeout=30)
            response.raise_for_status()
            
            # 保存到本地
            with open(local_path, 'wb') as f:
                f.write(response.content)
            
            print(f"音乐文件下载完成: {local_path}")
            return local_path
            
        except Exception as e:
            print(f"从URL下载音乐文件失败: {str(e)}")
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

