import os
import types
import atexit
from time import perf_counter
from functools import partial
from dataclasses import fields, asdict

import torch
import torch.multiprocessing as mp
from transformers import AutoTokenizer, AutoModelForCausalLM
from transformers import RepetitionPenaltyLogitsProcessor
try:    
    from vllm import LLM
    from vllm import SamplingParams as VllmSamplingParams
    from vllm.inputs import TokensPrompt as TokensPrompt
    SUPPORT_VLLM = True
except ImportError:
    SUPPORT_VLLM = False

from soulxpodcast.config import Config, SamplingParams
from soulxpodcast.models.modules.sampler import _ras_sample_hf_engine


def _get_supported_dtype():
    """
    根据GPU计算能力自动选择支持的dtype。
    bfloat16 需要计算能力 >= 8.0 (Ampere+)
    float16 支持计算能力 >= 7.0 (Volta+)
    """
    if not torch.cuda.is_available():
        # CPU 使用 float32
        return "float32"
    
    try:
        # 获取当前GPU的计算能力
        compute_capability = torch.cuda.get_device_capability(0)
        major, minor = compute_capability
        
        # 计算能力 >= 8.0 (Ampere+) 支持 bfloat16
        if major >= 8:
            return "bfloat16"
        # 计算能力 >= 7.0 (Volta+) 支持 float16
        elif major >= 7:
            return "float16"
        else:
            # 老GPU使用 float32
            return "float32"
    except Exception:
        # 如果检测失败，默认使用 float16（更安全）
        return "float16"

class HFLLMEngine:

    def __init__(self, model, **kwargs):
        config_fields = {field.name for field in fields(Config)}
        config_kwargs = {k: v for k, v in kwargs.items() if k in config_fields}
        config = Config(model, **config_kwargs)
        
        self.tokenizer = AutoTokenizer.from_pretrained(model, use_fast=True)
        config.eos = config.hf_config.eos_token_id # speech eos token;
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        
        # 根据GPU计算能力自动选择dtype
        dtype_str = _get_supported_dtype()
        if dtype_str == "bfloat16":
            torch_dtype = torch.bfloat16
        elif dtype_str == "float16":
            torch_dtype = torch.float16
        else:
            torch_dtype = torch.float32
        
        # 输出GPU信息和选择的dtype
        if torch.cuda.is_available():
            compute_cap = torch.cuda.get_device_capability(0)
            gpu_name = torch.cuda.get_device_name(0)
            print(f"[INFO] GPU: {gpu_name}, 计算能力: {compute_cap[0]}.{compute_cap[1]}, 自动选择 dtype: {dtype_str}")
        
        self.model = AutoModelForCausalLM.from_pretrained(model, torch_dtype=torch_dtype, device_map=self.device)
        self.config = config
        self.pad_token_id = self.tokenizer.pad_token_id

    def generate(
        self,
        prompt: list[str],
        sampling_param: SamplingParams,
        past_key_values=None,
    ) -> dict:
        
        # 使用 eos_token_id 参数而不是自定义 stopping_criteria，避免重复警告
        # transformers 库会自动创建 EosTokenCriteria
        if sampling_param.use_ras:
            sample_hf_engine_handler = partial(_ras_sample_hf_engine, 
                    use_ras=sampling_param.use_ras, 
                    win_size=sampling_param.win_size, tau_r=sampling_param.tau_r)
        else:
            sample_hf_engine_handler = None
        rep_pen_processor = RepetitionPenaltyLogitsProcessor(
            penalty=sampling_param.repetition_penalty,
            prompt_ignore_length=len(prompt)
        ) # exclude the input prompt, consistent with vLLM implementation;
        with torch.no_grad(): 
            input_len = len(prompt)
            generated_ids = self.model.generate(
                input_ids = torch.tensor([prompt], dtype=torch.int64).to(self.device),
                do_sample=True,
                top_k=sampling_param.top_k,
                top_p=sampling_param.top_p,
                min_new_tokens=sampling_param.min_tokens,
                max_new_tokens=sampling_param.max_tokens,
                temperature=sampling_param.temperature,
                eos_token_id=self.config.hf_config.eos_token_id,  # 使用 eos_token_id 参数，让 transformers 自动处理
                past_key_values=past_key_values,
                custom_generate=sample_hf_engine_handler,
                use_cache=True,
                logits_processor=[rep_pen_processor]
            )
            generated_ids = generated_ids[:, input_len:].cpu().numpy().tolist()[0]
        output = {
            "text": self.tokenizer.decode(generated_ids),
            "token_ids": generated_ids,
        }
        return output

