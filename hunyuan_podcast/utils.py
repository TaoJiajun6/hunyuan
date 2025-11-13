"""
工具函数模块
提供音频处理、文本格式化、文件管理等功能
"""
import os
import torch
import torchaudio
from typing import List, Optional, Tuple
from pathlib import Path
import numpy as np
from .config import AUDIO_SAMPLING_RATE, AUDIO_SILENCE_INTERVAL, OUTPUT_DIR

# 尝试导入 librosa，如果失败则提供错误提示
try:
    import librosa
    HAS_LIBROSA = True
except ImportError:
    HAS_LIBROSA = False
    print("⚠️  警告：librosa 未安装，某些音频处理功能可能受限")
    print("💡 安装方法：pip install librosa")


def ensure_dir(directory: str) -> None:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        directory: 目录路径
    """
    os.makedirs(directory, exist_ok=True)


def get_output_path(filename: Optional[str] = None) -> str:
    """
    获取输出文件路径
    
    Args:
        filename: 文件名，如果为None则自动生成
    
    Returns:
        完整的输出文件路径
    """
    ensure_dir(OUTPUT_DIR)
    if filename is None:
        import time
        filename = f"podcast_{int(time.time())}.wav"
    return os.path.join(OUTPUT_DIR, filename)


def load_audio(file_path: str, target_sr: int = AUDIO_SAMPLING_RATE) -> Tuple[torch.Tensor, int]:
    """
    加载音频文件
    
    Args:
        file_path: 音频文件路径
        target_sr: 目标采样率
    
    Returns:
        (音频张量, 采样率)
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"音频文件不存在: {file_path}")
    
    audio, sr = torchaudio.load(file_path)
    
    # 如果是多声道，转换为单声道
    if audio.shape[0] > 1:
        audio = torch.mean(audio, dim=0, keepdim=True)
    
    # 重采样到目标采样率
    if sr != target_sr:
        resampler = torchaudio.transforms.Resample(sr, target_sr)
        audio = resampler(audio)
    
    return audio, target_sr


def create_silence(duration_ms: int = AUDIO_SILENCE_INTERVAL, sr: int = AUDIO_SAMPLING_RATE) -> torch.Tensor:
    """
    创建静音片段
    
    Args:
        duration_ms: 静音时长（毫秒）
        sr: 采样率
    
    Returns:
        静音音频张量
    """
    duration_samples = int(sr * duration_ms / 1000.0)
    silence = torch.zeros(1, duration_samples)
    return silence


def concatenate_audios(
    audio_list: List[torch.Tensor],
    silence_intervals: Optional[List[int]] = None,
    sr: int = AUDIO_SAMPLING_RATE
) -> torch.Tensor:
    """
    拼接多个音频片段
    
    Args:
        audio_list: 音频片段列表
        silence_intervals: 静音间隔列表（毫秒），如果为None则使用默认值
        sr: 采样率
    
    Returns:
        拼接后的音频张量
    """
    if not audio_list:
        raise ValueError("音频列表不能为空")
    
    result = []
    default_silence = create_silence(AUDIO_SILENCE_INTERVAL, sr)
    
    for i, audio in enumerate(audio_list):
        # 确保音频是单声道
        if audio.shape[0] > 1:
            audio = torch.mean(audio, dim=0, keepdim=True)
        
        result.append(audio)
        
        # 在音频之间添加静音（除了最后一个）
        if i < len(audio_list) - 1:
            if silence_intervals and i < len(silence_intervals):
                silence = create_silence(silence_intervals[i], sr)
            else:
                silence = default_silence
            result.append(silence)
    
    # 拼接所有音频
    concatenated = torch.cat(result, dim=1)
    return concatenated


