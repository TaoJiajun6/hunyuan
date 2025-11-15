"""
SoulX-Podcast TTS 包装类
提供与 IndexTTS 类似的接口，方便替换
"""
import os
import sys
import re
import torch
import soundfile as sf
from typing import Optional, List, Dict
from pathlib import Path

# 添加 SoulX-Podcast 路径到 sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
soulx_path = os.path.join(project_root, "SoulX-Podcast")
if soulx_path not in sys.path:
    sys.path.insert(0, soulx_path)

try:
    from soulxpodcast.models.soulxpodcast import SoulXPodcast
    from soulxpodcast.utils.infer_utils import initiate_model, process_single_input
    from soulxpodcast.utils.parser import podcast_format_parser
    from soulxpodcast.config import Config, SoulXPodcastLLMConfig, SamplingParams
    HAS_SOULX = True
except ImportError as e:
    HAS_SOULX = False
    IMPORT_ERROR = str(e)
    print(f"⚠️  警告：无法导入 SoulX-Podcast: {e}")
    print("💡 请确保已安装 SoulX-Podcast 依赖：")
    print("   cd SoulX-Podcast")
    print("   pip install -r requirements.txt")


class SoulXTTS:
    """SoulX-Podcast TTS 包装类，提供类似 IndexTTS 的接口"""
    
    def __init__(
        self,
        model_path: str,
        llm_engine: str = "hf",
        fp16_flow: bool = False,
        seed: int = 1988,
        device: Optional[str] = None
    ):
        """
        初始化 SoulX-Podcast TTS
        
        Args:
            model_path: 模型路径
            llm_engine: LLM 引擎类型 ("hf" 或 "vllm")
            fp16_flow: 是否使用 FP16 精度
            seed: 随机种子
            device: 设备类型（SoulX-Podcast 自动使用 CUDA，此参数保留以兼容接口）
        """
        if not HAS_SOULX:
            raise ImportError(f"无法导入 SoulX-Podcast: {IMPORT_ERROR}\n请按照提示安装依赖。")
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型路径不存在: {model_path}")
        
        self.model_path = model_path
        self.llm_engine = llm_engine
        self.fp16_flow = fp16_flow
        self.seed = seed
        self.device = device  # SoulX-Podcast 自动使用 CUDA
        
        # 延迟加载模型
        self.model = None
        self.dataset = None
        
        # 缓存：角色名到索引的映射
        self.role_to_index: Dict[str, int] = {}
        self.prompt_cache: Dict[str, Dict] = {}  # 缓存每个角色的 prompt 信息
    
    def _ensure_model_loaded(self):
        """确保模型已加载"""
        if self.model is None or self.dataset is None:
            print(f"正在加载 SoulX-Podcast 模型...")
            print(f"模型路径: {self.model_path}")
            self.model, self.dataset = initiate_model(
                seed=self.seed,
                model_path=self.model_path,
                llm_engine=self.llm_engine,
                fp16_flow=self.fp16_flow
            )
            print(f"✅ SoulX-Podcast 模型加载完成！")
    
    def infer(
        self,
        spk_audio_prompt: str,
        text: str,
        output_path: str,
        prompt_text: Optional[str] = None,
        verbose: bool = False,
        **kwargs
    ):
        """
        生成音频（单角色）
        
        Args:
            spk_audio_prompt: 说话人参考音频路径
            text: 要合成的文本
            output_path: 输出音频路径
            prompt_text: 提示文本（可选，用于描述说话人特征）
            verbose: 是否输出详细信息
            **kwargs: 其他参数（兼容性保留）
        
        Returns:
            输出音频路径
        """
        # 确保模型已加载
        self._ensure_model_loaded()
        
        # 如果没有提供 prompt_text，使用默认值
        if prompt_text is None or prompt_text.strip() == "":
            prompt_text = "这是一个参考音频。"
        
        # 构建单角色播客格式
        # SoulX-Podcast 需要多角色格式，我们创建一个单角色的
        podcast_data = {
            "speakers": {
                "S1": {
                    "prompt_audio": spk_audio_prompt,
                    "prompt_text": prompt_text
                }
            },
            "text": [
                ["S1", text]
            ]
        }
        
        # 解析格式
        inputs = podcast_format_parser(podcast_data)
        
        # 处理输入
        data = process_single_input(
            self.dataset,
            inputs['text'],
            inputs['prompt_wav'],
            inputs['prompt_text'],
            inputs.get('use_dialect_prompt', False),
            inputs.get('dialect_prompt_text', [])
        )
        
        if verbose:
            print(f"[INFO] 开始生成音频...")
        
        # 生成音频
        results_dict = self.model.forward_longform(**data)
        
        # 保存音频
        target_audio = None
        for wav in results_dict["generated_wavs"]:
            if target_audio is None:
                target_audio = wav
            else:
                target_audio = torch.cat([target_audio, wav], dim=1)
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        # SoulX-Podcast 输出采样率为 24000
        sf.write(output_path, target_audio.cpu().squeeze(0).numpy(), 24000)
        
        if verbose:
            print(f"[INFO] 音频已保存到: {output_path}")
        
        return output_path
    
    def infer_multi_speaker(
        self,
        speakers: Dict[str, Dict[str, str]],
        dialogues: List[tuple],
        output_path: str,
        silence_interval: Optional[int] = None,
        verbose: bool = False
    ):
        """
        生成多角色播客音频
        
        Args:
            speakers: 说话人信息字典，格式为 {角色名: {"prompt_audio": 路径, "prompt_text": 文本}}
            dialogues: 对话列表，格式为 [(角色名, 文本), ...]
            output_path: 输出音频路径
            silence_interval: 角色切换静音间隔（毫秒），如果为None则使用默认值400ms
            verbose: 是否输出详细信息
        
        Returns:
            输出音频路径
        """
        # 确保模型已加载
        self._ensure_model_loaded()
        
        # 构建播客格式数据
        # 将角色名映射为 S1, S2, S3...
        role_mapping = {}
        podcast_speakers = {}
        for idx, (role_name, role_info) in enumerate(speakers.items(), 1):
            spk_id = f"S{idx}"
            role_mapping[role_name] = spk_id
            podcast_speakers[spk_id] = {
                "prompt_audio": role_info["prompt_audio"],
                "prompt_text": role_info.get("prompt_text", "这是一个参考音频。")
            }
        
        # 转换对话格式
        podcast_text = []
        for role_name, text in dialogues:
            spk_id = role_mapping.get(role_name, "S1")
            podcast_text.append([spk_id, text])
        
        podcast_data = {
            "speakers": podcast_speakers,
            "text": podcast_text
        }
        
        # 解析格式
        inputs = podcast_format_parser(podcast_data)
        
        # 处理输入
        data = process_single_input(
            self.dataset,
            inputs['text'],
            inputs['prompt_wav'],
            inputs['prompt_text'],
            inputs.get('use_dialect_prompt', False),
            inputs.get('dialect_prompt_text', [])
        )
        
        if verbose:
            print(f"[INFO] 开始生成多角色播客音频...")
            print(f"      说话人数量: {len(speakers)}")
            print(f"      对话轮数: {len(dialogues)}")
            # 估算生成时间（根据经验值：每段对话约2-5秒推理时间）
            estimated_time = len(dialogues) * 3  # 平均每段3秒
            print(f"      预计生成时间: 约 {estimated_time} 秒（{estimated_time/60:.1f} 分钟）")
            print(f"      提示：SoulX-Podcast需要逐段生成音频，这是正常现象")
        
        # 生成音频（这是最耗时的步骤）
        # 原因分析：
        # 1. 每段对话都需要经过LLM生成 -> Flow生成 -> HiFi-GAN生成三个步骤
        # 2. 对于4-5分钟的播客（30-60段对话），总耗时 = 段数 × 每段耗时（2-5秒）
        # 3. 如果使用较慢的GPU或CPU，每段可能需要更长时间
        import time
        generation_start = time.time()
        results_dict = self.model.forward_longform(**data)
        generation_time = time.time() - generation_start
        if verbose:
            print(f"[INFO] 音频生成完成，耗时: {generation_time:.2f} 秒（{generation_time/60:.2f} 分钟）")
            print(f"      平均每段对话耗时: {generation_time/len(dialogues):.2f} 秒")
        
        # 处理音频片段，添加静音间隔以改善角色衔接
        # 只在对话最开始和结束时应用淡入淡出效果，中间片段保持真实切换
        generated_wavs = results_dict["generated_wavs"]
        if not generated_wavs:
            raise ValueError("未生成任何音频片段")
        
        # SoulX-Podcast 输出采样率为 24000
        sr = 24000
        # 使用传入的静音间隔，如果没有则使用默认值400ms（比配置的800ms稍短以保持流畅）
        silence_interval_ms = silence_interval if silence_interval is not None else 400
        fade_duration_ms = 200  # 淡入淡出时长（毫秒），用于对话开始和结束
        
        processed_segments = []
        
        for i, wav in enumerate(generated_wavs):
            # 确保音频格式正确 (1, samples)
            if wav.dim() == 1:
                wav = wav.unsqueeze(0)
            elif wav.dim() > 1 and wav.shape[0] > 1:
                wav = torch.mean(wav, dim=0, keepdim=True)
            
            # 克隆张量以避免在推理模式下的原地操作错误
            # 推理模式下不能对张量进行原地操作，需要先克隆
            wav = wav.clone()
            
            # 获取音频的设备，确保所有操作在同一设备上
            device = wav.device
            
            # 只在第一个片段（对话开始）应用淡入效果
            # 只在最后一个片段（对话结束）应用淡出效果
            # 中间片段不添加淡入淡出，保持真实对话切换
            fade_samples = int(sr * fade_duration_ms / 1000.0)
            
            if fade_samples > 0 and wav.shape[1] > fade_samples * 2:
                # 第一个片段：应用淡入效果（对话开始）
                if i == 0:
                    fade_in_curve = torch.linspace(0, 1, fade_samples, device=device).unsqueeze(0)
                    wav[:, :fade_samples] = wav[:, :fade_samples] * fade_in_curve
                
                # 最后一个片段：应用淡出效果（对话结束）
                if i == len(generated_wavs) - 1:
                    fade_out_curve = torch.linspace(1, 0, fade_samples, device=device).unsqueeze(0)
                    fade_out_start = wav.shape[1] - fade_samples
                    wav[:, fade_out_start:] = wav[:, fade_out_start:] * fade_out_curve
            
            processed_segments.append(wav)
            
            # 在片段之间添加静音间隔（除了最后一个），确保在正确的设备上
            if i < len(generated_wavs) - 1:
                silence_samples = int(sr * silence_interval_ms / 1000.0)
                silence = torch.zeros(1, silence_samples, device=device)
                processed_segments.append(silence)
        
        # 拼接所有处理后的音频片段
        if len(processed_segments) == 1:
            target_audio = processed_segments[0]
        else:
            target_audio = torch.cat(processed_segments, dim=1)
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        # SoulX-Podcast 输出采样率为 24000
        sf.write(output_path, target_audio.cpu().squeeze(0).numpy(), sr)
        
        if verbose:
            print(f"[INFO] 音频已保存到: {output_path}")
        
        return output_path

