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
    print("💡 安装方法：")
    print("   如果使用 uv 环境: cd index-tts && uv pip install librosa")
    print("   如果使用标准环境: pip install librosa")


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
    fade_out_ms: int = 500
) -> torch.Tensor:
    """
    将前景音频与背景音频混合
    
    Args:
        foreground: 前景音频（主音频）
        background: 背景音频（如背景音乐）
        background_volume: 背景音量（0.0-1.0），默认0.3
        fade_in_ms: 淡入时长（毫秒）
        fade_out_ms: 淡出时长（毫秒）
    
    Returns:
        混合后的音频张量
    """
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
    
    # 混合音频（简单相加，然后归一化避免削波）
    mixed = foreground + background
    
    # 归一化到[-1, 1]范围
    max_val = torch.abs(mixed).max()
    if max_val > 1.0:
        mixed = mixed / max_val
    
    return mixed


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
        intro_music: 开场音乐（可选）
        outro_music: 结尾音乐（可选）
        intro_fade_out_ms: 开场音乐淡出时长（毫秒）
        outro_fade_in_ms: 结尾音乐淡入时长（毫秒）
        sr: 采样率
    
    Returns:
        添加了开场和结尾音乐的完整音频
    """
    audio_segments = []
    
    # 添加开场音乐
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