def save_audio(audio: torch.Tensor, output_path: str, sr: int = AUDIO_SAMPLING_RATE) -> None:
    """
    保存音频文件
    
    Args:
        audio: 音频张量
        output_path: 输出路径
        sr: 采样率
    """
    # 确保输出路径是绝对路径
    output_path = os.path.abspath(output_path)
    ensure_dir(os.path.dirname(output_path))
    
    # 确保音频格式正确
    if audio.dim() == 1:
        audio = audio.unsqueeze(0)
    
    # 转换为int16格式
    audio_int16 = (audio * 32767.0).clamp(-32767, 32767).to(torch.int16)
    
    torchaudio.save(output_path, audio_int16, sr)
    print(f"✅ 音频已保存到: {output_path}")
    print(f"   文件大小: {os.path.getsize(output_path) / (1024*1024):.2f} MB")


def normalize_audio(audio: torch.Tensor) -> torch.Tensor:
    """
    归一化音频
    
    Args:
        audio: 音频张量
    
    Returns:
        归一化后的音频张量
    """
    max_val = torch.abs(audio).max()
    if max_val > 0:
        audio = audio / max_val
    return audio


def trim_silence(audio: torch.Tensor, sr: int = AUDIO_SAMPLING_RATE, threshold: float = 0.01) -> torch.Tensor:
    """
    去除音频首尾的静音
    
    Args:
        audio: 音频张量
        sr: 采样率
        threshold: 静音阈值
    
    Returns:
        处理后的音频张量
    """
    if audio.dim() > 1:
        audio = audio.squeeze()
    
    audio_np = audio.numpy() if isinstance(audio, torch.Tensor) else audio
    
    # 找到非静音的起始和结束位置
    non_silent = np.abs(audio_np) > threshold
    
    if non_silent.any():
        start = np.argmax(non_silent)
        end = len(non_silent) - np.argmax(non_silent[::-1])
        audio_np = audio_np[start:end]
    
    if isinstance(audio, torch.Tensor):
        return torch.from_numpy(audio_np)
    return audio_np


