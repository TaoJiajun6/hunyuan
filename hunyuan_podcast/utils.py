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


def sanitize_filename(title: str, max_length: int = 50) -> str:
    """
    将标题转换为安全的文件名
    
    Args:
        title: 原始标题
        max_length: 最大长度（不包括扩展名）
    
    Returns:
        安全的文件名（不含扩展名）
    """
    import re
    # 移除或替换非法字符
    # Windows 不允许的字符：< > : " / \ | ? *
    # 也移除其他可能有问题的字符
    filename = re.sub(r'[<>:"/\\|?*]', '', title)
    # 移除首尾空格和点
    filename = filename.strip(' .')
    # 替换多个空格为单个下划线
    filename = re.sub(r'\s+', '_', filename)
    # 限制长度（保留一些空间用于可能的冲突后缀）
    if len(filename) > max_length - 10:
        filename = filename[:max_length - 10]
    # 如果文件名为空，使用时间戳
    if not filename:
        import time
        filename = f"podcast_{int(time.time())}"
    return filename


def get_output_path(filename: Optional[str] = None, title: Optional[str] = None, podcast_id: Optional[str] = None) -> str:
    """
    获取输出文件路径
    
    Args:
        filename: 文件名（不含扩展名），如果为None则自动生成
        title: 播客标题
        podcast_id: 播客ID（可选），如果提供且filename为None，将使用ID生成文件名
    
    Returns:
        完整的输出文件路径
    """
    ensure_dir(OUTPUT_DIR)
    if filename is None:
        if podcast_id:
            # 使用ID生成文件名
            # 清理ID中的特殊字符，确保文件名安全
            import re
            safe_id = re.sub(r'[<>:"/\\|?*]', '', str(podcast_id))
            filename = f"{safe_id}.wav"
        else:
            # 如果没有ID，使用时间戳生成文件名（不使用title）
            import time
            filename = f"podcast_{int(time.time())}.wav"
    elif not filename.endswith('.wav'):
        # 如果提供了文件名但没有扩展名，添加扩展名
        filename = f"{filename}.wav"
    
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


def remove_silence_segments(
    audio: torch.Tensor,
    sr: int = AUDIO_SAMPLING_RATE,
    threshold: float = 0.01,
    min_silence_duration_ms: int = 200
) -> torch.Tensor:
    """
    去除音频中的静音段（包括中间的静音）
    
    Args:
        audio: 音频张量，形状为 (1, samples) 或 (samples,)
        sr: 采样率
        threshold: 静音阈值（绝对值）
        min_silence_duration_ms: 最小静音时长（毫秒），小于此值的静音段不会被去除
    
    Returns:
        处理后的音频张量
    """
    # 确保是1D张量
    if audio.dim() > 1:
        if audio.shape[0] == 1:
            audio = audio.squeeze(0)
        else:
            audio = torch.mean(audio, dim=0)
    
    audio_np = audio.cpu().numpy() if isinstance(audio, torch.Tensor) else audio
    
    # 找到非静音的位置
    non_silent = np.abs(audio_np) > threshold
    
    # 计算最小静音样本数
    min_silence_samples = int(sr * min_silence_duration_ms / 1000.0)
    
    # 找到所有非静音段
    if not non_silent.any():
        # 如果全部是静音，返回空音频
        return torch.zeros(1, 0) if isinstance(audio, torch.Tensor) else np.array([])
    
    # 找到静音段的开始和结束
    # 使用差分来找到静音段的边界
    diff = np.diff(non_silent.astype(int))
    silence_starts = np.where(diff == -1)[0] + 1  # 从非静音到静音
    silence_ends = np.where(diff == 1)[0] + 1     # 从静音到非静音
    
    # 处理开头和结尾
    if not non_silent[0]:
        # 开头是静音
        silence_starts = np.concatenate([[0], silence_starts])
    if not non_silent[-1]:
        # 结尾是静音
        silence_ends = np.concatenate([silence_ends, [len(non_silent)]])
    
    # 过滤掉太短的静音段
    valid_segments = []
    last_end = 0
    
    for start, end in zip(silence_starts, silence_ends):
        silence_duration = end - start
        if silence_duration >= min_silence_samples:
            # 保留前面的非静音段
            if start > last_end:
                valid_segments.append((last_end, start))
            last_end = end
        # 如果静音段太短，不处理（保留）
    
    # 添加最后一段
    if last_end < len(audio_np):
        valid_segments.append((last_end, len(audio_np)))
    
    # 如果没有有效的非静音段，返回空音频
    if not valid_segments:
        return torch.zeros(1, 0) if isinstance(audio, torch.Tensor) else np.array([])
    
    # 拼接所有非静音段
    result_segments = []
    for start, end in valid_segments:
        result_segments.append(audio_np[start:end])
    
    if result_segments:
        result = np.concatenate(result_segments)
    else:
        result = np.array([])
    
    # 转换回tensor
    if isinstance(audio, torch.Tensor):
        result = torch.from_numpy(result).unsqueeze(0)
    
    return result


