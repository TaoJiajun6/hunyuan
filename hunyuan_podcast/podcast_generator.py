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
        detected_roles = {d[0] for d in dialogues}
        missing_roles = sorted(detected_roles - provided_roles)
        
        # 如果检测到的角色不在提供的角色列表中，尝试进行智能映射
        if missing_roles and len(missing_roles) == len(provided_roles):
            # 如果缺失的角色数量与提供的角色数量相同，尝试按顺序映射
            # 例如：检测到["林剑", "何立峰"]，提供["角色A", "角色B"]，则映射为：林剑->角色A, 何立峰->角色B
            provided_roles_list = sorted(list(provided_roles))
            missing_roles_list = sorted(missing_roles)
            role_mapping = dict(zip(missing_roles_list, provided_roles_list))
            
            logger.warning(f"检测到角色名不匹配，尝试进行智能映射：{role_mapping}")
            logger.warning(f"原因：生成的对话使用了文本素材中的人名（{missing_roles_list}）作为角色名，而不是指定的角色名（{provided_roles_list}）")
            
            # 应用映射
            mapped_dialogues = [(role_mapping.get(role, role), content) for role, content in dialogues]
            dialogues = mapped_dialogues
            filtered_dialogues = dialogues
        else:
            filtered_dialogues = [d for d in dialogues if d[0] in provided_roles]
            if missing_roles:
                logger.warning(f"以下角色未提供音色文件，将被跳过: {missing_roles}")

        # 如果所有对话都被过滤掉，抛出错误
        if not filtered_dialogues:
            error_msg = f"未能找到任何已提供音色的角色对话。\n"
            error_msg += f"检测到的角色: {sorted(detected_roles)}\n"
            error_msg += f"已提供的角色: {sorted(provided_roles)}\n\n"
            error_msg += f"问题分析：生成的对话文本中使用了文本素材中的人名（如{missing_roles[:3]}等）作为角色名，\n"
            error_msg += f"而不是使用指定的角色名（{sorted(provided_roles)}）。\n\n"
            error_msg += f"解决方案：\n"
            error_msg += f"1. 检查提示词是否正确指定了角色名\n"
            error_msg += f"2. 如果问题持续，可能需要重新生成对话文本"
            raise ValueError(error_msg)

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
    
    def generate_from_text_streaming(
        self,
        text: str,
        role_voices: Optional[Dict[str, str]] = None,
        silence_interval: int = AUDIO_SILENCE_INTERVAL,
        background_music: Optional[Union[str, List[str]]] = None,
        background_volume: float = 0.3,
        background_mode: str = "random",
        verbose: bool = False
    ):
        """
        从文本流式生成播客音频（生成器）
        
        Args:
            text: 包含角色标记的文本
            role_voices: 角色音色映射，如果为None则使用已设置的映射
            silence_interval: 角色切换时的静音间隔（毫秒）
            background_music: 背景音乐文件路径或路径列表（可选）
            background_volume: 背景音乐音量（0.0-1.0），默认0.3
            background_mode: 背景音乐处理模式（"random"/"concat"/"mix"），默认"random"
            verbose: 是否输出详细信息
        
        Yields:
            (segment_index, role_name, audio_segment, is_final):
                - segment_index: 片段索引
                - role_name: 角色名（静音片段为None）
                - audio_segment: 音频张量 (1, samples)，采样率22050
                - is_final: 是否为最后一个片段
        """
        if role_voices:
            self.set_role_voices(role_voices)

        # 解析角色对话
        dialogues = self.text_processor.parse_role_text(text)

        # 创建模块级日志器
        logger = logging.getLogger(__name__)

        if not dialogues:
            raise ValueError("未能从文本中解析出角色对话")

        # 过滤掉那些没有提供音色文件的角色
        provided_roles = set(self.role_voices.keys())
        detected_roles = {d[0] for d in dialogues}
        missing_roles = sorted(detected_roles - provided_roles)
        
        if missing_roles and len(missing_roles) == len(provided_roles):
            provided_roles_list = sorted(list(provided_roles))
            missing_roles_list = sorted(missing_roles)
            role_mapping = dict(zip(missing_roles_list, provided_roles_list))
            
            logger.warning(f"检测到角色名不匹配，尝试进行智能映射：{role_mapping}")
            mapped_dialogues = [(role_mapping.get(role, role), content) for role, content in dialogues]
            dialogues = mapped_dialogues
            filtered_dialogues = dialogues
        else:
            filtered_dialogues = [d for d in dialogues if d[0] in provided_roles]
            if missing_roles:
                logger.warning(f"以下角色未提供音色文件，将被跳过: {missing_roles}")

        if not filtered_dialogues:
            error_msg = f"未能找到任何已提供音色的角色对话。\n"
            error_msg += f"检测到的角色: {sorted(detected_roles)}\n"
            error_msg += f"已提供的角色: {sorted(provided_roles)}"
            raise ValueError(error_msg)

        dialogues = filtered_dialogues
        
        if verbose:
            print(f"解析到 {len(dialogues)} 段对话")
        
        # 确保TTS模型已加载
        self._ensure_tts_loaded()
        
        # 构建说话人信息字典
        speakers = {}
        for role in set(role for role, _ in dialogues):
            voice_file = self.role_voices.get(role)
            if not voice_file:
                raise ValueError(f"角色 '{role}' 没有设置音色文件")
            speakers[role] = {
                "prompt_audio": voice_file,
                "prompt_text": f"这是角色 {role} 的参考音频。"
            }
        
        if verbose:
            print(f"正在使用SoulX-Podcast流式生成多角色播客音频...")
        
        # 预处理背景音乐（如果提供）
        background_audio = None
        background_audio_processed = None
        intro_duration_ms = 5000
        outro_duration_ms = 5000
        current_position = 0  # 当前音频位置（样本数）
        intro_samples = int(AUDIO_SAMPLING_RATE * intro_duration_ms / 1000.0)
        
        if background_music:
            if verbose:
                print("正在加载背景音乐...")
            
            # 处理背景音乐文件
            background_music_list = []
            if isinstance(background_music, str):
                if os.path.exists(background_music):
                    background_music_list = [background_music]
            elif isinstance(background_music, list):
                background_music_list = [f for f in background_music if f and isinstance(f, str) and os.path.exists(f)]
            
            if background_music_list:
                # 加载背景音乐
                from .utils import load_audio, remove_silence_segments
                background_audios = []
                for bg_path in background_music_list:
                    try:
                        bg_audio, _ = load_audio(bg_path, AUDIO_SAMPLING_RATE)
                        background_audios.append(bg_audio)
                    except Exception as e:
                        if verbose:
                            print(f"加载背景音乐失败: {str(e)}")
                
                if background_audios:
                    # 根据模式选择背景音乐
                    if len(background_audios) == 1:
                        background_audio = background_audios[0]
                    elif background_mode == "random":
                        import random
                        background_audio = random.choice(background_audios)
                    else:
                        background_audio = background_audios[0]
                    
                    # 去除静音段
                    background_audio = remove_silence_segments(
                        background_audio, 
                        sr=AUDIO_SAMPLING_RATE, 
                        threshold=0.01, 
                        min_silence_duration_ms=200
                    )
                    
                    # 确保格式正确
                    if background_audio.dim() > 1 and background_audio.shape[0] > 1:
                        background_audio = torch.mean(background_audio, dim=0, keepdim=True)
                    if background_audio.dim() == 1:
                        background_audio = background_audio.unsqueeze(0)
                    
                    if verbose:
                        print(f"背景音乐加载完成，时长: {background_audio.shape[1] / AUDIO_SAMPLING_RATE:.2f}秒")
        
        # 如果有背景音乐，先发送intro片段
        if background_audio is not None:
            intro_samples = int(AUDIO_SAMPLING_RATE * intro_duration_ms / 1000.0)
            intro_fade_in_samples = min(int(AUDIO_SAMPLING_RATE * 1000 / 1000.0), intro_samples)
            
            # 生成intro片段（只有背景音乐）
            bg_start = 0
            bg_end = min(intro_samples, background_audio.shape[1])
            intro_segment = background_audio[:, bg_start:bg_end].clone()
            
            # 如果intro比背景音乐长，循环填充
            if intro_segment.shape[1] < intro_samples:
                repeat_times = (intro_samples // intro_segment.shape[1]) + 1
                intro_segment = intro_segment.repeat(1, repeat_times)[:, :intro_samples]
            
            # 应用淡入效果
            if intro_fade_in_samples > 0:
                fade_in_curve = torch.linspace(0, 1, intro_fade_in_samples, device=intro_segment.device).unsqueeze(0)
                intro_segment[:, :intro_fade_in_samples] *= fade_in_curve
            
            # 应用基础音量
            intro_segment = intro_segment * background_volume
            
            if verbose:
                print(f"生成intro片段，时长: {intro_segment.shape[1] / AUDIO_SAMPLING_RATE:.2f}秒")
            
            yield -1, None, intro_segment, False  # -1表示intro片段
        
        # 使用流式生成
        resampler = None
        dialogue_start_position = intro_samples  # 对话开始位置
        total_dialogue_samples = 0  # 累计对话音频长度（不包括静音）
        total_silence_samples = 0  # 累计静音长度
        segment_counter = 0  # 片段计数器（用于yield）
        
        for segment_index, role_name, audio_segment, is_final in self.tts.infer_multi_speaker_streaming(
            speakers=speakers,
            dialogues=dialogues,
            silence_interval=silence_interval,
            verbose=verbose
        ):
            # 重采样到目标采样率（从24000到22050）
            if audio_segment.shape[1] > 0:  # 确保不是空音频
                if resampler is None:
                    resampler = torchaudio.transforms.Resample(24000, AUDIO_SAMPLING_RATE)
                
                # 确保音频格式正确
                if audio_segment.dim() == 1:
                    audio_segment = audio_segment.unsqueeze(0)
                elif audio_segment.dim() > 1 and audio_segment.shape[0] > 1:
                    audio_segment = torch.mean(audio_segment, dim=0, keepdim=True)
                
                # 重采样
                audio_segment = resampler(audio_segment)
                
                # 累计长度
                if role_name is not None:
                    # 对话片段
                    total_dialogue_samples += audio_segment.shape[1]
                else:
                    # 静音片段
                    total_silence_samples += audio_segment.shape[1]
            else:
                # 空音频片段，跳过混合
                yield segment_counter, role_name, audio_segment, is_final
                segment_counter += 1
                continue
            
            # 如果有背景音乐，进行流式混合
            if background_audio is not None and audio_segment.shape[1] > 0:
                segment_len = audio_segment.shape[1]
                
                # 计算当前片段在整体音频中的位置
                if role_name is not None:
                    # 对话片段：intro + 之前的对话 + 之前的静音
                    segment_start = dialogue_start_position + (total_dialogue_samples - segment_len) + total_silence_samples
                else:
                    # 静音片段：intro + 所有对话 + 之前的静音
                    segment_start = dialogue_start_position + total_dialogue_samples + (total_silence_samples - segment_len)
                
                segment_end = segment_start + segment_len
                
                # 从背景音乐中提取对应片段（循环播放）
                bg_start = segment_start % background_audio.shape[1]
                bg_end = segment_end % background_audio.shape[1]
                
                if bg_end > bg_start:
                    # 正常情况：从背景音乐中提取连续片段
                    bg_segment = background_audio[:, bg_start:bg_end].clone()
                else:
                    # 跨越循环边界：需要拼接
                    part1 = background_audio[:, bg_start:].clone()
                    part2 = background_audio[:, :bg_end].clone()
                    bg_segment = torch.cat([part1, part2], dim=1)
                    # 如果提取的长度不匹配，调整
                    if bg_segment.shape[1] > segment_len:
                        bg_segment = bg_segment[:, :segment_len]
                    elif bg_segment.shape[1] < segment_len:
                        # 如果背景音乐片段不够长，循环填充
                        repeat_times = (segment_len // bg_segment.shape[1]) + 1
                        bg_segment = bg_segment.repeat(1, repeat_times)[:, :segment_len]
                
                # 确定当前片段的位置阶段
                # 由于intro已经单独发送，这里不会再有intro片段
                is_intro = False  # 不会再有intro，因为已经单独发送
                is_outro = False  # outro会在最后单独发送
                is_dialogue = True  # 所有从TTS来的片段都是对话或静音
                
                # 创建背景音乐音量曲线
                bg_volume_curve = torch.ones(1, segment_len, device=audio_segment.device, dtype=audio_segment.dtype)
                
                if is_dialogue:
                    # 对话阶段：ducking效果（压低背景音乐）
                    ducking_ratio = 0.15  # 降低到15%
                    bg_volume_curve[:, :] = ducking_ratio
                    
                    # 在对话开始和结束时添加平滑过渡
                    transition_samples = min(int(AUDIO_SAMPLING_RATE * 0.2), segment_len // 4)
                    dialogue_relative_start = segment_start - dialogue_start_position
                    
                    if dialogue_relative_start < transition_samples:
                        # 对话开始：从正常音量过渡到压低音量
                        transition_len = min(transition_samples - dialogue_relative_start, segment_len)
                        if transition_len > 0:
                            transition_curve = torch.linspace(1.0, ducking_ratio, transition_len, device=audio_segment.device).unsqueeze(0)
                            bg_volume_curve[:, :transition_len] = transition_curve
                    
                    # 对话结束时的过渡（最后一个对话片段）
                    if is_final and role_name is not None:
                        # 对话结束：从压低音量过渡到正常音量（为outro做准备）
                        dialogue_end_position = dialogue_start_position + total_dialogue_samples
                        if segment_end >= dialogue_end_position - transition_samples:
                            transition_start = max(0, dialogue_end_position - transition_samples - segment_start)
                            transition_len = min(segment_len - transition_start, transition_samples)
                            if transition_len > 0:
                                transition_curve = torch.linspace(ducking_ratio, 1.0, transition_len, device=audio_segment.device).unsqueeze(0)
                                bg_volume_curve[:, transition_start:transition_start + transition_len] = transition_curve
                
                # 应用背景音量曲线和基础音量
                bg_segment = bg_segment * bg_volume_curve * background_volume
                
                # 混合音频
                mixed_segment = audio_segment + bg_segment
                
                # 归一化避免削波
                max_val = torch.abs(mixed_segment).max()
                if max_val > 1.0:
                    mixed_segment = mixed_segment / max_val
                
                audio_segment = mixed_segment
                
                if verbose and segment_index % 10 == 0:
                    print(f"已混合片段 {segment_index}，位置: {segment_start/AUDIO_SAMPLING_RATE:.2f}s - {segment_end/AUDIO_SAMPLING_RATE:.2f}s")
            
            yield segment_counter, role_name, audio_segment, is_final
            segment_counter += 1
            
            # 如果是最后一个片段，添加outro部分（如果启用了背景音乐）
            if is_final and background_audio is not None:
                outro_samples = int(AUDIO_SAMPLING_RATE * outro_duration_ms / 1000.0)
                outro_start = dialogue_start_position + total_dialogue_samples + total_silence_samples
                
                # 生成outro片段（一次性生成整个outro）
                outro_segment_len = outro_samples
                
                # 从背景音乐中提取outro片段（循环播放）
                bg_start = outro_start % background_audio.shape[1]
                bg_end = (outro_start + outro_segment_len) % background_audio.shape[1]
                
                if bg_end > bg_start:
                    bg_segment = background_audio[:, bg_start:bg_end].clone()
                else:
                    part1 = background_audio[:, bg_start:].clone()
                    part2 = background_audio[:, :bg_end].clone()
                    bg_segment = torch.cat([part1, part2], dim=1)
                
                # 如果背景音乐片段不够长，循环填充
                if bg_segment.shape[1] < outro_segment_len:
                    repeat_times = (outro_segment_len // bg_segment.shape[1]) + 1
                    bg_segment = bg_segment.repeat(1, repeat_times)[:, :outro_segment_len]
                elif bg_segment.shape[1] > outro_segment_len:
                    bg_segment = bg_segment[:, :outro_segment_len]
                
                # 应用淡出效果
                outro_fade_out_samples = min(int(AUDIO_SAMPLING_RATE * 1000 / 1000.0), outro_samples)
                if outro_fade_out_samples > 0:
                    fade_out_start = outro_segment_len - outro_fade_out_samples
                    fade_out_curve = torch.linspace(1, 0, outro_fade_out_samples, device=bg_segment.device).unsqueeze(0)
                    bg_segment[:, fade_out_start:] *= fade_out_curve
                
                # 应用基础音量
                bg_segment = bg_segment * background_volume
                
                if verbose:
                    print(f"生成outro片段，时长: {bg_segment.shape[1] / AUDIO_SAMPLING_RATE:.2f}秒")
                
                # 输出outro片段（只有背景音乐，没有对话）
                yield segment_counter, None, bg_segment, True
                segment_counter += 1
    
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
            max_tokens=3000  # 增加到3000以支持更长的对话（5-6分钟播客）
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
            max_tokens=3000  # 增加到3000以支持更长的对话（5-6分钟播客）
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
            max_tokens=3500  # 增加到3500以支持更长的对话（5-6分钟播客）
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