def mix_audio_with_background(
    foreground: torch.Tensor,
    background: torch.Tensor,
    background_volume: float = 0.3,
    fade_in_ms: int = 500,
    fade_out_ms: int = 500,
    background_mode: str = "single",
    enable_ducking: bool = True,
    ducking_threshold: float = 0.01,
    ducking_ratio: float = 0.3
) -> torch.Tensor:
    """
    将前景音频与背景音频混合，支持ducking效果（对话时自动压低背景音乐）
    
    Args:
        foreground: 前景音频（主音频）
        background: 背景音频（如背景音乐），可以是单个音频或列表
        background_volume: 背景音量（0.0-1.0），默认0.3
        fade_in_ms: 淡入时长（毫秒）
        fade_out_ms: 淡出时长（毫秒）
        background_mode: 背景音乐处理模式
            - "single": 单个背景音乐（默认）
            - "random": 从多个背景音乐中随机选择一个
            - "concat": 按顺序拼接多个背景音乐
            - "mix": 混合多个背景音乐
        enable_ducking: 是否启用ducking效果（对话时自动压低背景音乐），默认True
        ducking_threshold: ducking触发阈值（前景音频音量超过此值时触发），默认0.01
        ducking_ratio: ducking时背景音乐音量降低比例（0.0-1.0），默认0.3（降低到30%）
    
    Returns:
        混合后的音频张量
    """
    # 如果是列表，处理多个背景音乐
    if isinstance(background, list):
        if len(background) == 0:
            return foreground
        elif len(background) == 1:
            background = background[0]
        else:
            # 根据模式处理多个背景音乐
            if background_mode == "random":
                import random
                background = random.choice(background)
            elif background_mode == "concat":
                # 拼接所有背景音乐
                background_list = []
                for bg in background:
                    if bg.dim() > 1 and bg.shape[0] > 1:
                        bg = torch.mean(bg, dim=0, keepdim=True)
                    if bg.dim() == 1:
                        bg = bg.unsqueeze(0)
                    background_list.append(bg)
                background = concatenate_audios(background_list, silence_intervals=[200] * (len(background_list) - 1))
            elif background_mode == "mix":
                # 混合所有背景音乐
                max_len = max(bg.shape[1] if bg.dim() > 1 else len(bg) for bg in background)
                mixed_bg = None
                for bg in background:
                    if bg.dim() > 1 and bg.shape[0] > 1:
                        bg = torch.mean(bg, dim=0, keepdim=True)
                    if bg.dim() == 1:
                        bg = bg.unsqueeze(0)
                    if bg.shape[1] < max_len:
                        repeat_times = (max_len // bg.shape[1]) + 1
                        bg = bg.repeat(1, repeat_times)
                    bg = bg[:, :max_len]
                    if mixed_bg is None:
                        mixed_bg = bg
                    else:
                        mixed_bg = mixed_bg + bg
                if mixed_bg is not None:
                    max_val = torch.abs(mixed_bg).max()
                    if max_val > 0:
                        mixed_bg = mixed_bg / max_val
                background = mixed_bg if mixed_bg is not None else background[0]
    
    # 确保都是单声道
    if foreground.dim() > 1 and foreground.shape[0] > 1:
        foreground = torch.mean(foreground, dim=0, keepdim=True)
    if background.dim() > 1 and background.shape[0] > 1:
        background = torch.mean(background, dim=0, keepdim=True)
    
    # 确保都是2D张量 (1, samples)
    if foreground.dim() == 1:
        foreground = foreground.unsqueeze(0)
    if background.dim() == 1:
        background = background.unsqueeze(0)
    
    foreground_len = foreground.shape[1]
    background_len = background.shape[1]
    
    # 如果背景音频比前景短，循环播放
    if background_len < foreground_len:
        repeat_times = (foreground_len // background_len) + 1
        background = background.repeat(1, repeat_times)
    
    # 裁剪背景音频到前景长度
    background = background[:, :foreground_len]
    
    # 应用淡入淡出效果
    sr = AUDIO_SAMPLING_RATE
    fade_in_samples = int(sr * fade_in_ms / 1000.0)
    fade_out_samples = int(sr * fade_out_ms / 1000.0)
    
    # 创建淡入淡出曲线
    fade_in_curve = torch.linspace(0, 1, fade_in_samples).unsqueeze(0)
    fade_out_curve = torch.linspace(1, 0, fade_out_samples).unsqueeze(0)
    
    # 应用淡入
    if fade_in_samples > 0 and fade_in_samples < foreground_len:
        background[:, :fade_in_samples] *= fade_in_curve
    
    # 应用淡出
    if fade_out_samples > 0 and fade_out_samples < foreground_len:
        start_fade_out = foreground_len - fade_out_samples
        background[:, start_fade_out:] *= fade_out_curve
    
    # 调整背景音量
    background = background * background_volume
    
    # 如果启用ducking效果，根据前景音频音量动态调整背景音量
    if enable_ducking:
        # 计算前景音频的包络（使用滑动窗口平滑）
        window_size = int(sr * 0.05)  # 50ms窗口
        if window_size < 1:
            window_size = 1
        
        # 计算前景音频的绝对值（音量）
        foreground_abs = torch.abs(foreground)
        
        # 使用平均池化创建平滑的包络
        if foreground_abs.shape[1] > window_size:
            # 使用简单的移动平均来创建平滑的包络
            # 将音频分成多个窗口，计算每个窗口的平均值
            num_windows = (foreground_len + window_size - 1) // window_size
            envelope_samples = []
            
            for i in range(num_windows):
                start = i * window_size
                end = min(start + window_size, foreground_len)
                window_avg = foreground_abs[:, start:end].mean()
                envelope_samples.append(window_avg)
            
            # 创建包络张量
            foreground_envelope = torch.tensor(envelope_samples, device=foreground_abs.device, dtype=foreground_abs.dtype)
            
            # 插值回原始长度（使用简单的线性插值）
            if len(envelope_samples) > 1:
                # 使用numpy进行插值，然后转回tensor
                import numpy as np
                envelope_np = foreground_envelope.cpu().numpy()
                indices = np.linspace(0, len(envelope_np) - 1, foreground_len)
                envelope_interp = np.interp(indices, np.arange(len(envelope_np)), envelope_np)
                foreground_envelope = torch.from_numpy(envelope_interp).to(foreground_abs.device).unsqueeze(0)
            else:
                foreground_envelope = foreground_envelope.unsqueeze(0).repeat(1, foreground_len)
        else:
            foreground_envelope = foreground_abs
        
        # 归一化包络到[0, 1]
        max_envelope = foreground_envelope.max()
        if max_envelope > 0:
            foreground_envelope = foreground_envelope / max_envelope
        
        # 创建ducking曲线：当前景音频音量高时，背景音量降低
        # 使用平滑的过渡曲线
        ducking_curve = torch.ones_like(foreground_envelope)
        # 当前景音频超过阈值时，应用ducking
        mask = foreground_envelope > ducking_threshold
        if mask.any():
            # 计算ducking强度（前景音量越高，ducking越强）
            ducking_strength = (foreground_envelope - ducking_threshold) / (1.0 - ducking_threshold)
            ducking_strength = torch.clamp(ducking_strength, 0, 1)
            # 应用ducking：背景音量降低到 ducking_ratio
            ducking_curve = 1.0 - ducking_strength * (1.0 - ducking_ratio)
        
        # 应用ducking曲线到背景音乐
        background = background * ducking_curve
    
    # 混合音频（简单相加，然后归一化避免削波）
    mixed = foreground + background
    
    # 归一化到[-1, 1]范围
    max_val = torch.abs(mixed).max()
    if max_val > 1.0:
        mixed = mixed / max_val
    
    return mixed


def load_multiple_audios(
    file_paths: List[str],
    target_sr: int = AUDIO_SAMPLING_RATE,
    mode: str = "random"
) -> torch.Tensor:
    """
    加载多个音频文件并处理
    
    Args:
        file_paths: 音频文件路径列表
        target_sr: 目标采样率
        mode: 处理模式
            - "random": 随机选择一个文件
            - "concat": 按顺序拼接所有文件
            - "mix": 混合所有文件（仅适用于背景音乐）
    
    Returns:
        处理后的音频张量
    """
    if not file_paths:
        raise ValueError("文件路径列表不能为空")
    
    # 过滤掉不存在的文件
    valid_paths = [p for p in file_paths if p and os.path.exists(p)]
    if not valid_paths:
        raise ValueError("没有有效的音频文件")
    
    if mode == "random":
        # 随机选择一个文件
        import random
        selected_path = random.choice(valid_paths)
        return load_audio(selected_path, target_sr)[0]
    
    elif mode == "concat":
        # 按顺序拼接所有文件
        audio_list = []
        for path in valid_paths:
            audio, _ = load_audio(path, target_sr)
            audio_list.append(audio)
        return concatenate_audios(audio_list, silence_intervals=[200] * (len(audio_list) - 1), sr=target_sr)
    
    elif mode == "mix":
        # 混合所有文件（平均混合）
        audio_list = []
        max_len = 0
        for path in valid_paths:
            audio, _ = load_audio(path, target_sr)
            audio_list.append(audio)
            # 确保都是单声道
            if audio.dim() > 1 and audio.shape[0] > 1:
                audio = torch.mean(audio, dim=0, keepdim=True)
            if audio.dim() == 1:
                audio = audio.unsqueeze(0)
            max_len = max(max_len, audio.shape[1])
        
        # 将所有音频调整到相同长度并混合
        mixed = None
        for audio in audio_list:
            # 确保都是单声道
            if audio.dim() > 1 and audio.shape[0] > 1:
                audio = torch.mean(audio, dim=0, keepdim=True)
            if audio.dim() == 1:
                audio = audio.unsqueeze(0)
            
            # 如果音频比最长音频短，循环播放
            if audio.shape[1] < max_len:
                repeat_times = (max_len // audio.shape[1]) + 1
                audio = audio.repeat(1, repeat_times)
            audio = audio[:, :max_len]
            
            if mixed is None:
                mixed = audio
            else:
                mixed = mixed + audio
        
        # 归一化
        if mixed is not None:
            max_val = torch.abs(mixed).max()
            if max_val > 0:
                mixed = mixed / max_val
        
        return mixed if mixed is not None else audio_list[0]
    
    else:
        raise ValueError(f"不支持的模式: {mode}")


def add_intro_outro_music(
    main_audio: torch.Tensor,
    intro_music: Optional[torch.Tensor] = None,
    outro_music: Optional[torch.Tensor] = None,
    intro_fade_out_ms: int = 1000,
    outro_fade_in_ms: int = 1000,
    sr: int = AUDIO_SAMPLING_RATE
) -> torch.Tensor:
    """
    为主音频添加开场和结尾音乐
    
    Args:
        main_audio: 主音频（播客对话内容）
        intro_music: 开场音乐（可选，可以是单个音频或列表）
        outro_music: 结尾音乐（可选，可以是单个音频或列表）
        intro_fade_out_ms: 开场音乐淡出时长（毫秒）
        outro_fade_in_ms: 结尾音乐淡入时长（毫秒）
        sr: 采样率
    
    Returns:
        添加了开场和结尾音乐的完整音频
    """
    audio_segments = []
    
    # 添加开场音乐
    if intro_music is not None:
        # 如果是列表，处理多个开场音乐
        if isinstance(intro_music, list):
            if len(intro_music) > 0:
                # 随机选择一个或拼接
                import random
                if len(intro_music) == 1:
                    intro_music = intro_music[0]
                else:
                    # 随机选择一个
                    intro_music = random.choice(intro_music)
        
        if intro_music is not None:
            # 确保开场音乐是单声道
            if intro_music.dim() > 1 and intro_music.shape[0] > 1:
                intro_music = torch.mean(intro_music, dim=0, keepdim=True)
            if intro_music.dim() == 1:
                intro_music = intro_music.unsqueeze(0)
            
            # 应用淡出效果
            if intro_fade_out_ms > 0:
                fade_out_samples = int(sr * intro_fade_out_ms / 1000.0)
                if fade_out_samples < intro_music.shape[1]:
                    fade_out_curve = torch.linspace(1, 0, fade_out_samples).unsqueeze(0)
                    intro_music[:, -fade_out_samples:] *= fade_out_curve
            
            audio_segments.append(intro_music)
            # 开场音乐后添加短暂静音
            audio_segments.append(create_silence(500, sr))
    
    # 添加主音频
    audio_segments.append(main_audio)
    
    # 添加结尾音乐
    if outro_music is not None:
        # 如果是列表，处理多个结尾音乐
        if isinstance(outro_music, list):
            if len(outro_music) > 0:
                # 随机选择一个或拼接
                import random
                if len(outro_music) == 1:
                    outro_music = outro_music[0]
                else:
                    # 随机选择一个
                    outro_music = random.choice(outro_music)
        
        if outro_music is not None:
            # 确保结尾音乐是单声道
            if outro_music.dim() > 1 and outro_music.shape[0] > 1:
                outro_music = torch.mean(outro_music, dim=0, keepdim=True)
            if outro_music.dim() == 1:
                outro_music = outro_music.unsqueeze(0)
            
            # 主音频后添加短暂静音
            audio_segments.append(create_silence(500, sr))
            
            # 应用淡入效果
            if outro_fade_in_ms > 0:
                fade_in_samples = int(sr * outro_fade_in_ms / 1000.0)
                if fade_in_samples < outro_music.shape[1]:
                    fade_in_curve = torch.linspace(0, 1, fade_in_samples).unsqueeze(0)
                    outro_music[:, :fade_in_samples] *= fade_in_curve
            
            audio_segments.append(outro_music)
    
    # 拼接所有音频
    if len(audio_segments) == 1:
        return audio_segments[0]
    
    final_audio = torch.cat(audio_segments, dim=1)
    return final_audio

