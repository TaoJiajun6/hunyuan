"""
音乐自动选择模块
使用AI分析文本内容，自动从音乐库中选择合适的背景音乐
支持本地文件系统和云存储两种方式
"""
import os
import glob
import re
import json
from typing import List, Optional, Dict
from .config import MUSIC_DIR
from .api_client import get_client
from .cloud_storage_music import get_cloud_music_client, CloudStorageMusicClient

# 全局音乐文件列表缓存（跨实例共享）
_global_music_cache: Optional[List[Dict[str, str]]] = None
_global_music_cache_cloud_client_id: Optional[str] = None


class MusicSelector:
    """音乐选择器"""
    
    # 音乐风格关键词映射（基于文件名）
    MUSIC_STYLE_KEYWORDS = {
        "chill": ["轻松", "放松", "休闲", "chill", "lofi", "lo-fi"],
        "corporate": ["商务", "企业", "正式", "corporate", "business", "professional"],
        "interview": ["访谈", "采访", "对话", "interview", "podcast"],
        "jazz": ["爵士", "优雅", "时尚", "jazz", "stylish", "fashion"],
        "storytelling": ["故事", "叙述", "讲述", "storytelling", "narrative"],
        "upbeat": ["积极", "成功", "正能量", "upbeat", "successful", "positive"],
        "intro": ["开场", "介绍", "intro", "opening"]
    }
    
    # 播客分类到音乐子目录的映射（使用英文目录名）
    CATEGORY_TO_MUSIC_DIR = {
        "商业": "business",
        "科技": "technology",
        "财经": "finance",
        "新闻": "news",
        "影视": "film",
        "音乐": "music",
        "文化艺术": "culture",
        "历史": "history",
        "哲学思考": "philosophy",
        "自我成长": "self_improvement",
        "职场": "career",
        "学习": "learning",
        "教育育儿": "education",
        "情感恋爱": "relationship",
        "健康养生": "health",
        "旅游": "travel",
        "美食": "food",
        "生活方式": "lifestyle",
        "娱乐": "entertainment",
        "游戏电竞": "gaming",
        "体育": "sports",
        "时尚美妆": "fashion",
        "汽车": "automotive",
        "法律": "law",
        "宠物": "pets"
    }
    
    def __init__(self, music_dir: Optional[str] = None, use_cloud_storage: bool = False):
        """
        初始化音乐选择器
        
        Args:
            music_dir: 音乐文件夹路径，如果为None则使用默认路径
            use_cloud_storage: 是否优先使用云存储，默认False（优先使用本地文件）
        """
        self.music_dir = music_dir or MUSIC_DIR
        self.api_client = get_client()
        self._music_cache: Optional[List[Dict[str, str]]] = None
        self.use_cloud_storage = use_cloud_storage
        self.cloud_client: Optional[CloudStorageMusicClient] = None
        
        # 如果启用云存储，尝试初始化云存储客户端
        if self.use_cloud_storage:
            self.cloud_client = get_cloud_music_client()
            if self.cloud_client:
                print("已启用云存储音乐支持")
            else:
                print("云存储配置不完整，将使用本地音乐文件")
        else:
            print(f"使用本地音乐文件（目录: {self.music_dir}）")
    
    def scan_music_files(self) -> List[Dict[str, str]]:
        """
        扫描音乐文件夹，获取所有音乐文件
        优先使用本地文件，如果启用云存储且本地文件不可用则从云存储获取
        
        Returns:
            音乐文件列表，每个元素包含 {'path': 文件路径, 'name': 文件名, 'style': 推断的风格, 'cloud_path': 云存储路径（如果有）}
        """
        if self._music_cache is not None:
            return self._music_cache
        
        music_files = []
        
        # 优先使用本地文件系统
        if os.path.exists(self.music_dir):
            # 支持的音频格式
            audio_extensions = ['*.mp3', '*.wav', '*.m4a', '*.flac', '*.ogg']
            
            # 递归扫描所有子目录
            for ext in audio_extensions:
                # 使用 ** 递归匹配所有子目录
                pattern = os.path.join(self.music_dir, '**', ext)
                files = glob.glob(pattern, recursive=True)
                for file_path in files:
                    filename = os.path.basename(file_path)
                    # 从文件名推断风格
                    style = self._infer_style_from_filename(filename)
                    # 计算相对路径（相对于music_dir），用于匹配子目录
                    relative_path = os.path.relpath(file_path, self.music_dir)
                    music_files.append({
                        'path': file_path,
                        'name': filename,
                        'style': style,
                        'relative_path': relative_path  # 添加相对路径，用于子目录匹配
                    })
            
            if music_files:
                self._music_cache = music_files
                print(f"从本地扫描到 {len(music_files)} 个音乐文件（递归扫描子目录）")
                return music_files
        
        # 如果本地文件不可用且启用了云存储，尝试从云存储获取
        if self.cloud_client:
            try:
                print(f"=" * 60)
                print(f"🎵 正在从云存储获取音乐文件")
                print(f"  存储桶: {self.cloud_client.bucket}")
                print(f"  音乐路径: {self.cloud_client.music_path}")
                print(f"=" * 60)
                cloud_files = self.cloud_client.list_music_files()
                if cloud_files:
                    print(f"✓ 从云存储获取到 {len(cloud_files)} 个音乐文件")
                    # 显示一些示例文件路径，帮助用户确认
                    if len(cloud_files) > 0:
                        print(f"  示例文件路径:")
                        for i, music_info in enumerate(cloud_files[:5], 1):
                            cloud_path = music_info.get('cloud_path', music_info.get('name', 'unknown'))
                            print(f"    [{i}] {cloud_path}")
                        if len(cloud_files) > 5:
                            print(f"    ... 还有 {len(cloud_files) - 5} 个文件")
                    # 预下载所有云存储文件到本地缓存
                    downloaded_count = 0
                    for i, music_info in enumerate(cloud_files, 1):
                        if 'url' in music_info and music_info['url']:
                            print(f"  [{i}/{len(cloud_files)}] 下载音乐文件: {music_info.get('name', 'unknown')}")
                            local_path = self.cloud_client.get_music_by_url(music_info['url'])
                            if local_path:
                                music_info['path'] = local_path
                                downloaded_count += 1
                                print(f"    ✓ 下载成功: {local_path}")
                            else:
                                print(f"    ✗ 下载失败: {music_info['url']}")
                        elif 'cloud_path' in music_info and music_info['cloud_path']:
                            print(f"  [{i}/{len(cloud_files)}] 下载音乐文件: {music_info.get('name', 'unknown')}")
                            local_path = self.cloud_client.download_music_file(music_info['cloud_path'])
                            if local_path:
                                music_info['path'] = local_path
                                downloaded_count += 1
                                print(f"    ✓ 下载成功: {local_path}")
                            else:
                                print(f"    ✗ 下载失败: {music_info['cloud_path']}")
                    print(f"✓ 成功下载 {downloaded_count}/{len(cloud_files)} 个音乐文件到本地缓存")
                    self._music_cache = cloud_files
                    return cloud_files
                else:
                    print("⚠️ 云存储中没有找到音乐文件，将尝试使用本地文件")
            except Exception as e:
                import traceback
                print(f"✗ 从云存储获取音乐文件失败: {str(e)}")
                print(f"  错误详情: {traceback.format_exc()}")
                print("  将尝试使用本地文件")
        
        # 如果本地和云存储都不可用
        if not music_files:
            print(f"警告：音乐文件夹不存在: {self.music_dir}")
            if self.cloud_client:
                print(f"提示：请确保云存储中有 music/ 文件夹，或创建本地音乐目录: {self.music_dir}")
            else:
                print(f"提示：请创建本地音乐目录: {self.music_dir}")
        
        return music_files
    
    def _infer_style_from_filename(self, filename: str) -> str:
        """
        从文件名推断音乐风格
        
        Args:
            filename: 文件名
        
        Returns:
            推断的风格名称
        """
        filename_lower = filename.lower()
        
        # 检查每个风格的关键词
        for style, keywords in self.MUSIC_STYLE_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in filename_lower:
                    return style
        
        # 默认风格
        return "general"
    
    def scan_music_files_metadata_only(self) -> List[Dict[str, str]]:
        """
        扫描音乐文件，只获取元数据，不预下载文件
        优化性能：避免在扫描时下载所有文件，使用全局缓存
        
        Returns:
            音乐文件列表，每个元素包含 {'path': 文件路径（可能为None）, 'name': 文件名, 'style': 推断的风格, 'cloud_path': 云存储路径（如果有）, 'url': 下载URL（如果有）}
        """
        global _global_music_cache, _global_music_cache_cloud_client_id
        
        # 使用全局缓存（如果云存储客户端相同）
        cloud_client_id = None
        if self.cloud_client:
            cloud_client_id = f"{self.cloud_client.bucket}:{self.cloud_client.music_path}"
        
        if _global_music_cache is not None and _global_music_cache_cloud_client_id == cloud_client_id:
            print(f"使用全局缓存的音乐文件列表: {len(_global_music_cache)} 个文件")
            return _global_music_cache
        
        music_files = []
        
        # 优先使用本地文件系统
        if os.path.exists(self.music_dir):
            # 支持的音频格式
            audio_extensions = ['*.mp3', '*.wav', '*.m4a', '*.flac', '*.ogg']
            
            # 递归扫描所有子目录
            for ext in audio_extensions:
                # 使用 ** 递归匹配所有子目录
                pattern = os.path.join(self.music_dir, '**', ext)
                files = glob.glob(pattern, recursive=True)
                for file_path in files:
                    filename = os.path.basename(file_path)
                    # 从文件名推断风格
                    style = self._infer_style_from_filename(filename)
                    # 计算相对路径（相对于music_dir），用于匹配子目录
                    relative_path = os.path.relpath(file_path, self.music_dir)
                    music_files.append({
                        'path': file_path,
                        'name': filename,
                        'style': style,
                        'relative_path': relative_path  # 添加相对路径，用于子目录匹配
                    })
            
            if music_files:
                print(f"从本地扫描到 {len(music_files)} 个音乐文件（递归扫描子目录，仅元数据）")
                # 更新全局缓存
                _global_music_cache = music_files
                _global_music_cache_cloud_client_id = cloud_client_id
                return music_files
        
        # 如果本地文件不可用且启用了云存储，尝试从云存储获取（只获取列表，不下载）
        if self.cloud_client:
            try:
                print(f"=" * 60)
                print(f"🎵 正在从云存储获取音乐文件列表")
                print(f"  存储桶: {self.cloud_client.bucket}")
                print(f"  音乐路径: {self.cloud_client.music_path}")
                print(f"=" * 60)
                cloud_files = self.cloud_client.list_music_files()
                if cloud_files:
                    print(f"✓ 从云存储获取到 {len(cloud_files)} 个音乐文件（仅元数据，未下载）")
                    # 显示一些示例文件路径，帮助用户确认
                    if len(cloud_files) > 0:
                        print(f"  示例文件路径:")
                        for i, music_info in enumerate(cloud_files[:5], 1):
                            cloud_path = music_info.get('cloud_path', music_info.get('name', 'unknown'))
                            print(f"    [{i}] {cloud_path}")
                        if len(cloud_files) > 5:
                            print(f"    ... 还有 {len(cloud_files) - 5} 个文件")
                    # 更新全局缓存
                    _global_music_cache = cloud_files
                    _global_music_cache_cloud_client_id = cloud_client_id
                    # 不预下载，只返回元数据
                    return cloud_files
                else:
                    print("⚠️ 云存储中没有找到音乐文件，将尝试使用本地文件")
            except Exception as e:
                import traceback
                print(f"✗ 从云存储获取音乐文件失败: {str(e)}")
                print(f"  错误详情: {traceback.format_exc()}")
                print("  将尝试使用本地文件")
        
        # 如果本地和云存储都不可用
        if not music_files:
            print(f"警告：音乐文件夹不存在: {self.music_dir}")
            if self.cloud_client:
                print(f"提示：请确保云存储中有 music/ 文件夹，或创建本地音乐目录: {self.music_dir}")
            else:
                print(f"提示：请创建本地音乐目录: {self.music_dir}")
        
        # 更新全局缓存
        _global_music_cache = music_files
        _global_music_cache_cloud_client_id = cloud_client_id
        return music_files
    
    def _download_music_if_needed(self, music_info: Dict[str, str]) -> Optional[str]:
        """
        如果需要，下载音乐文件到本地
        
        Args:
            music_info: 音乐文件信息字典
        
        Returns:
            本地文件路径，如果下载失败则返回None
        """
        music_path = music_info.get('path')
        
        # 如果已经有本地路径且文件存在，直接使用
        if music_path and os.path.exists(music_path):
            return music_path
        
        # 如果有URL，尝试下载
        if 'url' in music_info and music_info['url'] and self.cloud_client:
            print(f"  正在下载选中的音乐文件: {music_info.get('name', 'unknown')}")
            local_path = self.cloud_client.get_music_by_url(music_info['url'])
            if local_path:
                print(f"    ✓ 下载成功: {local_path}")
                return local_path
            else:
                print(f"    ✗ 下载失败: {music_info.get('url')}")
                return None
        
        # 如果有云存储路径，尝试下载
        if 'cloud_path' in music_info and music_info['cloud_path'] and self.cloud_client:
            print(f"  正在下载选中的音乐文件: {music_info.get('name', 'unknown')}")
            cloud_path = music_info['cloud_path']
            local_path = self.cloud_client.download_music_file(cloud_path)
            if local_path:
                print(f"    ✓ 下载成功: {local_path}")
                return local_path
            else:
                print(f"    ✗ 下载失败: {cloud_path}")
                return None
        
        # 如果有本地路径但文件不存在
        if music_path:
            print(f"  警告：音乐文件不存在: {music_path}")
            return None
        
        return None
    
    def _match_music_directory(self, category: Optional[str], topic: Optional[str] = None) -> Optional[str]:
        """
        根据播客分类匹配音乐子目录
        
        Args:
            category: 播客分类
            topic: 播客主题（可选，用于辅助匹配）
        
        Returns:
            匹配的音乐子目录名称，如果未匹配则返回None
        """
        if not category:
            return None
        
        # 直接匹配
        if category in self.CATEGORY_TO_MUSIC_DIR:
            return self.CATEGORY_TO_MUSIC_DIR[category]
        
        # 模糊匹配：检查 category 是否包含在目录名称中，或目录名称是否包含 category
        category_lower = category.lower()
        for cat, dir_name in self.CATEGORY_TO_MUSIC_DIR.items():
            if category_lower in cat.lower() or cat.lower() in category_lower:
                return dir_name
        
        return None
    
    def _filter_music_by_directory(self, music_files: List[Dict[str, str]], directory_name: str) -> List[Dict[str, str]]:
        """
        根据子目录名称过滤音乐文件
        
        Args:
            music_files: 音乐文件列表
            directory_name: 子目录名称（英文，如 "sports"、"finance"、"business" 等）
        
        Returns:
            匹配的音乐文件列表
        """
        filtered = []
        # 使用小写进行匹配（英文目录名）
        directory_name_lower = directory_name.lower().strip()
        
        # 调试：打印匹配信息
        print(f"  匹配目录: '{directory_name}'")
        
        for music_info in music_files:
            # 优先检查相对路径（本地文件）
            relative_path = music_info.get('relative_path', '')
            if relative_path:
                # 提取目录部分：sports/music.mp3 -> sports
                path_parts = relative_path.split(os.sep)  # 使用os.sep支持跨平台
                if len(path_parts) >= 2:
                    subdir = path_parts[0]  # 第一个部分就是子目录名
                    subdir_lower = subdir.lower().strip()
                    
                    # 匹配逻辑：完全匹配或部分匹配（支持下划线和连字符）
                    is_match = (
                        directory_name_lower == subdir_lower or  # 完全匹配
                        directory_name_lower.replace('_', '-') == subdir_lower.replace('_', '-') or  # 支持下划线和连字符互换
                        directory_name_lower in subdir_lower or  # 包含匹配
                        subdir_lower in directory_name_lower  # 反向包含
                    )
                    
                    if is_match:
                        print(f"    ✓ 匹配: {relative_path} (子目录: '{subdir}')")
                        filtered.append(music_info)
                        continue
            
            # 检查云存储路径（格式：music/sports/music.mp3 或 music/business/music.mp3）
            cloud_path = music_info.get('cloud_path', '')
            if cloud_path:
                # 提取目录部分：music/sports/music.mp3 -> sports
                path_parts = cloud_path.split('/')
                if len(path_parts) >= 2:
                    # 跳过 "music" 部分，获取子目录
                    subdir = path_parts[1] if path_parts[0].lower() == 'music' else path_parts[0]
                    subdir_lower = subdir.lower().strip()
                    
                    # 匹配逻辑：完全匹配或部分匹配（支持下划线和连字符）
                    # 例如：business 匹配 business, self_improvement 匹配 self_improvement
                    is_match = (
                        directory_name_lower == subdir_lower or  # 完全匹配
                        directory_name_lower.replace('_', '-') == subdir_lower.replace('_', '-') or  # 支持下划线和连字符互换
                        directory_name_lower in subdir_lower or  # 包含匹配
                        subdir_lower in directory_name_lower  # 反向包含
                    )
                    
                    if is_match:
                        print(f"    ✓ 匹配: {cloud_path} (子目录: '{subdir}')")
                        filtered.append(music_info)
                        continue
            
            # 检查本地路径（备用方案，从完整路径提取）
            path = music_info.get('path', '')
            if path:
                # 提取目录部分
                dir_part = os.path.dirname(path)
                dir_name = os.path.basename(dir_part)
                dir_name_lower = dir_name.lower().strip()
                
                # 匹配逻辑：同上
                is_match = (
                    directory_name_lower == dir_name_lower or
                    directory_name_lower.replace('_', '-') == dir_name_lower.replace('_', '-') or
                    directory_name_lower in dir_name_lower or
                    dir_name_lower in directory_name_lower
                )
                
                if is_match:
                    filtered.append(music_info)
                    continue
        
        print(f"  匹配结果: 找到 {len(filtered)} 个文件")
        return filtered
    
    def select_music_by_category(
        self,
        category: Optional[str] = None,
        topic: Optional[str] = None,
        num_music: int = 1
    ) -> List[str]:
        """
        根据播客分类选择背景音乐（新策略：先匹配子目录，再随机选择）
        
        Args:
            category: 播客分类
            topic: 播客主题（可选，用于辅助匹配）
            num_music: 需要选择的音乐数量，默认1
        
        Returns:
            选中的音乐文件路径列表
        """
        # 扫描音乐文件（只获取文件列表，不预下载）
        music_files = self.scan_music_files_metadata_only()
        if not music_files:
            print(f"警告：没有找到音乐文件（音乐目录: {self.music_dir}）")
            print(f"提示：请确保音乐文件位于 {self.music_dir} 目录下")
            return []
        
        # 如果只有一个音乐文件，直接下载并返回
        if len(music_files) == 1:
            music_info = music_files[0]
            local_path = self._download_music_if_needed(music_info)
            if local_path:
                return [local_path]
            else:
                return []
        
        # 根据 category 匹配音乐子目录
        matched_directory = None
        if category:
            matched_directory = self._match_music_directory(category, topic)
            if matched_directory:
                print(f"✓ 根据分类 '{category}' 匹配到音乐子目录: {matched_directory}")
            else:
                print(f"⚠️ 无法根据分类 '{category}' 匹配到音乐子目录，将从所有音乐中随机选择")
        else:
            print("⚠️ 未提供播客分类，将从所有音乐中随机选择")
        
        # 如果匹配到子目录，在该子目录中过滤音乐文件
        if matched_directory:
            filtered_music = self._filter_music_by_directory(music_files, matched_directory)
            if filtered_music:
                print(f"✓ 在子目录 '{matched_directory}' 中找到 {len(filtered_music)} 个音乐文件")
                music_files = filtered_music
            else:
                print(f"⚠️ 在子目录 '{matched_directory}' 中未找到音乐文件，将从所有音乐中随机选择")
                music_files = music_files  # 使用全部音乐文件
        
        # 随机选择音乐
        import random
        if len(music_files) == 0:
            print("⚠️ 没有可用的音乐文件")
            return []
        
        selected_count = min(num_music, len(music_files))
        selected_indices = random.sample(range(len(music_files)), selected_count)
        
        # 获取选中的音乐文件路径（只下载选中的文件）
        selected_music = []
        for idx in selected_indices:
            music_info = music_files[idx]
            local_path = self._download_music_if_needed(music_info)
            if local_path:
                selected_music.append(local_path)
            else:
                print(f"警告：无法下载音乐文件 {music_info.get('name', 'unknown')}，跳过")
        
        if selected_music:
            print(f"✓ 随机选择音乐: {[os.path.basename(p) for p in selected_music]}")
            if matched_directory:
                print(f"  来源子目录: {matched_directory}")
        else:
            print("⚠️ 未能成功选择任何音乐文件")
        
        return selected_music
    
    def select_music_by_ai(
        self,
        text: str,
        podcast_name: Optional[str] = None,
        topic: Optional[str] = None,
        scene_types: Optional[List[str]] = None,
        category: Optional[str] = None,
        num_music: int = 1
    ) -> List[str]:
        """
        使用AI分析文本内容，自动选择合适的背景音乐
        
        新策略：如果提供了 category，则先根据分类匹配子目录，然后在子目录中随机选择
        否则，使用原有的AI分析方式
        
        Args:
            text: 播客文本内容
            topic: 播客主题（可选）
            podcast_name: 播客名称（可选）
            scene_types: 场景类型列表（可选）
            category: 播客分类（可选），如果提供则使用分类匹配策略
            num_music: 需要选择的音乐数量，默认1
        
        Returns:
            选中的音乐文件路径列表
        """
        # 如果提供了 category，使用新的分类匹配策略
        if category:
            print("=" * 60)
            print("🎵 使用分类匹配策略选择背景音乐")
            print(f"  播客分类: {category}")
            print(f"  播客主题: {topic or '未指定'}")
            print("=" * 60)
            return self.select_music_by_category(category=category, topic=topic, num_music=num_music)
        
        # 否则，使用原有的AI分析方式
        print("=" * 60)
        print("🎵 使用AI分析策略选择背景音乐")
        print("=" * 60)
        
        # 扫描音乐文件（只获取文件列表，不预下载）
        # 优化：先选择音乐，再下载选中的文件，避免下载所有文件
        music_files = self.scan_music_files_metadata_only()
        if not music_files:
            print(f"警告：没有找到音乐文件（音乐目录: {self.music_dir}）")
            print(f"提示：请确保音乐文件位于 {self.music_dir} 目录下")
            return []
        
        # 如果只有一个音乐文件，直接下载并返回
        if len(music_files) == 1:
            music_info = music_files[0]
            local_path = self._download_music_if_needed(music_info)
            if local_path:
                return [local_path]
            else:
                return []
        
        # 优化：如果音乐文件数量较少（<=5个），直接使用关键词匹配，避免AI调用
        if len(music_files) <= 5:
            print(f"音乐文件数量较少（{len(music_files)}个），使用关键词匹配，跳过AI调用以提升性能")
            return self._select_music_by_keywords(text, topic, scene_types, music_files, num_music)
        
        # 构建选择提示词（优化：缩短文本预览，减少prompt长度）
        music_list_str = "\n".join([
            f"{i+1}. {m['name']} ({m['style']})"
            for i, m in enumerate(music_files)
        ])
        
        # 构建场景描述
        scene_desc = ""
        if scene_types:
            scene_desc = f"场景：{', '.join(scene_types[:3])}\n"  # 限制场景数量
        
        # 优化：缩短prompt，减少文本预览长度
        text_preview = text[:300] if len(text) > 300 else text
        
        selection_prompt = f"""从以下音乐中选择最合适的背景音乐：

播客：{podcast_name or "未指定"}
主题：{topic or "未指定"}
{scene_desc}文本：{text_preview}...

音乐库：
{music_list_str}

要求：根据主题和场景选择匹配的音乐。返回JSON：
{{"selected_music": [编号], "reason": "理由"}}"""
        
        try:
            # 优化：降低max_tokens，加快响应速度
            response = self.api_client.generate_text(
                prompt=selection_prompt,
                temperature=0.7,
                max_tokens=200  # 从500降低到200，减少生成时间
            )
            
            # 提取JSON
            response = re.sub(r'```json\s*', '', response)
            response = re.sub(r'```\s*', '', response)
            response = response.strip()
            
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                
                selected_indices = result.get("selected_music", [])
                if not isinstance(selected_indices, list):
                    selected_indices = [selected_indices]
                
                # 验证索引范围
                valid_indices = [
                    idx - 1 for idx in selected_indices
                    if isinstance(idx, int) and 1 <= idx <= len(music_files)
                ]
                
                if not valid_indices:
                    # 如果AI选择失败，随机选择
                    import random
                    print("AI选择失败，使用随机选择")
                    valid_indices = random.sample(range(len(music_files)), min(num_music, len(music_files)))
                
                # 限制数量
                valid_indices = valid_indices[:num_music]
                
                # 获取选中的音乐文件路径（只下载选中的文件）
                selected_music = []
                for idx in valid_indices:
                    music_info = music_files[idx]
                    local_path = self._download_music_if_needed(music_info)
                    if local_path:
                        selected_music.append(local_path)
                    else:
                        print(f"警告：无法下载音乐文件 {music_info.get('name', 'unknown')}，跳过")
                
                reason = result.get("reason", "AI自动选择")
                print(f"AI选择音乐: {[os.path.basename(p) for p in selected_music]}")
                print(f"选择理由: {reason}")
                
                return selected_music
            else:
                # 如果无法解析JSON，使用基于关键词的简单匹配
                print("无法解析AI响应，使用基于关键词的匹配")
                return self._select_music_by_keywords(text, topic, scene_types, music_files, num_music)
                
        except Exception as e:
            print(f"AI选择音乐失败: {str(e)}，使用基于关键词的匹配")
            return self._select_music_by_keywords(text, topic, scene_types, music_files, num_music)
    
    def _select_music_by_keywords(
        self,
        text: str,
        topic: Optional[str],
        scene_types: Optional[List[str]],
        music_files: List[Dict[str, str]],
        num_music: int
    ) -> List[str]:
        """
        基于关键词的简单匹配选择音乐（AI选择失败时的备选方案）
        """
        # 合并所有文本内容
        all_text = " ".join([text, topic or "", " ".join(scene_types or [])]).lower()
        
        # 计算每个音乐的匹配分数
        scores = []
        for music in music_files:
            score = 0
            style = music['style']
            name = music['name'].lower()
            
            # 根据场景类型匹配
            if scene_types:
                scene_text = " ".join(scene_types).lower()
                if "interview" in scene_text or "访谈" in scene_text:
                    if "interview" in style or "interview" in name:
                        score += 10
                if "corporate" in scene_text or "商务" in scene_text or "企业" in scene_text:
                    if "corporate" in style or "corporate" in name:
                        score += 10
                if "轻松" in scene_text or "chill" in scene_text:
                    if "chill" in style or "chill" in name:
                        score += 10
            
            # 根据主题匹配
            if topic:
                topic_lower = topic.lower()
                if "商务" in topic_lower or "企业" in topic_lower:
                    if "corporate" in style or "corporate" in name:
                        score += 5
                if "访谈" in topic_lower or "对话" in topic_lower:
                    if "interview" in style or "interview" in name:
                        score += 5
            
            scores.append((score, music))
        
        # 按分数排序
        scores.sort(key=lambda x: x[0], reverse=True)
        
        # 选择前num_music个，处理云存储文件
        selected = []
        for _, music in scores[:num_music]:
            # 使用统一的下载方法
            local_path = self._download_music_if_needed(music)
            if local_path:
                selected.append(local_path)
            else:
                print(f"警告：无法获取音乐文件 {music.get('name', 'unknown')}，跳过")
        
        print(f"基于关键词选择音乐: {[os.path.basename(p) for p in selected]}")
        return selected