def mix_audio_with_background(
    foreground: torch.Tensor,
    background: torch.Tensor,
    background_volume: float = 0.3,
    fade_in_ms: int = 500,
    fade_out_ms: int = 500,
    background_mode: str = "single",
    enable_ducking: bool = True,
    ducking_threshold: float = 0.02,  # 提高阈值，让对话间隔更明显
    ducking_ratio: float = 0.15,  # 降低到15%，让对话时音乐更明显地被压低
    intro_duration_ms: int = 5000,
    outro_duration_ms: int = 5000,
    remove_background_silence: bool = True
) -> torch.Tensor:
    """
    将前景音频与背景音频混合，支持ducking效果（对话时自动压低背景音乐）
    实现策略：
    1. 先播放背景音乐几秒钟（intro，背景音乐正常音量）
    2. 慢慢引入角色对话（淡入效果）
    3. 对话时背景音乐音量始终压低（ducking效果，不管是否有对话内容）
    4. 如果背景音乐有连接，截掉背景音的空白部分
    5. 对话结束后，音乐音量恢复（背景音乐正常音量）
    6. 播放几秒钟才结束（outro，背景音乐正常音量）
    
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
        ducking_threshold: ducking触发阈值（已废弃，保留用于兼容性），默认0.02
        ducking_ratio: ducking时背景音乐音量降低比例（0.0-1.0），默认0.15（降低到15%，对话过程中始终保持压低）
        intro_duration_ms: 开场音乐播放时长（毫秒），默认5000（5秒）
        outro_duration_ms: 结束音乐播放时长（毫秒），默认5000（5秒）
        remove_background_silence: 是否去除背景音乐中的静音段，默认True
    
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
    
    # 去除背景音乐中的静音段（如果启用）
    if remove_background_silence:
        background = remove_silence_segments(background, sr=AUDIO_SAMPLING_RATE, threshold=0.01, min_silence_duration_ms=200)
        background_len = background.shape[1] if background.dim() > 1 else len(background)
        if background_len == 0:
            # 如果背景音乐全部是静音，返回前景音频
            return foreground
    
    foreground_len = foreground.shape[1]
    background_len = background.shape[1]
    sr = AUDIO_SAMPLING_RATE
    
    # 计算intro和outro的样本数
    intro_samples = int(sr * intro_duration_ms / 1000.0)
    outro_samples = int(sr * outro_duration_ms / 1000.0)
    
    # 计算总长度：intro + 对话 + outro
    total_len = intro_samples + foreground_len + outro_samples
    
    # 准备背景音乐：需要覆盖整个长度（intro + 对话 + outro）
    # 如果背景音频比总长度短，循环播放
    if background_len < total_len:
        repeat_times = (total_len // background_len) + 1
        background = background.repeat(1, repeat_times)
    
    # 裁剪背景音频到总长度
    background = background[:, :total_len]
    
    # 创建前景音频：在intro和outro部分添加静音
    foreground_padded = torch.zeros(1, total_len, device=foreground.device, dtype=foreground.dtype)
    foreground_padded[:, intro_samples:intro_samples + foreground_len] = foreground
    
    # 对前景音频应用淡入效果（在对话开始时）
    dialogue_fade_in_samples = int(sr * fade_in_ms / 1000.0)
    if dialogue_fade_in_samples > 0 and dialogue_fade_in_samples < foreground_len:
        dialogue_fade_in_curve = torch.linspace(0, 1, dialogue_fade_in_samples, device=foreground.device).unsqueeze(0)
        foreground_padded[:, intro_samples:intro_samples + dialogue_fade_in_samples] *= dialogue_fade_in_curve
    
    # 对前景音频应用淡出效果（在对话结束时）
    dialogue_fade_out_samples = int(sr * fade_out_ms / 1000.0)
    if dialogue_fade_out_samples > 0 and dialogue_fade_out_samples < foreground_len:
        dialogue_fade_out_start = intro_samples + foreground_len - dialogue_fade_out_samples
        dialogue_fade_out_curve = torch.linspace(1, 0, dialogue_fade_out_samples, device=foreground.device).unsqueeze(0)
        foreground_padded[:, dialogue_fade_out_start:intro_samples + foreground_len] *= dialogue_fade_out_curve
    
    # 创建背景音乐音量曲线
    background_volume_curve = torch.ones(1, total_len, device=background.device, dtype=background.dtype)
    
    # Intro部分：背景音乐从0淡入到正常音量
    intro_fade_in_samples = min(intro_samples, int(sr * 1000 / 1000.0))  # 1秒淡入
    if intro_fade_in_samples > 0:
        intro_fade_in_curve = torch.linspace(0, 1, intro_fade_in_samples, device=background.device).unsqueeze(0)
        background_volume_curve[:, :intro_fade_in_samples] = intro_fade_in_curve
        # Intro剩余部分保持正常音量
        background_volume_curve[:, intro_fade_in_samples:intro_samples] = 1.0
    
    # 对话部分：应用ducking效果（如果启用）
    dialogue_start = intro_samples
    dialogue_end = intro_samples + foreground_len
    
    if enable_ducking:
        # 对话部分：始终压低背景音乐音量
        # 在对话开始和结束时添加平滑过渡，避免音量突变
        dialogue_len = dialogue_end - dialogue_start
        
        # 创建对话部分的ducking曲线：始终压低到ducking_ratio
        ducking_curve = torch.ones(1, dialogue_len, device=background.device, dtype=background.dtype) * ducking_ratio
        
        # 在对话开始和结束时添加淡入/淡出过渡，让音量变化更平滑
        transition_samples = int(sr * 0.2)  # 200ms过渡时间
        transition_samples = min(transition_samples, dialogue_len // 4)  # 不超过对话长度的1/4
        
        if transition_samples > 0:
            # 对话开始：从正常音量（1.0）平滑过渡到压低音量（ducking_ratio）
            transition_start_curve = torch.linspace(1.0, ducking_ratio, transition_samples, device=background.device).unsqueeze(0)
            ducking_curve[:, :transition_samples] = transition_start_curve
            
            # 对话结束：从压低音量（ducking_ratio）平滑过渡到正常音量（1.0）
            transition_end_curve = torch.linspace(ducking_ratio, 1.0, transition_samples, device=background.device).unsqueeze(0)
            ducking_curve[:, -transition_samples:] = transition_end_curve
        
        # 应用到对话部分的背景音量曲线
        background_volume_curve[:, dialogue_start:dialogue_end] = ducking_curve
    
    # Outro部分：背景音乐从正常音量淡出到0
    outro_fade_out_samples = min(outro_samples, int(sr * 1000 / 1000.0))  # 1秒淡出
    if outro_fade_out_samples > 0:
        outro_fade_out_curve = torch.linspace(1, 0, outro_fade_out_samples, device=background.device).unsqueeze(0)
        outro_start = total_len - outro_samples
        outro_fade_out_start = total_len - outro_fade_out_samples
        # Outro开始部分保持正常音量
        background_volume_curve[:, outro_start:outro_fade_out_start] = 1.0
        # Outro结束部分淡出
        background_volume_curve[:, outro_fade_out_start:] = outro_fade_out_curve
    
    # 应用背景音量曲线和基础音量
    background = background * background_volume_curve * background_volume
    
    # 混合音频（简单相加，然后归一化避免削波）
    mixed = foreground_padded + background
    
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

