"""
播客生成核心模块
整合混元模型和IndexTTS-2，实现多角色播客生成
"""
import os
import sys
import logging
import torch
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# 设置 HuggingFace 镜像（如果未设置，避免下载时的网络问题）
if "HF_ENDPOINT" not in os.environ:
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

# 添加index-tts路径到sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
index_tts_path = os.path.join(project_root, "index-tts")
if index_tts_path not in sys.path:
    sys.path.insert(0, index_tts_path)

try:
    from indextts.infer_v2 import IndexTTS2
except ImportError as e:
    error_msg = str(e)
    # 检查是否是缺少依赖导致的错误
    if "librosa" in error_msg or "No module named" in error_msg:
        print("导入错误：缺少必要的依赖")
        print(f"   错误详情: {error_msg}")
        print("\n解决方案：")
        print("   1. 如果使用 uv 环境：")
        print("      cd index-tts")
        print("      uv sync --all-extras")
        print("   2. 如果使用标准 Python 环境：")
        print("      pip install librosa torch torchaudio")
        print("   3. 确保在正确的 Python 环境中运行")
        raise ImportError(f"缺少依赖: {error_msg}\n请按照上述提示安装依赖。")
    
    # 如果直接导入失败，尝试从项目根目录导入
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "infer_v2",
        os.path.join(index_tts_path, "indextts", "infer_v2.py")
    )
    if spec and spec.loader:
        infer_v2_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(infer_v2_module)
        IndexTTS2 = infer_v2_module.IndexTTS2
    else:
        raise ImportError("无法导入IndexTTS2，请检查index-tts路径")

from .api_client import get_client, SiliconFlowClient
from .text_processor import TextProcessor
from .utils import (
    concatenate_audios,
    save_audio,
    load_audio,
    get_output_path,
    add_intro_outro_music,
    mix_audio_with_background,
    AUDIO_SAMPLING_RATE,
    AUDIO_SILENCE_INTERVAL
)
from .config import INDEXTTS_CONFIG_PATH, INDEXTTS_MODEL_DIR


