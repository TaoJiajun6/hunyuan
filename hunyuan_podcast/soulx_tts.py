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
        verbose: bool = False
    ):
        """
        生成多角色播客音频
        
        Args:
            speakers: 说话人信息字典，格式为 {角色名: {"prompt_audio": 路径, "prompt_text": 文本}}
            dialogues: 对话列表，格式为 [(角色名, 文本), ...]
            output_path: 输出音频路径
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

