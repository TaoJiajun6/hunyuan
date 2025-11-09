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