class VLLMEngine:

    def __init__(self, model, **kwargs):
        
        config_fields = {field.name for field in fields(Config)}
        config_kwargs = {k: v for k, v in kwargs.items() if k in config_fields}
        config = Config(model, **config_kwargs)
        
        self.tokenizer = AutoTokenizer.from_pretrained(config.model, use_fast=True)
        config.eos = config.hf_config.eos_token_id # speech eos token;
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        os.environ["VLLM_USE_V1"] = "0"
        if SUPPORT_VLLM:
            # 根据GPU计算能力自动选择dtype
            dtype_str = _get_supported_dtype()
            # vllm 使用的 dtype 字符串格式
            if dtype_str == "float16":
                vllm_dtype = "half"  # vllm 使用 "half" 表示 float16
            elif dtype_str == "bfloat16":
                vllm_dtype = "bfloat16"
            else:
                vllm_dtype = "float"  # float32
            
            # 输出GPU信息和选择的dtype
            if torch.cuda.is_available():
                compute_cap = torch.cuda.get_device_capability(0)
                gpu_name = torch.cuda.get_device_name(0)
                print(f"[INFO] VLLM Engine - GPU: {gpu_name}, 计算能力: {compute_cap[0]}.{compute_cap[1]}, 自动选择 dtype: {vllm_dtype}")
            
            # V100 (compute capability 7.0) 在使用 float16 时有 Triton 编译问题
            # 错误发生在 prefix_prefill.py 的 attention kernel 编译时
            # 错误信息: "LLVM ERROR: Unsupported rounding mode for conversion"
            # 
            # 解决方案（按推荐顺序）：
            # 1. 使用 float32（自动处理，较慢但兼容）
            # 2. 禁用 prefix caching + float16（可能不够，但可尝试）
            # 3. 使用 HF 引擎（最推荐用于 V100）
            compute_cap = torch.cuda.get_device_capability(0) if torch.cuda.is_available() else (0, 0)
            use_prefix_caching = True
            
            # 检查是否有环境变量强制使用 float32（用于 V100 兼容性）
            # 默认对于 V100，建议使用 float32 以避免 Triton 编译错误
            v100_auto_float32 = os.environ.get("VLLM_V100_AUTO_FLOAT32", "true").lower() == "true"
            force_float32 = os.environ.get("VLLM_V100_FORCE_FLOAT32", "false").lower() == "true"
            
            if compute_cap[0] == 7 and vllm_dtype == "half":
                if force_float32 or v100_auto_float32:
                    # V100 + float16 有 Triton 编译问题，自动使用 float32
                    vllm_dtype = "float"
                    if v100_auto_float32:
                        print(f"[WARNING] V100 GPU: 检测到 float16 + Triton 兼容性问题，自动切换到 float32")
                        print(f"[INFO] float32 比 float16 慢约 2 倍，但兼容 V100")
                        print(f"[INFO] 如果想强制使用 float16，设置: export VLLM_V100_AUTO_FLOAT32=false")
                    else:
                        print(f"[WARNING] V100 GPU: 检测到环境变量 VLLM_V100_FORCE_FLOAT32=true，使用 float32")
                else:
                    # 尝试禁用 prefix caching，但可能仍然失败
                    use_prefix_caching = False
                    print(f"[WARNING] V100 GPU 使用 float16: 禁用 prefix caching 以避免 Triton 编译错误")
                    print(f"[WARNING] 注意: 可能仍然会遇到 Triton 编译错误")
                    print(f"[INFO] 如果出错，建议：")
                    print(f"[INFO]   1. 设置环境变量: export VLLM_V100_AUTO_FLOAT32=true (使用 float32)")
                    print(f"[INFO]   2. 或切换到 HF 引擎: llm_engine='hf' (推荐)")
            
            # 设置 Triton 相关环境变量以减少编译问题
            if compute_cap[0] == 7:
                # V100 可能需要禁用某些 Triton 优化
                os.environ.setdefault("TRITON_CACHE_DIR", "/tmp/triton_cache")
                # 禁用 Triton 的一些可能导致问题的优化
                os.environ.setdefault("TRITON_INTERPRET", "0")
            
            # 初始化 VLLM 模型
            self.model = LLM(
                model=model, 
                enforce_eager=True, 
                dtype=vllm_dtype, 
                max_model_len=8192, 
                enable_prefix_caching=use_prefix_caching,
                disable_custom_all_reduce=False,  # 保持默认
            )
        else:
            raise ImportError("Not Support VLLM now!!!")
        self.config = config
        self.pad_token_id = self.tokenizer.pad_token_id

    def generate(
        self,
        prompt: list[str],
        sampling_param: SamplingParams,
        past_key_values=None,
    ) -> dict:
        sampling_param.stop_token_ids = [self.config.hf_config.eos_token_id]
        with torch.no_grad():
            generated_ids = self.model.generate(
                TokensPrompt(prompt_token_ids=prompt), 
                VllmSamplingParams(**asdict(sampling_param)),
                use_tqdm=False,
            )[0].outputs[0].token_ids
        output = {
            "text": self.tokenizer.decode(generated_ids),
            "token_ids": list(generated_ids),
        }
        return output