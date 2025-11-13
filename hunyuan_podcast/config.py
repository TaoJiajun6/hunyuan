"""
配置文件模块
"""
import os
from typing import Optional

# 硅基流动API配置
# 请在此处直接配置您的API密钥（从 https://cloud.siliconflow.cn 获取）
SILICONFLOW_API_KEY = "sk-tpoapasxdwjyexqfagbiigtvwsoydwravbptrmrrmwjfdwbh"  # 请替换为您的实际API密钥
SILICONFLOW_API_BASE = "https://api.siliconflow.cn/v1"
SILICONFLOW_MODEL = "tencent/Hunyuan-A13B-Instruct"

# IndexTTS-2配置
# 获取项目根目录（相对于当前文件）
_current_file_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_current_file_dir)
_default_config_path = os.path.join(_project_root, "index-tts", "checkpoints", "config.yaml")
_default_model_dir = os.path.join(_project_root, "index-tts", "checkpoints")

INDEXTTS_CONFIG_PATH = os.getenv("INDEXTTS_CONFIG_PATH", _default_config_path)
INDEXTTS_MODEL_DIR = os.getenv("INDEXTTS_MODEL_DIR", _default_model_dir)

# 默认参数
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 2000
DEFAULT_TOP_P = 0.9

# 音频合成配置
AUDIO_SILENCE_INTERVAL = 300  # 角色切换时的静音间隔（毫秒）
AUDIO_SAMPLING_RATE = 22050

# 输出目录（使用绝对路径，确保无论从哪里运行都能正确保存）
_current_file_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_current_file_dir)
OUTPUT_DIR = os.path.join(_project_root, "outputs", "podcasts")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 音乐文件夹路径
MUSIC_DIR = os.path.join(_project_root, "index-tts", "music")

