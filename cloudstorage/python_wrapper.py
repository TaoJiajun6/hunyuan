"""
Python包装器 - 用于调用Node.js云存储服务
可以在Python代码中方便地使用Node.js SDK的功能
"""

import subprocess
import json
import os
import sys
from typing import Optional, Dict, Any, List


class CloudStorageClient:
    """华为AGC云存储客户端 - Python包装器"""
    
    def __init__(self, credential_path: Optional[str] = None, bucket_name: Optional[str] = None):
        """
        初始化云存储客户端
        
        Args:
            credential_path: AGC凭据文件路径（可选，会尝试自动查找）
            bucket_name: 存储桶名称（可选，默认使用环境变量或默认值）
        """
        self.script_path = os.path.join(os.path.dirname(__file__), 'cloudstorage_service.js')
        self.credential_path = credential_path
        self.bucket_name = bucket_name
        
        # 检查Node.js是否可用
        try:
            result = subprocess.run(['node', '--version'], capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError('Node.js未安装或不可用')
        except FileNotFoundError:
            raise RuntimeError('Node.js未安装，请先安装Node.js')
    
    def _run_command(self, command: str, *args) -> Dict[str, Any]:
        """
        运行Node.js命令
        
        Args:
            command: 命令名称（upload, download, list, delete等）
            *args: 命令参数
        
        Returns:
            命令执行结果
        """
        cmd = ['node', self.script_path, command] + list(args)
        
        # 设置环境变量
        env = os.environ.copy()
        if self.credential_path:
            env['AGC_CONFIG'] = self.credential_path
        if self.bucket_name:
            env['AGC_BUCKET'] = self.bucket_name
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=300  # 5分钟超时
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"命令执行失败: {result.stderr}")
            
            # 尝试从输出中提取JSON结果
            output_lines = result.stdout.strip().split('\n')
            for line in reversed(output_lines):
                line = line.strip()
                if line.startswith('{') or line.startswith('['):
                    try:
                        return json.loads(line)
                    except json.JSONDecodeError:
                        continue
            
            # 如果没有找到JSON，返回成功状态
            return {'success': True, 'message': result.stdout}
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("命令执行超时")
        except Exception as e:
            raise RuntimeError(f"执行命令时出错: {str(e)}")
    
    def upload_file(self, local_path: str, cloud_path: str) -> Dict[str, Any]:
        """
        上传文件到云存储
        
        Args:
            local_path: 本地文件路径
            cloud_path: 云存储路径
        
        Returns:
            上传结果，包含url等信息
        """
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"本地文件不存在: {local_path}")
        
        return self._run_command('upload', local_path, cloud_path)
    
    def download_file(self, cloud_path: str, local_path: str) -> Dict[str, Any]:
        """
        从云存储下载文件
        
        Args:
            cloud_path: 云存储路径
            local_path: 本地保存路径
        
        Returns:
            下载结果
        """
        # 确保本地目录存在
        local_dir = os.path.dirname(local_path)
        if local_dir and not os.path.exists(local_dir):
            os.makedirs(local_dir, exist_ok=True)
        
        return self._run_command('download', cloud_path, local_path)
    
    def upload_podcast(self, podcast_path: str, file_name: Optional[str] = None) -> Dict[str, Any]:
        """
        上传播客文件
        
        Args:
            podcast_path: 播客文件本地路径
            file_name: 文件名（可选，默认使用原文件名）
        
        Returns:
            上传结果
        """
        if not file_name:
            file_name = os.path.basename(podcast_path)
        cloud_path = f"outputs/podcasts/{file_name}"
        return self.upload_file(podcast_path, cloud_path)
    
    def upload_voice(self, voice_path: str, file_name: Optional[str] = None) -> Dict[str, Any]:
        """
        上传音色文件
        
        Args:
            voice_path: 音色文件本地路径
            file_name: 文件名（可选，默认使用原文件名）
        
        Returns:
            上传结果
        """
        if not file_name:
            file_name = os.path.basename(voice_path)
        cloud_path = f"voices/{file_name}"
        return self.upload_file(voice_path, cloud_path)
    
    def download_podcast(self, cloud_path: str, local_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        下载播客文件
        
        Args:
            cloud_path: 云存储路径（如 'outputs/podcasts/podcast.wav'）
            local_dir: 本地保存目录（可选，默认使用downloads/podcasts）
        
        Returns:
            下载结果
        """
        if not local_dir:
            local_dir = os.path.join(os.getcwd(), 'downloads', 'podcasts')
        
        file_name = os.path.basename(cloud_path)
        local_path = os.path.join(local_dir, file_name)
        return self.download_file(cloud_path, local_path)
    
    def download_voice(self, cloud_path: str, local_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        下载音色文件
        
        Args:
            cloud_path: 云存储路径（如 'voices/voice.wav'）
            local_dir: 本地保存目录（可选，默认使用downloads/voices）
        
        Returns:
            下载结果
        """
        if not local_dir:
            local_dir = os.path.join(os.getcwd(), 'downloads', 'voices')
        
        file_name = os.path.basename(cloud_path)
        local_path = os.path.join(local_dir, file_name)
        return self.download_file(cloud_path, local_path)
    
    def list_files(self, prefix: str = '') -> Dict[str, Any]:
        """
        列出文件
        
        Args:
            prefix: 路径前缀（如 'outputs/podcasts/'）
        
        Returns:
            文件列表
        """
        if prefix:
            return self._run_command('list', prefix)
        else:
            return self._run_command('list')
    
    def delete_file(self, cloud_path: str) -> Dict[str, Any]:
        """
        删除文件
        
        Args:
            cloud_path: 云存储路径
        
        Returns:
            删除结果
        """
        return self._run_command('delete', cloud_path)


# 使用示例
if __name__ == '__main__':
    # 创建客户端
    client = CloudStorageClient()
    
    # 示例：上传播客文件
    try:
        result = client.upload_podcast('./podcast.wav')
        print(f"上传成功: {result.get('url')}")
    except Exception as e:
        print(f"上传失败: {e}")
    
    # 示例：上传音色文件
    try:
        result = client.upload_voice('./voice.wav')
        print(f"上传成功: {result.get('url')}")
    except Exception as e:
        print(f"上传失败: {e}")
    
    # 示例：列出播客文件
    try:
        result = client.list_files('outputs/podcasts/')
        print(f"文件列表: {result}")
    except Exception as e:
        print(f"列出文件失败: {e}")