class PodcastGenerator:
    """播客生成器"""
    
    def __init__(
        self,
        tts_config_path: Optional[str] = None,
        tts_model_dir: Optional[str] = None,
        use_fp16: bool = False,
        use_cuda_kernel: bool = False,
        device: Optional[str] = None,
        api_client: Optional[SiliconFlowClient] = None
    ):
        """
        初始化播客生成器
        
        Args:
            tts_config_path: IndexTTS-2配置文件路径
            tts_model_dir: IndexTTS-2模型目录
            use_fp16: 是否使用FP16精度
            use_cuda_kernel: 是否使用CUDA内核
            device: 设备类型 (如 'cuda:0', 'cuda', 'cpu')，如果为None则自动检测
            api_client: API客户端实例，如果为None则创建新实例
        """
        # 保存TTS配置（延迟加载）
        self.tts_config_path = tts_config_path or INDEXTTS_CONFIG_PATH
        self.tts_model_dir = tts_model_dir or INDEXTTS_MODEL_DIR
        self.use_fp16 = use_fp16
        self.use_cuda_kernel = use_cuda_kernel
        self.device = device
        
        # TTS模型延迟加载（在需要时才加载）
        self.tts: Optional[IndexTTS2] = None
        
        # 初始化文本处理器和API客户端
        self.text_processor = TextProcessor()
        self.api_client = api_client or get_client()
        
        # 角色音色映射
        self.role_voices: Dict[str, str] = {}
    
    def _ensure_tts_loaded(self) -> None:
        """
        确保TTS模型已加载（延迟加载）
        """
        if self.tts is None:
            print(f"正在加载IndexTTS-2模型...")
            print(f"配置文件: {self.tts_config_path}")
            print(f"模型目录: {self.tts_model_dir}")
            
            # 如果没有指定设备，自动检测GPU
            device = self.device
            if device is None:
                if torch.cuda.is_available():
                    device = "cuda:0"
                    print(f"🎯 检测到GPU，将使用设备: {device}")
                else:
                    device = None  # 让IndexTTS2自动检测
                    print("⚠️  未检测到GPU，将使用CPU模式")
            else:
                print(f"🎯 使用指定设备: {device}")
            
            self.tts = IndexTTS2(
                cfg_path=self.tts_config_path,
                model_dir=self.tts_model_dir,
                use_fp16=self.use_fp16,
                device=device,
                use_cuda_kernel=self.use_cuda_kernel,
                use_deepspeed=False
            )
            print(f"✅ IndexTTS-2模型加载完成！使用设备: {self.tts.device}")
    
    def set_role_voice(self, role: str, voice_file: str) -> None:
        """
        设置角色的音色文件
        
        Args:
            role: 角色名
            voice_file: 音色参考音频文件路径
        """
        if not os.path.exists(voice_file):
            raise FileNotFoundError(f"音色文件不存在: {voice_file}")
        self.role_voices[role] = voice_file
        print(f"已设置角色 '{role}' 的音色: {voice_file}")
    
    def set_role_voices(self, role_voices: Dict[str, str]) -> None:
        """
        批量设置角色音色
        
        Args:
            role_voices: 角色音色映射字典
        """
        for role, voice_file in role_voices.items():
            self.set_role_voice(role, voice_file)
    
    def generate_from_text(
        self,
        text: str,
        role_voices: Optional[Dict[str, str]] = None,
        output_path: Optional[str] = None,
        silence_interval: int = AUDIO_SILENCE_INTERVAL,
        intro_music: Optional[str] = None,
        outro_music: Optional[str] = None,
        background_music: Optional[str] = None,
        background_volume: float = 0.3,
        verbose: bool = False
    ) -> str:
        """
        从文本生成播客音频（子题目1：多角色自然互动播客）
        
        Args:
            text: 包含角色标记的文本
            role_voices: 角色音色映射，如果为None则使用已设置的映射
            output_path: 输出文件路径
            silence_interval: 角色切换时的静音间隔（毫秒）
            intro_music: 开场音乐文件路径（可选）
            outro_music: 结尾音乐文件路径（可选）
            background_music: 背景音乐文件路径（可选）
            background_volume: 背景音乐音量（0.0-1.0），默认0.3
            verbose: 是否输出详细信息
        
        Returns:
            生成的音频文件路径
        """
        if role_voices:
            self.set_role_voices(role_voices)

        # 解析角色对话
        dialogues = self.text_processor.parse_role_text(text)

        # 创建模块级日志器（延迟创建，防止重复）
        logger = logging.getLogger(__name__)

        if not dialogues:
            raise ValueError("未能从文本中解析出角色对话")

        # 过滤掉那些没有提供音色文件的角色，避免因为误识别的角色（例如来自错误解析的Content_Types）导致整个生成失败
        provided_roles = set(self.role_voices.keys())
        filtered_dialogues = [d for d in dialogues if d[0] in provided_roles]
        missing_roles = sorted({d[0] for d in dialogues} - provided_roles)
        if missing_roles:
            logger.warning(f"以下角色未提供音色文件，将被跳过: {missing_roles}")

        # 如果所有对话都被过滤掉，抛出错误
        if not filtered_dialogues:
            raise ValueError(f"未能找到任何已提供音色的角色对话。检测到的角色: {[d[0] for d in dialogues]}，已提供的角色: {list(provided_roles)}")

        # 替换为过滤后的对话列表继续生成
        dialogues = filtered_dialogues
        
        if verbose:
            print(f"解析到 {len(dialogues)} 段对话")
            for role, content in dialogues:
                print(f"  {role}: {content[:50]}...")
        
        # 为每个角色生成音频
        audio_segments = []
        for role, content in dialogues:
            if not content.strip():
                continue
            
            # 获取角色的音色文件
            voice_file = self.role_voices.get(role)
            if not voice_file:
                raise ValueError(f"角色 '{role}' 没有设置音色文件")
            
            if verbose:
                print(f"正在为角色 '{role}' 生成音频...")
            
            # 生成临时音频文件
            temp_audio_path = get_output_path(f"temp_{role}_{len(audio_segments)}.wav")
            
            # 确保TTS模型已加载
            self._ensure_tts_loaded()
            
            # 使用IndexTTS-2生成音频
            self.tts.infer(
                spk_audio_prompt=voice_file,
                text=content,
                output_path=temp_audio_path,
                verbose=verbose,
                max_text_tokens_per_segment=120
            )
            
            # 加载生成的音频
            audio, sr = load_audio(temp_audio_path, AUDIO_SAMPLING_RATE)
            audio_segments.append(audio)
            
            # 清理临时文件
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
        
        # 合成所有音频片段
        if not output_path:
            output_path = get_output_path()
        else:
            # 确保输出路径是绝对路径
            output_path = os.path.abspath(output_path)
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        if verbose:
            print(f"正在合成 {len(audio_segments)} 个音频片段...")
        
        # 合成所有对话音频
        main_audio = concatenate_audios(
            audio_segments,
            silence_intervals=[silence_interval] * (len(audio_segments) - 1),
            sr=AUDIO_SAMPLING_RATE
        )
        
        # 如果有背景音乐，混合背景音乐
        if background_music and os.path.exists(background_music):
            if verbose:
                print(f"正在加载并混合背景音乐: {background_music}")
            background_audio, _ = load_audio(background_music, AUDIO_SAMPLING_RATE)
            main_audio = mix_audio_with_background(
                main_audio,
                background_audio,
                background_volume=background_volume
            )
        
        # 加载开场和结尾音乐
        intro_audio = None
        outro_audio = None
        
        if intro_music and os.path.exists(intro_music):
            if verbose:
                print(f"正在加载开场音乐: {intro_music}")
            intro_audio, _ = load_audio(intro_music, AUDIO_SAMPLING_RATE)
        
        if outro_music and os.path.exists(outro_music):
            if verbose:
                print(f"正在加载结尾音乐: {outro_music}")
            outro_audio, _ = load_audio(outro_music, AUDIO_SAMPLING_RATE)
        
        # 添加开场和结尾音乐
        if intro_audio is not None or outro_audio is not None:
            if verbose:
                print("正在添加开场和结尾音乐...")
            final_audio = add_intro_outro_music(
                main_audio,
                intro_music=intro_audio,
                outro_music=outro_audio,
                sr=AUDIO_SAMPLING_RATE
            )
        else:
            final_audio = main_audio
        
        if verbose:
            print(f"正在保存音频到: {output_path}")
        
        save_audio(final_audio, output_path, AUDIO_SAMPLING_RATE)
        
        # 返回绝对路径
        return os.path.abspath(output_path)
    
    def generate_with_characters(
        self,
        character_descriptions: Dict[str, str],
        role_voices: Dict[str, str],
        topic: Optional[str] = None,
        output_path: Optional[str] = None,
        silence_interval: int = AUDIO_SILENCE_INTERVAL,
        verbose: bool = False
    ) -> str:
        """
        根据角色人设生成播客音频（子题目2：自定义角色人设和音色）
        
        Args:
            character_descriptions: 角色人设描述字典
            role_voices: 角色音色映射
            topic: 可选的主题
            output_path: 输出文件路径
            silence_interval: 角色切换时的静音间隔（毫秒）
            verbose: 是否输出详细信息
        
        Returns:
            生成的音频文件路径
        """
        # 设置角色音色
        self.set_role_voices(role_voices)
        
        # 构建提示词
        prompt = self.text_processor.build_character_prompt(character_descriptions, topic)
        
        if verbose:
            print("正在调用混元模型生成对话...")
            print(f"提示词: {prompt[:200]}...")
        
        # 调用混元模型生成对话文本
        generated_text = self.api_client.generate_text(
            prompt=prompt,
            temperature=0.8,
            max_tokens=2000
        )
        
        if verbose:
            print(f"生成的对话文本:\n{generated_text}")
        
        # 清理生成的文本
        generated_text = self.text_processor.clean_text(generated_text)
        
        # 从生成的文本生成音频
        return self.generate_from_text(
            text=generated_text,
            silence_interval=silence_interval,
            verbose=verbose,
            output_path=output_path
        )
    
    def generate_deep_podcast(
        self,
        topic: str,
        role_voices: Dict[str, str],
        num_characters: int = 2,
        depth_level: str = "深度",
        output_path: Optional[str] = None,
        silence_interval: int = AUDIO_SILENCE_INTERVAL,
        verbose: bool = False
    ) -> str:
        """
        基于主题生成深度播客音频（子题目3：主题深度播客）
        
        Args:
            topic: 播客主题
            role_voices: 角色音色映射
            num_characters: 角色数量
            depth_level: 深度级别
            output_path: 输出文件路径
            silence_interval: 角色切换时的静音间隔（毫秒）
            verbose: 是否输出详细信息
        
        Returns:
            生成的音频文件路径
        """
        # 设置角色音色
        self.set_role_voices(role_voices)
        
        # 构建提示词
        prompt = self.text_processor.build_deep_podcast_prompt(topic, depth_level, num_characters)
        
        if verbose:
            print("正在调用混元模型生成深度对话...")
            print(f"主题: {topic}")
            print(f"提示词: {prompt[:200]}...")
        
        # 调用混元模型生成对话文本
        generated_text = self.api_client.generate_text(
            prompt=prompt,
            temperature=0.7,
            max_tokens=2500
        )
        
        if verbose:
            print(f"生成的对话文本:\n{generated_text}")
        
        # 清理生成的文本
        generated_text = self.text_processor.clean_text(generated_text)
        
        # 从生成的文本生成音频
        return self.generate_from_text(
            text=generated_text,
            silence_interval=silence_interval,
            verbose=verbose,
            output_path=output_path
        )
    
    def generate_from_prompt(
        self,
        prompt: str,
        role_voices: Dict[str, str],
        output_path: Optional[str] = None,
        silence_interval: int = AUDIO_SILENCE_INTERVAL,
        verbose: bool = False
    ) -> str:
        """
        从自定义提示词生成播客音频
        
        Args:
            prompt: 自定义提示词
            role_voices: 角色音色映射
            output_path: 输出文件路径
            silence_interval: 角色切换时的静音间隔（毫秒）
            verbose: 是否输出详细信息
        
        Returns:
            生成的音频文件路径
        """
        # 设置角色音色
        self.set_role_voices(role_voices)
        
        if verbose:
            print("正在调用混元模型生成对话...")
        
        # 调用混元模型生成对话文本
        generated_text = self.api_client.generate_text(
            prompt=prompt,
            temperature=0.8,
            max_tokens=2000
        )
        
        if verbose:
            print(f"生成的对话文本:\n{generated_text}")
        
        # 清理生成的文本
        generated_text = self.text_processor.clean_text(generated_text)
        
        # 从生成的文本生成音频
        return self.generate_from_text(
            text=generated_text,
            silence_interval=silence_interval,
            verbose=verbose,
            output_path=output_path
        )

