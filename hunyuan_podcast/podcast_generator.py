"""
播客生成核心模块
整合混元模型和SoulX-Podcast，实现多角色播客生成
"""
import os
import sys
import logging
import torch
import torchaudio
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path

# 设置 HuggingFace 镜像（如果未设置，避免下载时的网络问题）
if "HF_ENDPOINT" not in os.environ:
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from .api_client import get_client, HunyuanClient
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
from .config import SOULX_PODCAST_MODEL_DIR, SOULX_PODCAST_LLM_ENGINE, SOULX_PODCAST_FP16_FLOW
from .soulx_tts import SoulXTTS


class PodcastGenerator:
    """播客生成器"""
    
    def __init__(
        self,
        tts_model_dir: Optional[str] = None,
        llm_engine: Optional[str] = None,
        fp16_flow: Optional[bool] = None,
        device: Optional[str] = None,
        api_client: Optional[HunyuanClient] = None
    ):
        """
        初始化播客生成器
        
        Args:
            tts_model_dir: SoulX-Podcast模型目录
            llm_engine: LLM引擎类型 ("hf" 或 "vllm")，如果为None则使用配置默认值
            fp16_flow: 是否使用FP16精度，如果为None则使用配置默认值
            device: 设备类型（SoulX-Podcast自动使用CUDA，此参数保留以兼容接口）
            api_client: API客户端实例，如果为None则创建新实例
        """
        # 保存TTS配置（延迟加载）
        self.tts_model_dir = tts_model_dir or SOULX_PODCAST_MODEL_DIR
        self.llm_engine = llm_engine if llm_engine is not None else SOULX_PODCAST_LLM_ENGINE
        self.fp16_flow = fp16_flow if fp16_flow is not None else SOULX_PODCAST_FP16_FLOW
        self.device = device  # SoulX-Podcast 自动使用 CUDA
        
        # TTS模型延迟加载（在需要时才加载）
        self.tts: Optional[SoulXTTS] = None
        
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
            print(f"正在加载SoulX-Podcast模型...")
            print(f"模型目录: {self.tts_model_dir}")
            print(f"LLM引擎: {self.llm_engine}")
            print(f"FP16 Flow: {self.fp16_flow}")
            
            if torch.cuda.is_available():
                print(f"🎯 检测到GPU，将使用CUDA")
            else:
                print("⚠️  警告：未检测到GPU，SoulX-Podcast需要GPU支持")
            
            self.tts = SoulXTTS(
                model_path=self.tts_model_dir,
                llm_engine=self.llm_engine,
                fp16_flow=self.fp16_flow,
                device=self.device
            )
            print(f"✅ SoulX-Podcast模型加载完成！")
    
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
        intro_music: Optional[Union[str, List[str]]] = None,
        outro_music: Optional[Union[str, List[str]]] = None,
        background_music: Optional[Union[str, List[str]]] = None,
        background_volume: float = 0.3,
        background_mode: str = "random",
        verbose: bool = False
    ) -> str:
        """
        从文本生成播客音频（子题目1：多角色自然互动播客）
        
        Args:
            text: 包含角色标记的文本
            role_voices: 角色音色映射，如果为None则使用已设置的映射
            output_path: 输出文件路径
            silence_interval: 角色切换时的静音间隔（毫秒）
            intro_music: 开场音乐文件路径或路径列表（可选）
            outro_music: 结尾音乐文件路径或路径列表（可选）
            background_music: 背景音乐文件路径或路径列表（可选）
            background_volume: 背景音乐音量（0.0-1.0），默认0.3
            background_mode: 背景音乐处理模式（"random"/"concat"/"mix"），默认"random"
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
        
        # 确保TTS模型已加载
        self._ensure_tts_loaded()
        
        # 构建说话人信息字典（SoulX-Podcast格式）
        speakers = {}
        for role in set(role for role, _ in dialogues):
            voice_file = self.role_voices.get(role)
            if not voice_file:
                raise ValueError(f"角色 '{role}' 没有设置音色文件")
            speakers[role] = {
                "prompt_audio": voice_file,
                "prompt_text": f"这是角色 {role} 的参考音频。"
            }
        
        # 生成临时音频文件（SoulX-Podcast输出24000采样率）
        temp_audio_path = get_output_path("temp_soulx_output.wav")
        
        if verbose:
            print(f"正在使用SoulX-Podcast生成多角色播客音频...")
        
        # 使用SoulX-Podcast生成多角色播客音频
        self.tts.infer_multi_speaker(
            speakers=speakers,
            dialogues=dialogues,
            output_path=temp_audio_path,
            silence_interval=silence_interval,
            verbose=verbose
        )
        
        # 加载生成的音频并重采样到目标采样率（SoulX-Podcast输出24000，需要重采样到22050）
        audio, sr = load_audio(temp_audio_path, AUDIO_SAMPLING_RATE)
        
        # 确保音频格式正确（单声道，2D张量 (1, samples)）
        if audio.dim() == 1:
            audio = audio.unsqueeze(0)
        elif audio.dim() > 1 and audio.shape[0] > 1:
            # 如果是多声道，转换为单声道
            audio = torch.mean(audio, dim=0, keepdim=True)
        
        # 如果采样率不匹配，进行重采样
        if sr != AUDIO_SAMPLING_RATE:
            if verbose:
                print(f"正在将音频从 {sr}Hz 重采样到 {AUDIO_SAMPLING_RATE}Hz...")
            resampler = torchaudio.transforms.Resample(sr, AUDIO_SAMPLING_RATE)
            audio = resampler(audio)
        
        # 合成所有音频片段（SoulX-Podcast已经生成了完整音频，这里主要是为了后续处理）
        if not output_path:
            output_path = get_output_path()
        else:
            # 确保输出路径是绝对路径
            output_path = os.path.abspath(output_path)
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        main_audio = audio
        
        # 如果有背景音乐，混合背景音乐（启用ducking效果）
        print("=" * 60)
        print("开始处理背景音乐...")
        print(f"背景音乐参数: {background_music}")
        print(f"背景音乐类型: {type(background_music)}")
        
        if background_music:
            # 处理单个文件或文件列表
            if isinstance(background_music, str):
                if os.path.exists(background_music):
                    background_music_list = [background_music]
                    print(f"✓ 找到单个背景音乐文件: {background_music}")
                else:
                    background_music_list = []
                    print(f"✗ 背景音乐文件不存在: {background_music}")
            elif isinstance(background_music, list):
                # 如果是列表，过滤掉不存在的文件
                background_music_list = []
                for f in background_music:
                    if f and isinstance(f, str):
                        if os.path.exists(f):
                            background_music_list.append(f)
                            print(f"  ✓ 有效文件: {os.path.basename(f)}")
                        else:
                            print(f"  ✗ 文件不存在: {f}")
                    else:
                        print(f"  ✗ 无效文件路径: {f}")
            else:
                background_music_list = []
                print(f"✗ 背景音乐格式不正确: {type(background_music)}")
            
            print(f"处理后的背景音乐列表: {background_music_list}")
            print(f"有效文件数量: {len(background_music_list)}")
            
            if background_music_list:
                if len(background_music_list) == 1:
                    print(f"正在加载并混合背景音乐: {background_music_list[0]}")
                else:
                    print(f"正在加载并混合 {len(background_music_list)} 个背景音乐文件（模式: {background_mode}）")
                
                # 加载所有背景音乐
                background_audios = []
                for i, bg_path in enumerate(background_music_list, 1):
                    print(f"  [{i}/{len(background_music_list)}] 加载: {os.path.basename(bg_path)}")
                    try:
                        bg_audio, _ = load_audio(bg_path, AUDIO_SAMPLING_RATE)
                        background_audios.append(bg_audio)
                        print(f"    ✓ 加载成功，时长: {bg_audio.shape[1] / AUDIO_SAMPLING_RATE:.2f}秒")
                    except Exception as e:
                        print(f"    ✗ 加载失败: {str(e)}")
                        import traceback
                        print(f"    错误详情: {traceback.format_exc()}")
                
                if not background_audios:
                    print("⚠️ 所有背景音乐文件加载失败，将不使用背景音乐")
                    background_music_list = []
                
                # 根据模式处理
                if len(background_audios) == 1:
                    background_audio = background_audios[0]
                else:
                    if background_mode == "random":
                        import random
                        background_audio = random.choice(background_audios)
                    elif background_mode == "concat":
                        background_audio = concatenate_audios(background_audios, silence_intervals=[200] * (len(background_audios) - 1), sr=AUDIO_SAMPLING_RATE)
                    elif background_mode == "mix":
                        # 混合所有背景音乐
                        from .utils import load_multiple_audios
                        background_paths = background_music_list
                        background_audio = load_multiple_audios(background_paths, target_sr=AUDIO_SAMPLING_RATE, mode="mix")
                    else:
                        background_audio = background_audios[0]
                
                print(f"正在混合背景音乐（ducking效果: 启用，音量: {background_volume}）...")
                print(f"播放策略: intro 5秒 -> 对话（ducking）-> outro 5秒")
                
                main_audio = mix_audio_with_background(
                    main_audio,
                    background_audio,
                    background_volume=background_volume,
                    background_mode=background_mode,
                    enable_ducking=True,  # 启用ducking效果
                    intro_duration_ms=5000,  # 开场音乐5秒
                    outro_duration_ms=5000,  # 结束音乐5秒
                    remove_background_silence=True  # 去除背景音乐中的静音段
                )
                print("✓ 背景音乐混合完成")
                final_audio = main_audio
            else:
                print("⚠️ 背景音乐列表为空，将不使用背景音乐")
                final_audio = main_audio
        else:
            print("ℹ️ 未提供背景音乐参数")
            final_audio = main_audio
        
        if verbose:
            print(f"正在保存音频到: {output_path}")
        
        save_audio(final_audio, output_path, AUDIO_SAMPLING_RATE)
        
        # 清理临时文件
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
        
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
            temperature=0.7,  # 降低温度以加快生成速度
            max_tokens=1500  # 降低以加快生成速度
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
            max_tokens=2000  # 降低以加快生成速度
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
            temperature=0.7,  # 降低温度以加快生成速度
            max_tokens=1500  # 降低以加快生成速度
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

