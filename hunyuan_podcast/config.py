"""
配置文件模块
"""
import os
from typing import Optional
from pathlib import Path

# 加载 .env 文件（如果存在）
def _load_dotenv_if_exists():
    """
    读取项目根目录下的 .env（可选），用于持久化环境变量。
    支持的格式：KEY=VALUE 或 KEY="VALUE"
    """
    try:
        # 获取项目根目录（相对于当前文件）
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_file_dir)
        env_path = Path(project_root) / ".env"
        
        if not env_path.exists():
            return
        
        print(f"检测到 .env 文件，正在加载环境变量: {env_path}")
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and v and k not in os.environ:
                os.environ[k] = v
                print(f"   ✓ 加载: {k}={v}")
    except Exception as e:
        print(f"⚠️  加载 .env 失败: {e}")

# 在导入配置之前加载 .env 文件
_load_dotenv_if_exists()

# 腾讯云混元API配置（直接调用，速度更快）
# 请在此处直接配置您的API密钥（从 https://console.cloud.tencent.com/hunyuan/start 获取）
HUNYUAN_API_KEY = os.getenv("HUNYUAN_API_KEY", "sk-9sdLTaRofvCIXznmikNf5WBlO8Tnmn7vkXwXtOJg3X5b5I4A")  # 腾讯云混元 API Key
HUNYUAN_API_BASE = "https://api.hunyuan.cloud.tencent.com/v1"
# 使用 hunyuan-a13b（混元第一个混合推理模型，80B总参数，13B激活，兼顾效果及推理性能）
HUNYUAN_MODEL = os.getenv("HUNYUAN_MODEL", "hunyuan-a13b")  # 默认使用 hunyuan-a13b
# 快思考模式开关（hunyuan-a13b 默认是慢思考模式，开启快思考模式可提升速度）
HUNYUAN_FAST_THINKING = os.getenv("HUNYUAN_FAST_THINKING", "True").lower() == "true"  # 默认开启快思考模式


# SoulX-Podcast配置
# 获取项目根目录（相对于当前文件）
_current_file_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_current_file_dir)
_default_model_dir = os.path.join(_project_root, "SoulX-Podcast", "pretrained_models", "SoulX-Podcast-1.7B")

SOULX_PODCAST_MODEL_DIR = os.getenv("SOULX_PODCAST_MODEL_DIR", _default_model_dir)
SOULX_PODCAST_LLM_ENGINE = os.getenv("SOULX_PODCAST_LLM_ENGINE", "hf")  # "hf" 或 "vllm"
SOULX_PODCAST_FP16_FLOW = os.getenv("SOULX_PODCAST_FP16_FLOW", "True").lower() == "true"

# 默认参数
DEFAULT_TEMPERATURE = 0.7  # 降低温度以加快生成速度
DEFAULT_MAX_TOKENS = 2000  # 降低最大token数以加快生成速度
DEFAULT_TOP_P = 0.9

# 音频合成配置
AUDIO_SILENCE_INTERVAL = 500  # 角色切换时的静音间隔（毫秒），默认500ms以保持对话流畅自然
AUDIO_SAMPLING_RATE = 22050

# 输出目录（使用绝对路径，确保无论从哪里运行都能正确保存）
_current_file_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_current_file_dir)
OUTPUT_DIR = os.path.join(_project_root, "outputs", "podcasts")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 音乐文件夹路径（保留原有路径，如果不存在则使用备用路径）
_music_dir_index_tts = os.path.join(_project_root, "index-tts", "music")
_music_dir_default = os.path.join(_project_root, "music")
MUSIC_DIR = _music_dir_index_tts if os.path.exists(_music_dir_index_tts) else _music_dir_default

# 云存储音乐配置
# 云存储音乐文件夹路径（相对于bucket的路径）
CLOUD_STORAGE_MUSIC_PATH = os.getenv('CLOUD_STORAGE_MUSIC_PATH', 'music/')

