"""
音乐自动选择模块
使用AI分析文本内容，自动从音乐库中选择合适的背景音乐
"""
import os
import glob
import re
import json
from typing import List, Optional, Dict
from .config import MUSIC_DIR
from .api_client import get_client


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
    
    def __init__(self, music_dir: Optional[str] = None):
        """
        初始化音乐选择器
        
        Args:
            music_dir: 音乐文件夹路径，如果为None则使用默认路径
        """
        self.music_dir = music_dir or MUSIC_DIR
        self.api_client = get_client()
        self._music_cache: Optional[List[Dict[str, str]]] = None
    
    def scan_music_files(self) -> List[Dict[str, str]]:
        """
        扫描音乐文件夹，获取所有音乐文件
        
        Returns:
            音乐文件列表，每个元素包含 {'path': 文件路径, 'name': 文件名, 'style': 推断的风格}
        """
        if self._music_cache is not None:
            return self._music_cache
        
        if not os.path.exists(self.music_dir):
            print(f"警告：音乐文件夹不存在: {self.music_dir}")
            return []
        
        music_files = []
        # 支持的音频格式
        audio_extensions = ['*.mp3', '*.wav', '*.m4a', '*.flac', '*.ogg']
        
        for ext in audio_extensions:
            pattern = os.path.join(self.music_dir, ext)
            files = glob.glob(pattern)
            for file_path in files:
                filename = os.path.basename(file_path)
                # 从文件名推断风格
                style = self._infer_style_from_filename(filename)
                music_files.append({
                    'path': file_path,
                    'name': filename,
                    'style': style
                })
        
        self._music_cache = music_files
        print(f"扫描到 {len(music_files)} 个音乐文件")
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
    
    def select_music_by_ai(
        self,
        text: str,
        podcast_name: Optional[str] = None,
        topic: Optional[str] = None,
        scene_types: Optional[List[str]] = None,
        num_music: int = 1
    ) -> List[str]:
        """
        使用AI分析文本内容，自动选择合适的背景音乐
        
        Args:
            text: 播客文本内容
            topic: 播客主题（可选）
            podcast_name: 播客名称（可选）
            scene_types: 场景类型列表（可选）
            num_music: 需要选择的音乐数量，默认1
        
        Returns:
            选中的音乐文件路径列表
        """
        # 扫描音乐文件
        music_files = self.scan_music_files()
        if not music_files:
            print("警告：没有找到音乐文件")
            return []
        
        # 如果只有一个音乐文件，直接返回
        if len(music_files) == 1:
            return [music_files[0]['path']]
        
        # 构建选择提示词
        music_list_str = "\n".join([
            f"- {i+1}. {m['name']} (风格: {m['style']})"
            for i, m in enumerate(music_files)
        ])
        
        # 构建场景描述
        scene_desc = ""
        if scene_types:
            scene_desc = f"场景类型：{', '.join(scene_types)}\n"
        
        selection_prompt = f"""你是一位专业的播客音乐总监。请根据以下信息，从音乐库中选择最合适的背景音乐。

播客信息：
- 播客名称：{podcast_name or "未指定"}
- 主题：{topic or "未指定"}
{scene_desc}
文本内容预览：{text[:500]}...

可用音乐库：
{music_list_str}

选择要求：
1. 根据播客的主题、场景类型和文本内容，选择最匹配的音乐
2. 音乐应该能够增强播客的氛围，不干扰对话
3. 优先选择与场景类型匹配的音乐（如访谈场景选择interview风格，商务场景选择corporate风格）
4. 如果场景类型不明确，选择chill或general风格的音乐

请返回JSON格式，包含选中的音乐编号（从1开始）：
{{
    "selected_music": [音乐编号1, 音乐编号2, ...],
    "reason": "选择理由（简要说明）"
}}

请直接返回JSON，不要添加其他说明。"""
        
        try:
            response = self.api_client.generate_text(
                prompt=selection_prompt,
                temperature=0.7,
                max_tokens=500
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
                
                selected_music = [music_files[idx]['path'] for idx in valid_indices]
                
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
        
        # 选择前num_music个
        selected = [music['path'] for _, music in scores[:num_music]]
        
        print(f"基于关键词选择音乐: {[os.path.basename(p) for p in selected]}")
        return selected

