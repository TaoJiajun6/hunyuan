"""
混元AI播客生成工作流插件
可以直接在工作流系统中使用
"""
import requests
import base64
import json
import os
import time
from typing import Dict, List, Optional, Any


class HunyuanPodcastPlugin:
    """混元AI播客生成工作流插件"""
    
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        """
        初始化插件
        
        Args:
            api_base_url: API服务地址
        """
        self.api_base_url = api_base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def health_check(self) -> bool:
        """检查API服务是否可用"""
        try:
            response = self.session.get(f"{self.api_base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def encode_audio_file(self, file_path: str) -> str:
        """
        将音频文件编码为base64
        
        Args:
            file_path: 音频文件路径
        
        Returns:
            base64编码的音频数据
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"音频文件不存在: {file_path}")
        
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    
    def decode_audio_file(self, base64_data: str, output_path: str):
        """
        将base64编码的音频数据解码并保存为文件
        
        Args:
            base64_data: base64编码的音频数据
            output_path: 输出文件路径
        """
        audio_data = base64.b64decode(base64_data)
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(audio_data)
    
    def generate_multi_role_podcast(
        self,
        text: str,
        role_voice_files: Dict[str, str],
        silence_interval: int = 300,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成多角色互动播客（子题目1）
        
        Args:
            text: 播客文本（支持角色标记或普通文本）
            role_voice_files: 角色音色文件路径字典，格式为 {角色名: 文件路径}
            silence_interval: 角色切换静音间隔（毫秒）
            output_path: 输出音频文件路径（可选，如果不提供则返回base64数据）
        
        Returns:
            API响应结果
        """
        # 编码音频文件
        role_voices = {}
        for role, file_path in role_voice_files.items():
            role_voices[role] = self.encode_audio_file(file_path)
        
        # 发送请求
        response = self.session.post(
            f"{self.api_base_url}/api/v1/podcast/multi_role",
            json={
                "text": text,
                "role_voices": role_voices,
                "silence_interval": silence_interval
            },
            timeout=300  # 5分钟超时
        )
        
        result = response.json()
        
        # 如果提供了输出路径，保存音频文件
        if result.get("success") and output_path and result.get("data", {}).get("audio_base64"):
            self.decode_audio_file(result["data"]["audio_base64"], output_path)
            result["data"]["audio_path"] = output_path
        
        return result
    
    def generate_character_podcast(
        self,
        characters: List[Dict[str, Any]],
        topic: Optional[str] = None,
        silence_interval: int = 300,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成自定义角色播客（子题目2）
        
        Args:
            characters: 角色列表，每个角色包含：
                - name: 角色名称
                - identity: 身份/职业（可选）
                - personality: 核心性格（可选）
                - catchphrase: 口头禅/说话习惯（可选）
                - speaking_style: 说话风格（可选）
                - relationship: 与其他角色的关系（可选）
                - voice_file: 音色文件路径
            topic: 播客主题（可选）
            silence_interval: 角色切换静音间隔（毫秒）
            output_path: 输出音频文件路径（可选）
        
        Returns:
            API响应结果
        """
        # 处理角色数据
        processed_characters = []
        for char in characters:
            char_data = {
                "name": char["name"],
                "identity": char.get("identity"),
                "personality": char.get("personality"),
                "catchphrase": char.get("catchphrase"),
                "speaking_style": char.get("speaking_style"),
                "relationship": char.get("relationship"),
                "voice": self.encode_audio_file(char["voice_file"])
            }
            processed_characters.append(char_data)
        
        # 发送请求
        response = self.session.post(
            f"{self.api_base_url}/api/v1/podcast/character",
            json={
                "characters": processed_characters,
                "topic": topic,
                "silence_interval": silence_interval
            },
            timeout=300
        )
        
        result = response.json()
        
        # 如果提供了输出路径，保存音频文件
        if result.get("success") and output_path and result.get("data", {}).get("audio_base64"):
            self.decode_audio_file(result["data"]["audio_base64"], output_path)
            result["data"]["audio_path"] = output_path
        
        return result
    
    def generate_deep_podcast(
        self,
        topic: str,
        role_voice_files: Dict[str, str],
        num_characters: int = 2,
        depth_level: str = "深度",
        silence_interval: int = 300,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成主题深度播客（子题目3）
        
        Args:
            topic: 播客主题
            role_voice_files: 角色音色文件路径字典，格式为 {角色名: 文件路径}
            num_characters: 角色数量（2-3个）
            depth_level: 深度级别（"深度"、"中等"、"浅层"）
            silence_interval: 角色切换静音间隔（毫秒）
            output_path: 输出音频文件路径（可选）
        
        Returns:
            API响应结果
        """
        # 编码音频文件
        role_voices = {}
        role_names = ["角色A", "角色B", "角色C"][:num_characters]
        for role_name in role_names:
            if role_name in role_voice_files:
                role_voices[role_name] = self.encode_audio_file(role_voice_files[role_name])
        
        # 发送请求
        response = self.session.post(
            f"{self.api_base_url}/api/v1/podcast/deep",
            json={
                "topic": topic,
                "role_voices": role_voices,
                "num_characters": num_characters,
                "depth_level": depth_level,
                "silence_interval": silence_interval
            },
            timeout=300
        )
        
        result = response.json()
        
        # 如果提供了输出路径，保存音频文件
        if result.get("success") and output_path and result.get("data", {}).get("audio_base64"):
            self.decode_audio_file(result["data"]["audio_base64"], output_path)
            result["data"]["audio_path"] = output_path
        
        return result


# 使用示例
if __name__ == "__main__":
    # 创建插件实例
    plugin = HunyuanPodcastPlugin(api_base_url="http://localhost:8000")
    
    # 检查服务状态
    if not plugin.health_check():
        print("❌ API服务不可用，请先启动API服务：python run_api_server.py")
        exit(1)
    
    print("✅ API服务连接成功")
    
    # 示例1：多角色互动播客
    print("\n📝 示例1：生成多角色互动播客")
    result = plugin.generate_multi_role_podcast(
        text="中科曙光发布640卡超节点，算力密度提升20倍。在2025世界互联网大会乌镇峰会上，中科曙光正式发布全球首款单机柜级640卡超节点scaleX640。",
        role_voice_files={
            "角色A": "path/to/voice_a.wav",
            "角色B": "path/to/voice_b.wav"
        },
        output_path="output_multi_role.wav"
    )
    
    if result["success"]:
        print(f"✅ 生成成功！")
        print(f"   音频文件: {result['data']['audio_path']}")
        print(f"   文件大小: {result['data']['file_size_mb']} MB")
        print(f"   角色: {', '.join(result['data']['roles'])}")
        print(f"   脚本预览: {result['data']['script'][:100]}...")
    else:
        print(f"❌ 生成失败: {result.get('error', '未知错误')}")
    
    # 示例2：自定义角色播客
    print("\n📝 示例2：生成自定义角色播客")
    result = plugin.generate_character_podcast(
        characters=[
            {
                "name": "托尼老师",
                "identity": "时尚潮人、理发店总监",
                "personality": "自信略带浮夸、热心肠",
                "catchphrase": "喜欢用夸张的赞美和比喻，语速快，充满激情",
                "speaking_style": "清亮有穿透力的声音，语调起伏大",
                "relationship": "与角色B是好友，经常互怼",
                "voice_file": "path/to/voice_a.wav"
            },
            {
                "name": "程序员阿哲",
                "identity": "资深后端工程师",
                "personality": "逻辑控、内向务实、轻微社恐",
                "catchphrase": "语速平缓，用词精准，喜欢用'从技术实现上讲...'",
                "speaking_style": "低沉温和的声音，语调平稳",
                "relationship": "与角色A是好友，经常被角色A的热情感染",
                "voice_file": "path/to/voice_b.wav"
            }
        ],
        topic="人工智能的发展与未来",
        output_path="output_character.wav"
    )
    
    if result["success"]:
        print(f"✅ 生成成功！")
        print(f"   音频文件: {result['data']['audio_path']}")
        print(f"   文件大小: {result['data']['file_size_mb']} MB")
    else:
        print(f"❌ 生成失败: {result.get('error', '未知错误')}")
    
    # 示例3：主题深度播客
    print("\n📝 示例3：生成主题深度播客")
    result = plugin.generate_deep_podcast(
        topic="人工智能对人类社会的影响",
        role_voice_files={
            "角色A": "path/to/voice_a.wav",
            "角色B": "path/to/voice_b.wav"
        },
        depth_level="深度",
        output_path="output_deep.wav"
    )
    
    if result["success"]:
        print(f"✅ 生成成功！")
        print(f"   音频文件: {result['data']['audio_path']}")
        print(f"   文件大小: {result['data']['file_size_mb']} MB")
        print(f"   主题: {result['data']['topic']}")
        print(f"   深度级别: {result['data']['depth_level']}")
    else:
        print(f"❌ 生成失败: {result.get('error', '未知错误')}")


















