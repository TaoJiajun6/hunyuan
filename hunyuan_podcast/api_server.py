"""
混元AI播客生成系统 - REST API服务
提供REST API接口供工作流系统调用
"""
import os
import sys
import base64
import tempfile
import logging
import time
import requests
import json
from typing import Optional, List, Dict, Any, Union
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
import asyncio
from pydantic import BaseModel, Field, ValidationError
import uvicorn
import glob
import base64 as _base64
from typing import Tuple
import concurrent.futures

# 尝试导入我们在 tools 中实现的 AGC 上传工具（可选）
try:
    from tools.upload_agc import get_agc_token as agc_get_token, upload_file_to_agc as agc_upload_file
except Exception:
    agc_get_token = None
    agc_upload_file = None

# 尝试导入库级上传客户端（优先使用包内实现）
try:
    from .upload_client import upload_generated_podcast as agc_upload_client
except Exception:
    agc_upload_client = None

from .podcast_generator import PodcastGenerator
from .config import SOULX_PODCAST_MODEL_DIR, SOULX_PODCAST_LLM_ENGINE, SOULX_PODCAST_FP16_FLOW, OUTPUT_DIR
from .text_processor import TextProcessor
from .api_client import get_client
from .input_processor import InputProcessor, get_processor
from .music_selector import MusicSelector


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 强制使用 HF 引擎（移除 vllm 支持）
_LLM_ENGINE = "hf" if SOULX_PODCAST_LLM_ENGINE == "vllm" else SOULX_PODCAST_LLM_ENGINE
if _LLM_ENGINE != SOULX_PODCAST_LLM_ENGINE:
    logger.info(f"VLLM support removed, using HF engine instead of {SOULX_PODCAST_LLM_ENGINE}")

# ============ 进度管理 ============
_PROGRESS_DIR = os.path.join(os.getcwd(), 'outputs', 'progress')
os.makedirs(_PROGRESS_DIR, exist_ok=True)
_PROGRESS_CACHE: Dict[str, Dict[str, Any]] = {}
# SSE连接管理：存储每个job_id的SSE连接队列
_PROGRESS_SSE_QUEUES: Dict[str, asyncio.Queue] = {}

def _progress_path(job_id: str) -> str:
    return os.path.join(_PROGRESS_DIR, f"{job_id}.json")

def _update_progress(job_id: Optional[str], phase: str, percent: int, message: str, done: bool = False, error: Optional[str] = None, audio_url: Optional[str] = None):
    """更新任务进度
    
    Args:
        job_id: 任务ID
        phase: 阶段
        percent: 百分比 (0-100)
        message: 消息
        done: 是否完成
        error: 错误信息（可选）
        audio_url: 音频云存储URL（可选，生成完成后提供）
    """
    if not job_id:
        return
    data = {
        "job_id": job_id,
        "phase": phase,
        "percent": max(0, min(100, percent)),
        "message": message,
        "done": done,
        "error": error,
        "ts": int(time.time())
    }
    # 如果提供了 audio_url，添加到进度数据中（用于前端从云存储下载）
    if audio_url:
        data["audio_url"] = audio_url
    _PROGRESS_CACHE[job_id] = data
    try:
        with open(_progress_path(job_id), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass
    
    # 如果有SSE连接，推送进度更新
    if job_id in _PROGRESS_SSE_QUEUES:
        queue = _PROGRESS_SSE_QUEUES[job_id]
        try:
            # 非阻塞方式放入队列
            queue.put_nowait(data)
        except asyncio.QueueFull:
            # 队列满了，忽略（不应该发生，因为只有一个连接）
            pass

def _get_progress(job_id: str) -> Dict[str, Any]:
    if job_id in _PROGRESS_CACHE:
        return _PROGRESS_CACHE[job_id]
    try:
        with open(_progress_path(job_id), 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"job_id": job_id, "phase": "unknown", "percent": 0, "message": "未开始或任务ID不存在", "done": False}

# 文件大小限制（字节）
MAX_AUDIO_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_REQUEST_BODY_SIZE = 100 * 1024 * 1024  # 100MB

app = FastAPI(
    title="混元AI播客生成API",
    description="基于混元大模型和SoulX-Podcast的智能播客音频生成API",
    version="1.0.0"
)

# 配置CORS，允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局生成器实例
generator: Optional[PodcastGenerator] = None
# GPU配置（从环境变量或启动参数获取）
device = os.getenv("DEVICE", None)


def get_generator() -> PodcastGenerator:
    """获取或创建生成器实例"""
    global generator
    if generator is None:
        logger.info("初始化PodcastGenerator...")
        logger.info(f"模型配置: model_dir={SOULX_PODCAST_MODEL_DIR}, llm_engine={_LLM_ENGINE}, fp16_flow={SOULX_PODCAST_FP16_FLOW}, device={device}")
        generator = PodcastGenerator(
            tts_model_dir=SOULX_PODCAST_MODEL_DIR,
            llm_engine=_LLM_ENGINE,
            fp16_flow=SOULX_PODCAST_FP16_FLOW,
            device=device
        )
        logger.info("PodcastGenerator初始化完成")
    return generator


# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求日志"""
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    method = request.method
    path = request.url.path
    
    # 过滤进度查询请求（GET /api/v1/podcast/progress/xxx），避免日志被轮询覆盖
    # 注意：HarmonyOS客户端使用HTTP轮询获取进度，因此需要过滤这些请求以避免日志被覆盖
    # 保留SSE连接请求的日志（/stream端点），虽然HarmonyOS不支持，但Web客户端可能使用
    is_progress_poll = (
        method == "GET" and 
        path.startswith("/api/v1/podcast/progress/") and 
        not path.endswith("/stream")
    )
    
    if not is_progress_poll:
        # 记录请求信息（非进度查询请求）
        content_length = request.headers.get("content-length")
        if content_length:
            content_length_mb = int(content_length) / (1024 * 1024)
            logger.info(f"收到请求: {method} {path} from {client_ip}, Content-Length: {content_length_mb:.2f} MB")
            
            # 检查Content-Length
            if int(content_length) > MAX_REQUEST_BODY_SIZE:
                logger.warning(f"请求体过大: {content_length_mb:.2f} MB (限制: {MAX_REQUEST_BODY_SIZE / 1024 / 1024:.2f} MB)")
                return JSONResponse(
                    status_code=413,
                    content={
                        "success": False,
                        "message": "请求体过大",
                        "error": f"请求体大小 {content_length_mb:.2f} MB 超过限制 {MAX_REQUEST_BODY_SIZE / 1024 / 1024:.2f} MB"
                    }
                )
        else:
            logger.info(f"收到请求: {method} {path} from {client_ip}")
    
    # 对于POST请求，尝试记录请求体（仅用于调试）
    if method == "POST" and path.startswith("/api/v1/podcast"):
        try:
            # 读取请求体（注意：读取后需要重新创建请求流）
            body_bytes = await request.body()
            if body_bytes:
                try:
                    body_json = json.loads(body_bytes.decode('utf-8'))
                    # 记录关键字段，但不记录完整的base64数据
                    log_body: Dict[str, Any] = {}
                    for key, value in body_json.items():
                        if key in ['role_voices', 'role_voice_urls'] and isinstance(value, dict):
                            log_body[key] = f"{{角色数量: {len(value)}, 角色: {list(value.keys())}}}"
                        elif key == 'text':
                            log_body[key] = f"长度: {len(str(value))} 字符"
                        else:
                            log_body[key] = value
                    logger.info(f"请求体内容: {json.dumps(log_body, ensure_ascii=False)}")
                    
                    # 检查必需字段
                    if path == "/api/v1/podcast/multi_role":
                        has_text = body_json.get("text") and str(body_json.get("text")).strip() and str(body_json.get("text")).strip() != "长度: 0 字符"
                        # 支持单个URL字符串或URL数组
                        text_file_url_value = body_json.get("text_file_url")
                        if isinstance(text_file_url_value, list):
                            has_text_file = len(text_file_url_value) > 0 and any(url and str(url).strip() for url in text_file_url_value)
                        else:
                            has_text_file = text_file_url_value and str(text_file_url_value).strip()
                        has_input_url = body_json.get("input_url") and str(body_json.get("input_url")).strip()
                        has_voice_urls = body_json.get("role_voice_urls") and len(body_json.get("role_voice_urls", {})) > 0
                        has_voices = body_json.get("role_voices") and len(body_json.get("role_voices", {})) > 0
                        input_type = body_json.get("input_type", "").strip()
                        
                        # 根据输入类型验证必需的输入
                        url_types = ["公众号", "公众号+指令", "网页", "网页+指令"]
                        text_types = ["文字", "文字+指令", "文字+英文指令"]
                        file_types = ["文件", "文件+指令"]
                        
                        # 对于URL类型（公众号、网页），不需要text或text_file_url
                        if input_type in url_types:
                            if not has_input_url and not has_text_file:
                                logger.error(f"{input_type}类型需要提供input_url或text_file_url")
                        # 对于文字类型，需要text
                        elif input_type in text_types:
                            if not has_text:
                                logger.error(f"{input_type}类型需要提供text字段")
                        # 对于文件类型，需要text_file_url
                        elif input_type in file_types:
                            if not has_text_file:
                                logger.error(f"{input_type}类型需要提供text_file_url字段")
                        # 对于未知类型，至少需要text、text_file_url或input_url之一
                        else:
                            if not has_text and not has_text_file and not has_input_url:
                                logger.error("缺少必需字段: text、text_file_url或input_url至少需要一个")
                        
                        if not has_voice_urls and not has_voices:
                            logger.error("缺少必需字段: role_voice_urls 或 role_voices 至少需要一个")
                except ValueError as e:  # json.JSONDecodeError是ValueError的子类
                    logger.error(f"请求体JSON解析失败: {str(e)}")
                except Exception as e:
                    logger.warning(f"处理请求体失败: {str(e)}")
            
            # 重新创建请求流（因为已经读取过了）
            async def receive():
                return {"type": "http.request", "body": body_bytes}
            request._receive = receive
        except Exception as e:
            logger.warning(f"无法读取请求体: {str(e)}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    
    # 记录响应信息（非进度查询请求）
    if not is_progress_poll:
        status_code = response.status_code
        logger.info(f"请求完成: {method} {path} - 状态码: {status_code} - 耗时: {process_time:.2f}s")
    
    return response


# ============ 请求模型 ============

class MultiRoleRequest(BaseModel):
    """多角色互动播客请求"""
    text: Optional[str] = Field(None, description="播客文本（支持角色标记或普通文本，如果使用text_file_url或input_url，此字段可为空）")
    text_file_url: Optional[Union[str, List[str]]] = Field(None, description="文本文件云存储URL（.txt或Word文件，如果提供，优先使用）。支持单个URL字符串或URL数组（多个文件）")
    input_type: Optional[str] = Field(None, description="输入类型，可选值：文字、文字+指令、公众号、公众号+指令、网页、网页+指令、文件、文件+指令、文字+英文指令")
    input_url: Optional[str] = Field(None, description="输入URL（用于公众号、网页、PDF等类型）")
    instruction: Optional[str] = Field(None, description="指令内容（可选，用于控制播客生成过程，如'生成5分钟播客'、'使用轻松风格'等）")
    role_voice_urls: Optional[Dict[str, str]] = Field(None, description="角色音色映射，云存储URL（如果使用云存储，键为角色名，值为云存储下载URL）")
    role_voices: Optional[Dict[str, str]] = Field(None, description="[已废弃] 角色音色映射，base64编码的音频文件（已废弃，请使用role_voice_urls）")
    silence_interval: int = Field(800, description="角色切换静音间隔（毫秒），默认800ms以增加角色之间的间隔，让对话更清晰", ge=200, le=1500)
    podcast_name: Optional[str] = Field(None, description="播客名称（可选）")
    topic: Optional[str] = Field(None, description="本期主题（可选）")
    character_1_name: Optional[str] = Field(None, description="角色1名称（可选）")
    character_1_personality: Optional[str] = Field(None, description="角色1性格特点（可选）")
    character_1_speaking_style: Optional[str] = Field(None, description="角色1说话风格（可选）")
    character_2_name: Optional[str] = Field(None, description="角色2名称（可选）")
    character_2_personality: Optional[str] = Field(None, description="角色2性格特点（可选）")
    character_2_speaking_style: Optional[str] = Field(None, description="角色2说话风格（可选）")
    character_3_name: Optional[str] = Field(None, description="角色3名称（可选）")
    character_3_personality: Optional[str] = Field(None, description="角色3性格特点（可选）")
    character_3_speaking_style: Optional[str] = Field(None, description="角色3说话风格（可选）")
    scene_types: Optional[List[str]] = Field(None, description="互动场景类型列表（可选）")
    category: Optional[str] = Field(None, description="播客分类（可选），如：商业、科技、财经、新闻、影视、音乐、文化艺术、历史、哲学思考、自我成长、职场、学习、教育育儿、情感恋爱、健康养生、旅游、美食、生活方式、娱乐、游戏电竞、体育、时尚美妆、汽车、法律、宠物等")
    intro_music: Optional[str] = Field(None, description="[已废弃] 开场音乐，base64编码的音频文件（已废弃）")
    outro_music: Optional[str] = Field(None, description="[已废弃] 结尾音乐，base64编码的音频文件（已废弃）")
    background_music: Optional[str] = Field(None, description="[已废弃] 背景音乐，base64编码的音频文件（已废弃）")
    background_volume: float = Field(0.3, description="背景音乐音量（0.0-1.0）", ge=0.0, le=1.0)
    # 如果为 True，则在生成完成后等待上传到 AGC 完成（同步），超时由 upload_timeout 控制（秒）。
    wait_for_upload: bool = Field(True, description="是否等待上传到云存储完成（可选，默认false）")
    upload_timeout: int = Field(120, description="等待上传完成的超时时间（秒），如果为0则根据文件大小自动计算", ge=0, le=600)
    job_id: Optional[str] = Field(None, description="可选任务ID，用于前端轮询进度")


class CharacterInfo(BaseModel):
    """角色信息"""
    name: str = Field(..., description="角色名称")
    identity: Optional[str] = Field(None, description="身份/职业")
    personality: Optional[str] = Field(None, description="核心性格")
    catchphrase: Optional[str] = Field(None, description="口头禅/说话习惯")
    speaking_style: Optional[str] = Field(None, description="说话风格")
    relationship: Optional[str] = Field(None, description="与其他角色的关系")
    voice_url: str = Field(..., description="音色文件云存储URL（必需）")
    voice: Optional[str] = Field(None, description="[已废弃] 音色文件，base64编码或URL（已废弃，请使用voice_url）")


class CharacterRequest(BaseModel):
    """自定义角色播客请求"""
    characters: List[CharacterInfo] = Field(..., description="角色列表", min_items=2, max_items=4)
    text: str = Field(..., description="文本素材（必需）")
    topic: Optional[str] = Field(None, description="播客主题（可选，主要用于背景音乐选择，如果不提供文本素材则作为对话主题）")
    silence_interval: int = Field(800, description="角色切换静音间隔（毫秒），默认800ms以增加角色之间的间隔，让对话更清晰", ge=200, le=1500)
    category: Optional[str] = Field(None, description="播客分类（可选），用于背景音乐选择，如：商业、科技、财经、新闻、影视、音乐、文化艺术、历史、哲学思考、自我成长、职场、学习、教育育儿、情感恋爱、健康养生、旅游、美食、生活方式、娱乐、游戏电竞、体育、时尚美妆、汽车、法律、宠物等")
    background_volume: float = Field(0.3, description="背景音乐音量（0.0-1.0）", ge=0.0, le=1.0)
    job_id: Optional[str] = Field(None, description="可选任务ID，用于前端轮询进度")


class DeepPodcastRequest(BaseModel):
    """主题深度播客请求"""
    topic: str = Field(..., description="播客主题")
    role_voice_urls: Dict[str, str] = Field(..., description="角色音色映射，云存储URL（必需，键为角色名，值为云存储下载URL）")
    role_voices: Optional[Dict[str, str]] = Field(None, description="[已废弃] 角色音色映射，base64编码的音频文件（已废弃，请使用role_voice_urls）")
    num_characters: int = Field(2, description="角色数量", ge=1, le=3)
    depth_level: str = Field("深度", description="深度级别", pattern="^(深度|中等|浅层)$")
    silence_interval: int = Field(800, description="角色切换静音间隔（毫秒），默认800ms以增加角色之间的间隔，让对话更清晰", ge=200, le=1500)
    category: Optional[str] = Field(None, description="播客分类（可选），用于背景音乐选择，如：商业、科技、财经、新闻、影视、音乐、文化艺术、历史、哲学思考、自我成长、职场、学习、教育育儿、情感恋爱、健康养生、旅游、美食、生活方式、娱乐、游戏电竞、体育、时尚美妆、汽车、法律、宠物等")
    background_volume: float = Field(0.3, description="背景音乐音量（0.0-1.0）", ge=0.0, le=1.0)
    wait_for_upload: bool = Field(False, description="是否等待上传到云存储完成（可选，默认false）")
    upload_timeout: int = Field(120, description="等待上传完成的超时时间（秒），如果为0则根据文件大小自动计算", ge=0, le=600)
    job_id: Optional[str] = Field(None, description="可选任务ID，用于前端轮询进度")


class ApiResponse(BaseModel):
    """API响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[Dict[str, Any]] = Field(None, description="响应数据")
    error: Optional[str] = Field(None, description="错误信息")


# ============ 工具函数 ============

def decode_base64_audio(base64_str: str, suffix: str = ".wav") -> str:
    """解码base64音频文件并保存到临时文件"""
    try:
        # 移除可能的数据URI前缀
        if "," in base64_str:
            base64_str = base64_str.split(",")[1]
        
        audio_data = base64.b64decode(base64_str)
        file_size = len(audio_data)
        file_size_mb = file_size / (1024 * 1024)
        
        logger.info(f"解码音频文件: 大小 {file_size_mb:.2f} MB")
        
        # 检查文件大小
        if file_size > MAX_AUDIO_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"音频文件过大: {file_size_mb:.2f} MB (限制: {MAX_AUDIO_FILE_SIZE / 1024 / 1024:.2f} MB)"
            )
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_file.write(audio_data)
        temp_file.close()
        
        logger.info(f"音频文件已保存到临时文件: {temp_file.name}")
        return temp_file.name
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"音频解码失败: {str(e)}")
        raise HTTPException(status_code=400, detail=f"音频解码失败: {str(e)}")


def convert_pcm_to_wav(pcm_path: str, wav_path: str, sample_rate: int = 48000, channels: int = 2, sample_width: int = 2) -> str:
    """将PCM文件转换为WAV格式
    
    Args:
        pcm_path: PCM文件路径
        wav_path: 输出WAV文件路径
        sample_rate: 采样率（默认48000 Hz，与前端录制参数一致）
        channels: 声道数（默认2，立体声）
        sample_width: 采样位宽（默认2字节，16位）
    
    Returns:
        WAV文件路径
    """
    import wave
    
    try:
        # 读取PCM数据
        with open(pcm_path, 'rb') as pcm_file:
            pcm_data = pcm_file.read()
        
        # 创建WAV文件
        with wave.open(wav_path, 'wb') as wav_file:
            wav_file.setnchannels(channels)  # 声道数
            wav_file.setsampwidth(sample_width)  # 采样位宽（字节）
            wav_file.setframerate(sample_rate)  # 采样率
            wav_file.writeframes(pcm_data)  # 写入PCM数据
        
        logger.info(f"PCM文件已转换为WAV: {pcm_path} -> {wav_path}")
        return wav_path
    except Exception as e:
        logger.error(f"PCM转WAV失败: {str(e)}")
        raise


def is_pcm_file(file_path: str) -> bool:
    """检测文件是否为PCM格式（通过检查文件头）
    
    WAV文件以"RIFF"开头，PCM文件没有这个头
    """
    try:
        with open(file_path, 'rb') as f:
            header = f.read(4)
            # WAV文件以"RIFF"开头，PCM文件没有这个头
            return header != b'RIFF'
    except Exception:
        return False


# 全局 Session 对象，用于复用连接池，提高下载速度
# 注意：在Python中，GIL确保了Session对象的线程安全性
_download_session = None

def _get_download_session():
    """获取全局下载 Session，实现连接池复用"""
    global _download_session
    if _download_session is None:
        _download_session = requests.Session()
        # 优化连接池配置，提高并发下载性能
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=50,  # 增加连接池数量（支持更多并发连接）
            pool_maxsize=100,  # 增加每个连接池的最大连接数
            max_retries=0  # 禁用urllib3的重试，我们自己处理
        )
        _download_session.mount('http://', adapter)
        _download_session.mount('https://', adapter)
        # 设置默认超时
        _download_session.timeout = (10, 120)  # (连接超时, 读取超时)
    return _download_session


def download_audio_from_url(url: str, suffix: str = ".wav", timeout: int = 120) -> str:
    """从URL下载音频文件并保存到临时文件
    
    注意：华为AGC云存储的下载URL通常可以直接访问，不需要额外认证。
    如果下载失败（如403 Forbidden），可能需要检查云存储的安全规则配置。
    
    如果下载的文件是PCM格式（扩展名为.wav但实际是PCM），会自动转换为WAV格式。
    """
    max_retries = 3
    retry_delay = 1  # 重试延迟（秒）
    
    for attempt in range(max_retries):
        try:
            logger.info(f"从URL下载音频文件: {url}" + (f" (重试 {attempt + 1}/{max_retries})" if attempt > 0 else ""))
            
            # 下载文件（华为AGC云存储的下载URL通常可以直接访问）
            # 优化请求头：音频文件通常不需要压缩，禁用压缩可能更快
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': '*/*',
                # 对于音频文件，禁用压缩可能更快（文件本身已压缩）
                # 'Accept-Encoding': 'gzip, deflate',  # 注释掉，让服务器直接返回原始数据
                'Connection': 'keep-alive',  # 保持连接，提高下载速度
                'Cache-Control': 'no-cache'  # 禁用缓存，确保获取最新数据
            }
            
            # 优化超时设置：连接超时和读取超时分开设置
            # 连接超时设置较短（10秒），读取超时设置较长（适应慢速下载）
            connect_timeout = 10
            read_timeout = timeout
            
            # 使用全局Session以复用连接池，提高下载速度
            session = _get_download_session()
            
            # 发送请求（使用全局Session，实现连接复用）
            response = session.get(
                url, 
                timeout=(connect_timeout, read_timeout),  # (连接超时, 读取超时)
                stream=True, 
                headers=headers,
                allow_redirects=True
            )
            response.raise_for_status()
            
            # 检查Content-Length
            content_length = response.headers.get("content-length")
            if content_length:
                file_size = int(content_length)
                file_size_mb = file_size / (1024 * 1024)
                logger.info(f"下载音频文件: 大小 {file_size_mb:.2f} MB")
                
                # 检查文件大小
                if file_size > MAX_AUDIO_FILE_SIZE:
                    raise HTTPException(
                        status_code=400,
                        detail=f"音频文件过大: {file_size_mb:.2f} MB (限制: {MAX_AUDIO_FILE_SIZE / 1024 / 1024:.2f} MB)"
                    )
            
            # 根据文件大小选择下载策略
            if content_length:
                file_size = int(content_length)
                file_size_mb = file_size / (1024 * 1024)
            else:
                file_size = None
                file_size_mb = None
            
            start_time = time.time()
            
            # 对于小文件（<1MB），直接下载可能更快
            if content_length and file_size < 1024 * 1024:
                # 小文件直接下载
                logger.info(f"小文件直接下载 (文件大小: {file_size_mb:.2f} MB)")
                downloaded_data = response.content
                downloaded_size = len(downloaded_data)
                
                # 保存到临时文件
                temp_file_obj = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                temp_file_obj.write(downloaded_data)
                temp_file_obj.close()
                temp_file_path = temp_file_obj.name
            else:
                # 大文件使用流式下载，增大 chunk_size 以提高下载速度
                temp_file_obj = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                downloaded_size = 0
                
                # 根据文件大小动态调整chunk_size，增大以提升下载速度
                if content_length:
                    if file_size_mb > 20:
                        chunk_size = 4 * 1024 * 1024  # 4MB chunks，超大文件
                    elif file_size_mb > 10:
                        chunk_size = 2 * 1024 * 1024  # 2MB chunks，大文件
                    elif file_size_mb > 2:
                        chunk_size = 2 * 1024 * 1024  # 2MB chunks，中等文件（2-10MB）
                    else:
                        chunk_size = 1024 * 1024  # 1MB chunks，小文件（1-2MB）
                else:
                    chunk_size = 2 * 1024 * 1024  # 默认2MB，如果没有Content-Length
                
                logger.info(f"使用流式下载，chunk_size: {chunk_size / 1024 / 1024:.1f} MB (文件大小: {file_size_mb:.2f} MB)" if content_length else f"使用流式下载，chunk_size: {chunk_size / 1024 / 1024:.1f} MB (文件大小未知)")
                
                try:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            temp_file_obj.write(chunk)
                            downloaded_size += len(chunk)
                            # 检查下载大小
                            if downloaded_size > MAX_AUDIO_FILE_SIZE:
                                temp_file_obj.close()
                                os.unlink(temp_file_obj.name)
                                raise HTTPException(
                                    status_code=400,
                                    detail=f"音频文件过大: {downloaded_size / (1024 * 1024):.2f} MB (限制: {MAX_AUDIO_FILE_SIZE / 1024 / 1024:.2f} MB)"
                                )
                finally:
                    temp_file_obj.close()
                temp_file_path = temp_file_obj.name
            
            download_time = time.time() - start_time
            download_speed = (downloaded_size / (1024 * 1024)) / download_time if download_time > 0 else 0
            
            if download_time > 5:  # 如果下载时间超过5秒，记录警告
                logger.warning(f"音频文件下载较慢: {download_time:.2f}秒，文件大小: {downloaded_size / (1024 * 1024):.2f} MB，速度: {download_speed:.2f} MB/s")
            else:
                logger.info(f"音频文件下载完成: {download_time:.2f}秒，速度: {download_speed:.2f} MB/s")
            
            # 检测文件格式：如果扩展名是.wav但实际是PCM格式，转换为WAV
            if suffix == ".wav" and is_pcm_file(temp_file_path):
                logger.info(f"检测到PCM格式文件，正在转换为WAV格式...")
                wav_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                wav_file.close()
                try:
                    convert_pcm_to_wav(temp_file_path, wav_file.name)
                    # 删除原始PCM文件
                    os.unlink(temp_file_path)
                    logger.info(f"PCM文件已转换为WAV: {wav_file.name}")
                    return wav_file.name
                except Exception as e:
                    logger.error(f"PCM转WAV失败: {str(e)}，使用原始文件")
                    # 如果转换失败，返回原始文件
                    return temp_file_path
            
            return temp_file_path
            
        except requests.exceptions.Timeout as e:
            if attempt < max_retries - 1:
                logger.warning(f"下载超时，{retry_delay}秒后重试 ({attempt + 1}/{max_retries})...")
                time.sleep(retry_delay)
                retry_delay *= 2  # 指数退避
                continue
            else:
                logger.error(f"下载音频文件失败: 超时（已重试{max_retries}次）")
                raise HTTPException(status_code=400, detail=f"下载音频文件失败: 超时（已重试{max_retries}次）")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logger.error(f"下载音频文件失败: 403 Forbidden - 可能是云存储安全规则限制或需要认证")
                logger.error(f"请检查华为AGC云存储的安全规则配置，确保下载URL可以公开访问")
                raise HTTPException(status_code=400, detail=f"下载音频文件失败: 403 Forbidden - 请检查云存储安全规则配置")
            elif e.response.status_code >= 500 and attempt < max_retries - 1:
                # 服务器错误，重试
                logger.warning(f"服务器错误 {e.response.status_code}，{retry_delay}秒后重试 ({attempt + 1}/{max_retries})...")
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            else:
                logger.error(f"下载音频文件失败: HTTP {e.response.status_code} - {str(e)}")
                raise HTTPException(status_code=400, detail=f"下载音频文件失败: HTTP {e.response.status_code} - {str(e)}")
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                logger.warning(f"下载请求异常: {str(e)}，{retry_delay}秒后重试 ({attempt + 1}/{max_retries})...")
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            else:
                logger.error(f"下载音频文件失败: {str(e)}")
                raise HTTPException(status_code=400, detail=f"下载音频文件失败: {str(e)}")
        except HTTPException:
            raise
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"下载异常: {str(e)}，{retry_delay}秒后重试 ({attempt + 1}/{max_retries})...")
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            else:
                logger.error(f"下载音频文件异常: {str(e)}")
                raise HTTPException(status_code=500, detail=f"下载音频文件异常: {str(e)}")


def download_text_from_url(url: Union[str, List[str]], timeout: int = 120) -> str:
    """从URL下载文本文件并返回内容（支持.txt、Word文件和PDF文件）
    
    Args:
        url: 文本文件的云存储URL（单个字符串）或URL列表（多个文件，内容会合并）
        timeout: 超时时间（秒）
        
    Returns:
        文本内容（字符串），多个文件时内容会合并，用换行分隔
        
    注意：华为AGC云存储的下载URL通常可以直接访问，不需要额外认证。
    如果下载失败（如403 Forbidden），可能需要检查云存储的安全规则配置。
    """
    # 如果传入的是列表，处理多个文件（使用并发下载）
    if isinstance(url, list):
        logger.info(f"从多个URL下载文本文件: {len(url)} 个文件")
        
        # 如果只有一个文件，直接下载
        if len(url) == 1:
            return download_text_from_url(url[0], timeout)
        
        # 多个文件使用并发下载
        import concurrent.futures
        all_texts = []
        file_urls_with_index = [(i, single_url) for i, single_url in enumerate(url)]
        
        def download_single_file(index_url_tuple):
            index, single_url = index_url_tuple
            logger.info(f"开始下载第 {index+1}/{len(url)} 个文件: {single_url}")
            try:
                text = download_text_from_url(single_url, timeout)  # 递归调用处理单个文件
                if text:
                    logger.info(f"第 {index+1} 个文件下载成功: {len(text)} 字符")
                    return index, text, None
                else:
                    logger.warning(f"第 {index+1} 个文件下载后内容为空")
                    return index, None, "内容为空"
            except Exception as e:
                logger.error(f"第 {index+1} 个文件下载失败: {str(e)}")
                return index, None, str(e)
        
        # 使用线程池并发下载（最多5个并发，文本文件通常较小）
        download_start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(5, len(url))) as executor:
            future_to_index = {executor.submit(download_single_file, item): item[0] for item in file_urls_with_index}
            results = {}
            for future in concurrent.futures.as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    result_index, text, error = future.result()
                    results[result_index] = (text, error)
                except Exception as e:
                    logger.error(f"文件 {index+1} 下载异常: {str(e)}")
                    results[index] = (None, str(e))
        
        # 按原始顺序合并文件内容
        for i in range(len(url)):
            if i in results:
                text, error = results[i]
                if text:
                    all_texts.append(text)
                elif error:
                    logger.warning(f"文件 {i+1} 下载失败: {error}")
        
        download_time = time.time() - download_start
        logger.info(f"所有文件下载完成，总耗时: {download_time:.2f}秒")
        
        if not all_texts:
            raise Exception("所有文件下载失败或内容为空")
        
        # 合并所有文件内容，用两个换行分隔
        merged_text = "\n\n".join(all_texts)
        logger.info(f"文件内容合并完成，合并后总长度: {len(merged_text)} 字符")
        return merged_text
    
    # 单个文件处理（原有逻辑）
    try:
        logger.info(f"从URL下载文本文件: {url}")
        
        # 下载文件（华为AGC云存储的下载URL通常可以直接访问）
        # 如果URL需要认证，可以在headers中添加Authorization头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'  # 保持连接，提高下载速度
        }
        # 使用Session以复用连接，提高下载速度
        session = requests.Session()
        try:
            response = session.get(url, timeout=timeout, stream=True, headers=headers)
            response.raise_for_status()
        finally:
            session.close()
        
        # 检查Content-Type和Content-Length
        content_type = response.headers.get("content-type", "").lower()
        content_length = response.headers.get("content-length")
        # 从URL中提取文件扩展名（支持查询参数的情况）
        url_path = url.split('?')[0]  # 移除查询参数
        file_extension = url_path.lower().split('.')[-1] if '.' in url_path else ''
        
        # 流式读取文件内容（根据文件大小动态调整chunk_size以提高下载速度）
        content_bytes = b''
        # 根据Content-Length动态调整chunk_size
        if content_length:
            file_size_mb = int(content_length) / (1024 * 1024)
            if file_size_mb > 20:
                chunk_size = 2 * 1024 * 1024  # 2MB chunks，超大文件
            elif file_size_mb > 10:
                chunk_size = 1024 * 1024  # 1MB chunks，大文件
            elif file_size_mb > 5:
                chunk_size = 512 * 1024  # 512KB chunks，中等文件
            else:
                chunk_size = 256 * 1024  # 256KB chunks，小文件
        else:
            chunk_size = 512 * 1024  # 默认512KB，如果没有Content-Length
        download_start = time.time()
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                content_bytes += chunk
        download_time = time.time() - download_start
        download_speed = (len(content_bytes) / (1024 * 1024)) / download_time if download_time > 0 else 0
        if download_time > 3:  # 如果下载时间超过3秒，记录警告
            logger.warning(f"文本文件下载较慢: {download_time:.2f}秒，文件大小: {len(content_bytes) / (1024 * 1024):.2f} MB，速度: {download_speed:.2f} MB/s")
        else:
            logger.info(f"文本文件下载完成: {download_time:.2f}秒，速度: {download_speed:.2f} MB/s")
        
        # 如果无法从URL确定文件类型，尝试从Content-Type判断
        if not file_extension:
            if 'application/pdf' in content_type:
                file_extension = 'pdf'
            elif 'application/msword' in content_type or 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' in content_type:
                file_extension = 'docx' if 'vnd.openxmlformats' in content_type else 'doc'
            elif 'text/plain' in content_type:
                file_extension = 'txt'
        
        # 如果仍然无法确定，尝试从文件内容检测（通过文件头）
        if not file_extension:
            # 检测PDF文件头：%PDF
            if content_bytes[:4] == b'%PDF':
                file_extension = 'pdf'
                logger.info("通过文件头检测到PDF文件")
            # 检测Word文件头：PK (ZIP格式，docx是zip)
            elif content_bytes[:4] == b'PK\x03\x04':
                # 检查是否是docx（包含word/目录）
                if b'word/' in content_bytes[:2048]:
                    file_extension = 'docx'
                    logger.info("通过文件头检测到DOCX文件")
                else:
                    # 可能是其他ZIP格式文件
                    logger.warning("检测到ZIP格式文件，但无法确定是否为Word文件")
            # 检测旧版Word文件头（OLE2格式）
            elif content_bytes[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
                file_extension = 'doc'
                logger.info("通过文件头检测到DOC文件")
        
        logger.info(f"检测到的文件类型: 扩展名={file_extension}, Content-Type={content_type}")
        
        # 根据文件类型解析内容
        if file_extension == 'txt' or 'text/plain' in content_type:
            # 纯文本文件，尝试多种编码
            try:
                # 尝试UTF-8
                text = content_bytes.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    # 尝试GBK（中文常用）
                    text = content_bytes.decode('gbk')
                except UnicodeDecodeError:
                    # 尝试GB2312
                    try:
                        text = content_bytes.decode('gb2312')
                    except UnicodeDecodeError:
                        # 最后尝试latin-1（不会失败）
                        text = content_bytes.decode('latin-1', errors='ignore')
            logger.info(f"文本文件读取成功: {len(text)} 字符")
            return text
        elif file_extension == 'pdf' or 'application/pdf' in content_type:
            # PDF文件，使用input_processor提取文本
            try:
                from .input_processor import get_processor
                input_processor = get_processor()
                # 保存为临时文件，然后提取文本
                import tempfile
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                temp_file.write(content_bytes)
                temp_file.close()
                try:
                    text = input_processor.extract_text_from_pdf_file(temp_file.name)
                    logger.info(f"PDF文件读取成功: {len(text)} 字符")
                    return text
                finally:
                    # 删除临时文件
                    try:
                        import os
                        os.unlink(temp_file.name)
                    except:
                        pass
            except Exception as e:
                logger.error(f"PDF文件解析失败: {str(e)}")
                raise HTTPException(
                    status_code=400,
                    detail=f"PDF文件解析失败: {str(e)}。请确保已安装pdfplumber或PyPDF2库: pip install pdfplumber"
                )
        elif file_extension in ['doc', 'docx'] or 'application/msword' in content_type or 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' in content_type:
            # Word文件，需要使用python-docx库
            try:
                import docx
                from io import BytesIO
                
                # 从字节流读取Word文档
                doc = docx.Document(BytesIO(content_bytes))
                
                # 提取所有段落文本
                text_parts = []
                for paragraph in doc.paragraphs:
                    if paragraph.text.strip():
                        text_parts.append(paragraph.text.strip())
                
                text = '\n'.join(text_parts)
                logger.info(f"Word文件读取成功: {len(text)} 字符")
                return text
            except ImportError:
                logger.error("需要安装python-docx库来处理Word文件: pip install python-docx")
                raise HTTPException(
                    status_code=500,
                    detail="Word文件处理需要python-docx库，请安装: pip install python-docx"
                )
            except Exception as e:
                logger.error(f"Word文件解析失败: {str(e)}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Word文件解析失败: {str(e)}"
                )
        else:
            # 未知文件类型，尝试作为文本处理
            logger.warning(f"未知文件类型: {file_extension}，尝试作为文本处理或Docx解析")

            # 有些情况下，URL 可能返回的是 docx（zip） 文件但扩展名或 content-type 不明确。
            # 尝试检测 docx 的 zip 文件头（PK）或包含 word/ 路径，以便使用 python-docx 解析。
            try:
                is_docx = False
                # 快速检查前几个字节是否为 zip 文件头 PK
                if content_bytes[:4] == b'PK\x03\x04':
                    is_docx = True
                # 或者前 2KB 内含有 word/ 路径提示
                elif b'word/' in content_bytes[:2048]:
                    is_docx = True

                if is_docx:
                    try:
                        import docx
                        from io import BytesIO

                        doc = docx.Document(BytesIO(content_bytes))
                        text_parts = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
                        text = '\n'.join(text_parts)
                        logger.info(f"Docx 文件解析成功，提取文本长度: {len(text)} 字符")
                        return text
                    except ImportError:
                        logger.error("需要安装python-docx库来处理docx文件: pip install python-docx")
                        raise HTTPException(
                            status_code=500,
                            detail="文件可能为docx格式；请安装python-docx库: pip install python-docx"
                        )
                    except Exception as e:
                        logger.warning(f"尝试作为docx解析失败，回退为文本解析: {str(e)}")

                # 回退为文本解析：尝试多种编码并剔除不可打印字符
                try:
                    text = content_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        text = content_bytes.decode('gbk')
                    except UnicodeDecodeError:
                        text = content_bytes.decode('latin-1', errors='ignore')

                # 移除明显的二进制/控制字符，保留换行和制表
                cleaned = []
                for ch in text:
                    if ch in ('\n', '\r', '\t'):
                        cleaned.append(ch)
                    elif ch.isprintable():
                        cleaned.append(ch)
                text = ''.join(cleaned)

                return text
            except Exception as e:
                logger.error(f"处理未知文本文件异常: {str(e)}")
                raise HTTPException(status_code=500, detail=f"处理文本文件异常: {str(e)}")
            
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            logger.error(f"下载文本文件失败: 403 Forbidden - 可能是云存储安全规则限制或需要认证")
            logger.error(f"请检查华为AGC云存储的安全规则配置，确保下载URL可以公开访问")
            raise HTTPException(status_code=400, detail=f"下载文本文件失败: 403 Forbidden - 请检查云存储安全规则配置")
        else:
            logger.error(f"下载文本文件失败: HTTP {e.response.status_code} - {str(e)}")
            raise HTTPException(status_code=400, detail=f"下载文本文件失败: HTTP {e.response.status_code} - {str(e)}")
    except requests.exceptions.RequestException as e:
        logger.error(f"下载文本文件失败: {str(e)}")
        raise HTTPException(status_code=400, detail=f"下载文本文件失败: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理文本文件异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理文本文件异常: {str(e)}")


def get_audio_file(voice_data: str, voice_url: Optional[str] = None, suffix: str = ".wav") -> str:
    """获取音频文件（从base64或URL）
    
    Args:
        voice_data: base64编码的音频数据或URL
        voice_url: 云存储URL（如果提供，优先使用）
        suffix: 文件后缀
        
    Returns:
        临时文件路径
    """
    # 如果提供了URL，优先使用URL
    if voice_url:
        return download_audio_from_url(voice_url, suffix)
    
    # 判断voice_data是URL还是base64
    if voice_data.startswith("http://") or voice_data.startswith("https://"):
        return download_audio_from_url(voice_data, suffix)
    else:
        return decode_base64_audio(voice_data, suffix)


def _find_agc_client_json() -> Optional[str]:
    """在工作目录或仓库根查找 agc-apiclient-*.json 文件，返回第一个匹配路径"""
    # 尝试当前工作目录和父目录
    patterns = ["agc-apiclient-*.json", "./agc-apiclient-*.json", "../agc-apiclient-*.json"]
    for pat in patterns:
        matches = glob.glob(pat)
        if matches:
            return matches[0]
    # 尝试项目根下（/workspace/hunyuan 或 repo root）
    matches = glob.glob(os.path.join(os.getcwd(), "agc-apiclient-*.json"))
    if matches:
        return matches[0]
    return None


def _load_agc_credentials_from_file(path: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """从 agc-apiclient JSON 中读取 client_id, client_secret, project_id"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            j = json.load(f)
        client_id = j.get('client_id')
        client_secret = j.get('client_secret')
        # 尝试多种可能的字段名
        project_id = j.get('project_id') or j.get('projectId') or j.get('projectId')
        logger.info(f"从 {path} 读取配置: client_id={'已设置' if client_id else '未设置'}, project_id={'已设置' if project_id else '未设置'}")
        return client_id, client_secret, project_id
    except Exception as e:
        logger.error(f"读取 AGC 凭证文件失败: {e}")
        return None, None, None


def encode_file_to_base64(file_path: str) -> str:
    """将文件编码为base64"""
    try:
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件编码失败: {str(e)}")


def calculate_upload_timeout(file_path: str, base_timeout: int = 300) -> int:
    """根据文件大小动态计算上传超时时间
    
    Args:
        file_path: 文件路径
        base_timeout: 基础超时时间（秒），默认300秒（5分钟）
        
    Returns:
        计算后的超时时间（秒），最小120秒，最大1800秒（30分钟）
    """
    try:
        if os.path.exists(file_path):
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            # 假设最小上传速度为0.1 MB/s（慢速网络）
            # 计算所需时间：文件大小(MB) / 最小速度(MB/s) + 缓冲时间
            min_upload_speed_mbps = 0.1
            calculated_timeout = int((file_size_mb / min_upload_speed_mbps) + 120)  # 至少120秒缓冲
            # 对于大文件（>10MB），额外增加时间
            if file_size_mb > 10:
                calculated_timeout += int((file_size_mb - 10) * 5)  # 大文件额外时间
            # 使用base_timeout和calculated_timeout中的较大值
            final_timeout = max(base_timeout, calculated_timeout)
            # 限制在120-1800秒之间（2分钟到30分钟）
            return max(120, min(1800, final_timeout))
    except Exception as e:
        logger.warning(f"计算上传超时时间失败: {e}，使用默认值 {base_timeout}")
    return base_timeout


def do_agc_upload(output_path: str, storage_url: str, bucket: str, product_id: Optional[str] = None,
                  domain: str = 'connect-api.cloud.huawei.com', client_id: Optional[str] = None,
                  client_secret: Optional[str] = None):
    """在后台执行 AGC 上传任务的 helper（供 BackgroundTasks 调用）"""
    try:
        if not agc_upload_client:
            logger.debug("未找到内部 agc 上传客户端，跳过后台上传")
            return

        logger.info(f"后台上传开始: {output_path} -> {bucket} (storage={storage_url})")
        try:
            res = agc_upload_client(
                output_path=output_path,
                storage_url=storage_url,
                bucket=bucket,
                product_id=product_id,
                domain=domain,
                client_id=client_id,
                client_secret=client_secret,
            )
            logger.info(f"后台 AGC 上传完成: {res}")
        except Exception as e:
            logger.exception(f"后台 AGC 上传失败: {e}")
    except Exception:
        logger.exception("do_agc_upload 异常")


# ============ API端点 ============

@app.get("/", response_model=ApiResponse)
async def root():
    """根端点，返回API信息"""
    return ApiResponse(
        success=True,
        message="混元AI播客生成API服务",
        data={
            "version": "1.0.0",
            "endpoints": {
                "multi_role": "/api/v1/podcast/multi_role",
                "character": "/api/v1/podcast/character",
                "deep": "/api/v1/podcast/deep",
                "analyze": "/api/v1/podcast/analyze",
                "health": "/health",
                "docs": "/docs"
            }
        }
    )


@app.get("/health")
async def health():
    """健康检查端点"""
    return {"status": "healthy", "service": "混元AI播客生成API"}


# 处理422验证错误
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求验证错误（422）"""
    errors = exc.errors()
    error_details = []
    for error in errors:
        field = ".".join(str(loc) for loc in error.get("loc", []))
        error_type = error.get("type", "unknown")
        error_msg = error.get("msg", "验证失败")
        error_details.append({
            "field": field,
            "type": error_type,
            "message": error_msg,
            "input": error.get("input")
        })
    
    logger.error(f"请求验证失败 (422): {request.method} {request.url.path}")
    logger.error(f"验证错误详情: {json.dumps(error_details, ensure_ascii=False, indent=2)}")
    
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "请求参数验证失败",
            "error": "请求参数不符合API要求",
            "details": error_details
        }
    )


@app.post("/api/v1/podcast/multi_role", response_model=ApiResponse)
async def generate_multi_role_podcast(request: MultiRoleRequest, background_tasks: BackgroundTasks):
    """
    生成多角色互动播客（子题目1）
    
    - **text**: 播客文本（支持角色标记或普通文本）
    - **role_voice_urls**: 角色音色映射，键为角色名，值为云存储下载URL（必需）
    - **silence_interval**: 角色切换静音间隔（毫秒）
    - **podcast_name**: 播客名称（可选）
    - **topic**: 本期主题（可选）
    - **character_1_name**: 角色1名称（可选）
    - **character_1_personality**: 角色1性格特点（可选）
    - **character_1_speaking_style**: 角色1说话风格（可选）
    - **character_2_name**: 角色2名称（可选）
    - **character_2_personality**: 角色2性格特点（可选）
    - **character_2_speaking_style**: 角色2说话风格（可选）
    - **character_3_name**: 角色3名称（可选）
    - **character_3_personality**: 角色3性格特点（可选）
    - **character_3_speaking_style**: 角色3说话风格（可选）
    - **scene_types**: 互动场景类型列表（可选），如：["接梗玩梗的轻松交流", "立场冲突的激烈辩论"]
    
    注意：本接口仅支持云存储URL，不再支持base64编码的音频文件
    """
    # 立即创建初始进度，确保前端轮询时能立即获取到状态
    _update_progress(request.job_id, "queued", 1, "任务已提交，准备开始处理")
    start_time = time.time()
    
    # 验证文本输入（text、text_file_url或input_url至少有一个）
    has_text = request.text and request.text.strip()
    # 支持单个URL字符串或URL列表
    if isinstance(request.text_file_url, list):
        has_text_file = len(request.text_file_url) > 0 and any(url and url.strip() for url in request.text_file_url)
    else:
        has_text_file = request.text_file_url and request.text_file_url.strip()
    has_input_url = request.input_url and request.input_url.strip()
    has_input_type = request.input_type and request.input_type.strip()
    
    # 如果没有指定input_type，自动检测
    if not has_input_type:
        if has_input_url:
            # 根据URL自动检测类型
            input_processor = get_processor()
            request.input_type = input_processor.detect_input_type_from_content("", request.input_url)
            logger.info(f"自动检测输入类型: {request.input_type}")
        elif has_text_file:
            # 如果有文件，可能是文件类型
            request.input_type = "文件"
            logger.info(f"自动检测输入类型: {request.input_type}")
        elif has_text:
            # 根据文本内容检测是否包含指令
            input_processor = get_processor()
            request.input_type = input_processor.detect_input_type_from_content(request.text)
            logger.info(f"自动检测输入类型: {request.input_type}")
        else:
            # 默认类型
            request.input_type = "文字"
    
    # 根据输入类型验证必需的输入
    input_type = request.input_type or ""
    text_types = ["文字", "文字+指令", "文字+英文指令"]
    file_types = ["文件", "文件+指令"]
    url_types = ["公众号", "公众号+指令", "网页", "网页+指令"]
    
    # 文字类型：只需要text，不需要text_file_url
    if input_type in text_types:
        if not has_text:
            raise HTTPException(status_code=400, detail="文字类型需要提供文本内容（text字段）")
        if has_text_file:
            logger.warning(f"文字类型不需要text_file_url，将忽略该字段")
            request.text_file_url = None
    
    # 文件类型：只需要text_file_url，不需要text（支持.txt、.doc、.docx、.pdf等文件）
    elif input_type in file_types:
        if not has_text_file:
            raise HTTPException(status_code=400, detail="文件类型需要上传文件（text_file_url字段，支持.txt、.doc、.docx、.pdf等格式）")
        if has_text:
            logger.warning(f"文件类型不需要text，将忽略该字段")
            request.text = None
    
    # 公众号/网页类型：需要input_url
    elif input_type in url_types:
        if not has_input_url and not has_text_file:
            raise HTTPException(status_code=400, detail=f"{input_type}类型需要提供输入URL（input_url字段）或上传文件")
    
    # 获取文本内容和指令
    text_content = ""
    extracted_instruction = request.instruction
    
    # 根据输入类型获取文本内容
    if input_type in url_types:
        # 公众号/网页类型：使用输入处理器处理URL
        try:
            input_processor = get_processor()
            _update_progress(request.job_id, "processing_input", 3, f"正在处理{input_type}类型输入")
            text_content, extracted_instruction = input_processor.process_input(
                input_type=input_type,
                input_content=None,
                input_url=request.input_url if has_input_url else None,
                instruction=request.instruction
            )
            logger.info(f"{input_type}类型输入处理成功: {len(text_content)} 字符")
            if extracted_instruction:
                logger.info(f"提取的指令: {extracted_instruction}")
        except Exception as e:
            logger.error(f"处理{input_type}类型输入失败: {str(e)}")
            raise HTTPException(status_code=400, detail=f"处理{input_type}类型输入失败: {str(e)}")
    elif input_type in file_types:
        # 文件类型：从云存储URL读取文件（支持.txt、.doc、.docx、.pdf等格式）
        # 支持单个URL或URL列表
        file_urls = request.text_file_url
        if isinstance(file_urls, str):
            file_urls = [file_urls]  # 转换为列表统一处理
        logger.info(f"从云存储URL读取文件: {len(file_urls)} 个文件")
        try:
            _update_progress(request.job_id, "downloading_text", 3, f"正在下载{len(file_urls)}个文件")
            text_content = download_text_from_url(file_urls)
            logger.info(f"文件读取成功: {len(text_content)} 字符")
            
            # 如果输入类型包含指令，尝试解析指令
            if "指令" in input_type or "instruction" in input_type.lower():
                input_processor = get_processor()
                text_content, extracted_instruction = input_processor.parse_instruction(text_content)
                if extracted_instruction:
                    logger.info(f"从文件中提取的指令: {extracted_instruction}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"读取文件失败: {str(e)}")
            raise HTTPException(status_code=400, detail=f"读取文件失败: {str(e)}")
    elif input_type in text_types:
        # 文字类型：使用直接输入的文本
        text_content = request.text
        
        # 如果输入类型包含指令，尝试解析指令
        if "指令" in input_type or "instruction" in input_type.lower():
            input_processor = get_processor()
            text_content, extracted_instruction = input_processor.parse_instruction(text_content)
            if extracted_instruction:
                logger.info(f"从文本中提取的指令: {extracted_instruction}")
        
        logger.info(f"使用直接输入的文本: {len(text_content)} 字符")
    else:
        # 其他未知类型，使用通用处理
        if has_input_url or has_input_type:
            try:
                input_processor = get_processor()
                _update_progress(request.job_id, "processing_input", 3, f"正在处理{input_type}类型输入")
                text_content, extracted_instruction = input_processor.process_input(
                    input_type=input_type,
                    input_content=request.text if has_text else None,
                    input_url=request.input_url if has_input_url else None,
                    instruction=request.instruction
                )
                logger.info(f"{input_type}类型输入处理成功: {len(text_content)} 字符")
            except Exception as e:
                logger.error(f"处理{input_type}类型输入失败: {str(e)}")
                raise HTTPException(status_code=400, detail=f"处理{input_type}类型输入失败: {str(e)}")
        elif has_text_file:
            # 从云存储URL读取文本文件（兼容旧逻辑）
            # 支持单个URL或URL列表
            file_urls = request.text_file_url
            if isinstance(file_urls, str):
                file_urls = [file_urls]  # 转换为列表统一处理
            logger.info(f"从云存储URL读取文本文件: {len(file_urls)} 个文件")
            try:
                _update_progress(request.job_id, "downloading_text", 3, f"正在下载{len(file_urls)}个文本文件")
                text_content = download_text_from_url(file_urls)
                logger.info(f"文本文件读取成功: {len(text_content)} 字符")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"读取文本文件失败: {str(e)}")
                raise HTTPException(status_code=400, detail=f"读取文本文件失败: {str(e)}")
        elif has_text:
            text_content = request.text
            logger.info(f"使用直接输入的文本: {len(text_content)} 字符")
        else:
            raise HTTPException(status_code=400, detail="text、text_file_url或input_url至少需要提供一个")
    
    # 如果提取了指令，将其应用到播客生成参数
    if extracted_instruction:
        # 这里可以将指令应用到生成参数，例如：
        # - 如果指令包含"5分钟"，设置更长的对话
        # - 如果指令包含"轻松"，设置轻松的场景类型
        # 目前先记录，后续可以扩展
        logger.info(f"将应用指令到播客生成: {extracted_instruction}")
        
        # 简单的指令解析和应用
        instruction_lower = extracted_instruction.lower()
        if "轻松" in extracted_instruction or "轻松" in instruction_lower or "relaxed" in instruction_lower:
            if not request.scene_types:
                request.scene_types = []
            if "接梗玩梗的轻松交流" not in request.scene_types:
                request.scene_types.append("接梗玩梗的轻松交流")
        if "激烈" in extracted_instruction or "激烈" in instruction_lower or "intense" in instruction_lower:
            if not request.scene_types:
                request.scene_types = []
            if "立场冲突的激烈辩论" not in request.scene_types:
                request.scene_types.append("立场冲突的激烈辩论")
    
    # 验证音色数据（role_voice_urls或role_voices至少有一个）
    has_voice_urls = request.role_voice_urls and len(request.role_voice_urls) > 0
    has_voices = request.role_voices and len(request.role_voices) > 0
    
    if not has_voice_urls and not has_voices:
        raise HTTPException(
            status_code=400, 
            detail="至少需要提供一个角色的音色文件（role_voice_urls或role_voices）"
        )
    
    # 确定使用哪个字段
    use_cloud_storage = has_voice_urls
    role_voice_data = request.role_voice_urls if use_cloud_storage else request.role_voices
    
    logger.info(f"开始生成多角色播客: 角色数量={len(role_voice_data)}, 文本长度={len(text_content)}, 使用云存储={use_cloud_storage}")
    
    try:
        gen = get_generator()
        processor = TextProcessor()
        
        # 获取音频文件（从云存储URL或base64）
        temp_files = []
        role_voices = {}
        
        # 性能统计：检索信息
        retrieval_timings = {}
        
        try:
            _update_progress(request.job_id, "downloading_voices", 5, "正在下载角色音色文件")
            voice_download_start = time.time()
            
            # 使用并发下载以提高速度（所有角色文件同时下载，包括单个文件）
            import concurrent.futures
            
            def download_role_voice(role_voice_tuple):
                role, voice_data = role_voice_tuple
                role_download_start = time.time()
                logger.info(f"开始获取角色 '{role}' 的音频文件...")
                try:
                    if use_cloud_storage:
                        # 从云存储URL下载
                        logger.info(f"从云存储下载: {voice_data}")
                        temp_file = download_audio_from_url(voice_data)
                    else:
                        # 从base64解码
                        logger.info(f"从base64解码")
                        temp_file = decode_base64_audio(voice_data)
                    role_download_time = time.time() - role_download_start
                    logger.info(f"角色 '{role}' 音频文件获取完成，耗时: {role_download_time:.2f}s")
                    return role, temp_file, role_download_time
                except Exception as e:
                    logger.error(f"角色 '{role}' 音频文件获取失败: {str(e)}")
                    raise
            
            # 使用线程池并发下载（最多5个并发，提高下载速度）
            logger.info(f"使用并发下载 {len(role_voice_data)} 个角色音色文件...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(5, len(role_voice_data))) as executor:
                future_to_role = {executor.submit(download_role_voice, item): item[0] for item in role_voice_data.items()}
                for future in concurrent.futures.as_completed(future_to_role):
                    role = future_to_role[future]
                    try:
                        role_name, temp_file, role_download_time = future.result()
                        retrieval_timings[f"角色音色下载_{role_name}"] = role_download_time
                        temp_files.append(temp_file)
                        role_voices[role_name] = temp_file
                    except Exception as e:
                        logger.error(f"角色 '{role}' 下载失败: {str(e)}")
                        raise
            
            voice_download_total = time.time() - voice_download_start
            retrieval_timings["角色音色下载_总计"] = voice_download_total
            logger.info(f"所有角色音色文件下载完成，总耗时: {voice_download_total:.2f}s")
            
            # 音效文件支持（如果未来需要）
            intro_music_path = None
            outro_music_path = None
            background_music_path = None
            
            # 解析文本中的角色
            roles = processor.extract_roles(text_content)
            
            # 如果没有找到角色标记，使用混元大模型自动转换为多角色对话
            if not roles:
                api_client = get_client()
                num_characters = min(len(role_voices), 3)
                
                # 构建角色描述字典
                character_descriptions = {}
                characters = [
                    (request.character_1_name, request.character_1_personality, request.character_1_speaking_style),
                    (request.character_2_name, request.character_2_personality, request.character_2_speaking_style),
                    (request.character_3_name, request.character_3_personality, request.character_3_speaking_style),
                ]
                
                role_keys = ["角色A", "角色B", "角色C"]
                for i, (name, personality, speaking_style) in enumerate(characters[:num_characters]):
                    if name and name.strip():
                        role_key = role_keys[i] if i < len(role_keys) else f"角色{chr(65+i)}"
                        character_descriptions[role_key] = {
                            "name": name.strip(),
                            "personality": personality.strip() if personality else "",
                            "speaking_style": speaking_style.strip() if speaking_style else ""
                        }
                
                prompt = processor.build_text_to_dialogue_prompt(
                    text=text_content,
                    num_characters=num_characters,
                    podcast_name=request.podcast_name if request.podcast_name else None,
                    topic=request.topic if request.topic else None,
                    character_descriptions=character_descriptions if character_descriptions else None,
                    scene_types=request.scene_types if request.scene_types else None,
                    category=request.category if request.category else None
                )
                
                text_generation_start = time.time()
                generated_text = api_client.generate_text(
                    prompt=prompt,
                    temperature=0.7,  # 提高温度以增加对话的自然性和多样性
                    max_tokens=6000  # 增加到6000以支持更长的对话（8-10分钟播客）
                )
                text_generation_time = time.time() - text_generation_start
                retrieval_timings["对话文本生成"] = text_generation_time
                logger.info(f"对话文本生成完成，耗时: {text_generation_time:.2f}s，文本长度: {len(generated_text)}")
                
                generated_text = processor.clean_text(generated_text)
                text_content = generated_text
                roles = processor.extract_roles(text_content)
            
            # 自动选择背景音乐（在AI生成对话之后，使用完整的文本内容）
            try:
                _update_progress(request.job_id, "selecting_music", 22, "正在选择背景音乐")
                logger.info("开始自动选择背景音乐...")
                music_selection_start = time.time()
                music_selector = MusicSelector(use_cloud_storage=False)
                selected_music = music_selector.select_music_by_ai(
                    text=text_content,  # 使用完整的文本内容（包括AI生成的对话）
                    podcast_name=request.podcast_name,
                    topic=request.topic,
                    scene_types=request.scene_types,
                    category=request.category if hasattr(request, 'category') else None,
                    num_music=1
                )
                music_selection_time = time.time() - music_selection_start
                retrieval_timings["背景音乐选择"] = music_selection_time
                logger.info(f"背景音乐选择完成，耗时: {music_selection_time:.2f}s")
                
                if selected_music and len(selected_music) > 0:
                    background_music_path = selected_music[0]
                    logger.info(f"✓ 自动选择背景音乐: {os.path.basename(background_music_path)}")
                    # 验证文件是否存在
                    if not os.path.exists(background_music_path):
                        logger.warning(f"⚠️ 背景音乐文件不存在: {background_music_path}")
                        background_music_path = None
                else:
                    logger.warning("⚠️ 未找到合适的背景音乐，将不使用背景音乐")
                    background_music_path = None
            except Exception as e:
                logger.warning(f"⚠️ 自动选择背景音乐失败: {str(e)}，将不使用背景音乐")
                import traceback
                logger.debug(f"错误详情: {traceback.format_exc()}")
                background_music_path = None
                if "music_selection_start" in locals():
                    music_selection_time = time.time() - music_selection_start
                    retrieval_timings["背景音乐选择"] = music_selection_time
            
            # 生成播客
            logger.info("开始生成播客音频...")
            dialogues = processor.parse_role_text(text_content)
            dialogue_count = len(dialogues)
            
            # 计算对话总字数
            total_chars = sum(len(content) for _, content in dialogues)
            avg_chars_per_dialogue = total_chars / dialogue_count if dialogue_count > 0 else 0
            
            # 统计角色信息
            unique_roles = set(role for role, _ in dialogues)
            role_count = len(unique_roles)
            
            # 输出脚本信息
            logger.info("=" * 60)
            logger.info("【输出脚本信息】")
            logger.info(f"  - 对话段数: {dialogue_count} 段")
            logger.info(f"  - 对话总字数: {total_chars} 字")
            logger.info(f"  - 平均每段字数: {avg_chars_per_dialogue:.1f} 字")
            logger.info(f"  - 角色数量: {role_count} 个")
            logger.info(f"  - 角色列表: {', '.join(sorted(unique_roles))}")
            logger.info("=" * 60)
            
            # 输出完整脚本内容到控制台
            logger.info("=" * 60)
            logger.info("【完整脚本内容】")
            logger.info(text_content)
            logger.info("=" * 60)
            
            # 中间过程-检索信息
            logger.info("=" * 60)
            logger.info("【中间过程-检索信息】")
            for key, timing in retrieval_timings.items():
                logger.info(f"  - {key}: {timing:.2f}s")
            retrieval_total = sum(retrieval_timings.values())
            logger.info(f"  - 检索总耗时: {retrieval_total:.2f}s")
            logger.info("=" * 60)
            
            # 性能分析
            logger.info("=" * 60)
            logger.info("性能分析：")
            logger.info(f"  - 使用引擎: {_LLM_ENGINE} (HF引擎)")
            logger.info(f"  - FP16 Flow: {SOULX_PODCAST_FP16_FLOW}")
            
            # 估算耗时（HF引擎：每段约2-5秒）
            estimated_time_per_segment = 3.0 if avg_chars_per_dialogue < 40 else 4.0
            
            estimated_total_time = dialogue_count * estimated_time_per_segment
            logger.info(f"  - 预计每段耗时: {estimated_time_per_segment:.1f} 秒")
            logger.info(f"  - 预计总耗时: {estimated_total_time:.0f} 秒（{estimated_total_time/60:.1f} 分钟）")
            logger.info("=" * 60)
            
            logger.info("提示：SoulX-Podcast需要逐段生成音频，这是最耗时的步骤")
            logger.info("     每段对话需要经过：LLM生成 -> Flow生成 -> HiFi-GAN生成")
            _update_progress(request.job_id, "generating", 25, "正在生成语音与合成音频（这可能需要几分钟，请耐心等待）")
            generation_start = time.time()
            output_path = gen.generate_from_text(
                text=text_content,
                role_voices=role_voices,
                silence_interval=request.silence_interval,
                intro_music=intro_music_path,
                outro_music=outro_music_path,
                background_music=background_music_path,
                background_volume=request.background_volume,
                background_mode="single",  # 单个背景音乐，使用single模式
                verbose=True
            )
            generation_time = time.time() - generation_start
            logger.info("=" * 60)
            logger.info("生成完成！性能统计：")
            logger.info("【必须】生成时延统计（单位：s）：")
            logger.info(f"  - 总耗时: {generation_time:.2f}s（{generation_time/60:.2f} 分钟）")
            if dialogue_count > 0:
                avg_time_per_segment = generation_time / dialogue_count
                logger.info(f"  - 平均时延: {avg_time_per_segment:.2f}s/段")
                logger.info(f"  - 对话段数: {dialogue_count} 段")
                logger.info(f"  - 每段平均字数: {avg_chars_per_dialogue:.1f} 字")
                logger.info(f"  - 生成速度: {avg_chars_per_dialogue/avg_time_per_segment:.1f} 字/秒")
                
                # 性能评估（HF引擎）
                if avg_time_per_segment < 3.0:
                    logger.info("  ✓ 性能良好（HF引擎）")
                else:
                    logger.info("  性能一般，可能的原因：")
                    logger.info("     - GPU性能不足")
                    logger.info("     - 对话文本过长")
            
            # 汇总所有耗时
            logger.info("=" * 60)
            logger.info("【总耗时汇总】")
            logger.info(f"  - 检索耗时: {retrieval_total:.2f}s")
            logger.info(f"  - 生成耗时: {generation_time:.2f}s")
            total_time = retrieval_total + generation_time
            logger.info(f"  - 总耗时: {total_time:.2f}s（{total_time/60:.2f} 分钟）")
            logger.info("=" * 60)
            _update_progress(request.job_id, "saving", 85, "保存音频文件")
            # 尝试启动 AGC 上传任务
            agc_result = None
            try:
                # 配置来源：优先环境变量，其次仓库中的 agc-apiclient-*.json
                agc_storage_url = os.getenv('AGC_STORAGE_URL')
                agc_bucket = os.getenv('AGC_BUCKET')
                agc_domain = os.getenv('AGC_DOMAIN', 'connect-api.cloud.huawei.com')
                agc_client_id = os.getenv('AGC_CLIENT_ID')
                agc_client_secret = os.getenv('AGC_CLIENT_SECRET')
                agc_product_id = os.getenv('AGC_PRODUCT_ID')

                # 如果没有显式提供 client_id/secret，尝试在仓库中查找 agc-apiclient-*.json
                if not agc_client_id or not agc_client_secret:
                    cfg_path = _find_agc_client_json()
                    if cfg_path:
                        cid, csecret, proj = _load_agc_credentials_from_file(cfg_path)
                        agc_client_id = agc_client_id or cid
                        agc_client_secret = agc_client_secret or csecret
                        agc_product_id = agc_product_id or proj

                if agc_storage_url and agc_bucket:
                    # 使用正斜杠构建云存储路径，避免 Windows 反斜杠问题
                    object_name = f"outputs/podcasts/{os.path.basename(output_path)}"
                    try:
                        if request.wait_for_upload:
                            logger.info("请求要求等待上传完成，开始同步上传...")
                            _update_progress(request.job_id, "uploading", 90, "正在上传到云存储（同步）")
                            # 计算超时时间：如果为0则根据文件大小自动计算，否则使用指定值
                            actual_timeout = calculate_upload_timeout(output_path, request.upload_timeout) if request.upload_timeout == 0 else request.upload_timeout
                            file_size_mb = os.path.getsize(output_path) / (1024 * 1024) if os.path.exists(output_path) else 0
                            logger.info(f"文件大小: {file_size_mb:.2f}MB, 使用超时时间: {actual_timeout}秒")
                            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                                future = executor.submit(agc_upload_client,
                                                          output_path=output_path,
                                                          storage_url=agc_storage_url,
                                                          bucket=agc_bucket,
                                                          product_id=agc_product_id,
                                                          domain=agc_domain,
                                                          client_id=agc_client_id,
                                                          client_secret=agc_client_secret)
                                try:
                                    res = future.result(timeout=actual_timeout)
                                    agc_result = {
                                        'status': 'uploaded',
                                        'bucket': agc_bucket,
                                        'object': object_name,
                                        'http_status': res.get('http_status'),
                                        'response_text': res.get('response_text'),
                                        'url': f"{agc_storage_url.rstrip('/')}/{agc_bucket}/{object_name}"
                                    }
                                    logger.info(f"同步 AGC 上传完成: {agc_result}")
                                    # 更新进度，包含音频URL以便前端从云存储下载并播放
                                    audio_url = agc_result.get('url') if isinstance(agc_result, dict) else None
                                    _update_progress(request.job_id, "completed", 100, "生成完成，已上传到云存储", done=True, audio_url=audio_url)
                                    # 同步上传成功，不再启动后台上传任务
                                except concurrent.futures.TimeoutError:
                                    logger.warning(f"同步上传超时（{actual_timeout}秒），文件大小: {file_size_mb:.2f}MB，已改为后台继续上传")
                                    background_tasks.add_task(do_agc_upload, output_path, agc_storage_url, agc_bucket,
                                                              agc_product_id, agc_domain, agc_client_id, agc_client_secret)
                                    agc_result = {
                                        'status': 'timeout_and_background',
                                        'bucket': agc_bucket,
                                        'object': object_name,
                                        'url': f"{agc_storage_url.rstrip('/')}/{agc_bucket}/{object_name}",
                                        'message': f'上传超时，已在后台继续上传（文件大小: {file_size_mb:.2f}MB）'
                                    }
                                    # 更新进度，包含音频URL（即使后台上传，也先返回URL以便前端下载）
                                    audio_url = agc_result.get('url') if isinstance(agc_result, dict) else None
                                    _update_progress(request.job_id, "uploading", 95, "生成完成，正在后台上传到云存储", done=True, audio_url=audio_url)
                                except Exception as e:
                                    logger.exception(f"同步上传失败: {e}")
                                    agc_result = {'status': 'failed', 'reason': str(e)}
                                    _update_progress(request.job_id, "upload_failed", 95, f"上传失败: {e}", done=True, error=str(e))
                        else:
                            # 后台异步上传（默认）
                            background_tasks.add_task(do_agc_upload, output_path, agc_storage_url, agc_bucket,
                                                      agc_product_id, agc_domain, agc_client_id, agc_client_secret)
                            logger.info("已在后台启动 AGC 上传任务")
                            agc_result = {
                                'status': 'started',
                                'bucket': agc_bucket,
                                'object': object_name,
                                'url': f"{agc_storage_url.rstrip('/')}/{agc_bucket}/{object_name}"
                            }
                            # 更新进度，包含音频URL（即使后台上传，也先返回URL以便前端从云存储下载）
                            audio_url = agc_result.get('url') if isinstance(agc_result, dict) else None
                            _update_progress(request.job_id, "uploading", 95, "生成完成，已开始后台上传到云存储", done=True, audio_url=audio_url)
                    except Exception as e:
                        logger.warning(f"准备 AGC 上传任务时出错（不影响主流程）: {str(e)}")
                else:
                    logger.debug("未检测到 AGC 存储配置，跳过后台上传")
                    _update_progress(request.job_id, "completed", 100, "生成完成", done=True)
            except Exception as e:
                logger.warning(f"准备 AGC 上传任务时出错（不影响主流程）: {str(e)}")
            
            # 编码输出音频
            logger.info("编码输出音频文件...")
            audio_base64 = encode_file_to_base64(output_path)
            file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
            total_time = time.time() - start_time
            logger.info(f"多角色播客生成成功，总耗时: {total_time:.2f}s，输出文件大小: {file_size:.2f} MB")
            
            data = {
                    "audio_base64": audio_base64,
                "audio_path": output_path,  # 默认使用本地路径
                    "file_size_mb": round(file_size, 2),
                "script": text_content,
                    "roles": list(roles)
                }
            if agc_result:
                data['agc_upload_status'] = agc_result
                # 如果上传成功，使用云存储路径作为 audio_path
                if isinstance(agc_result, dict):
                    if agc_result.get('object'):
                        # 使用云存储路径（object_name）作为 audio_path
                        data['audio_path'] = agc_result['object']
                    # 便于前端直接播放的直链
                    if agc_result.get('url'):
                        data['audio_url'] = agc_result['url']

            return ApiResponse(success=True, message="播客生成成功", data=data)
        finally:
            # 清理临时文件
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except:
                    pass
                    
    except HTTPException:
        _update_progress(getattr(request, 'job_id', None), "failed", 100, "请求参数错误", done=True, error="HTTPException")
        raise
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        total_time = time.time() - start_time
        logger.error(f"多角色播客生成失败，耗时: {total_time:.2f}s，错误: {str(e)}")
        logger.error(f"错误详情:\n{error_detail}")
        _update_progress(getattr(request, 'job_id', None), "failed", 100, f"生成失败: {str(e)}", done=True, error=str(e))
        return ApiResponse(
            success=False,
            message="播客生成失败",
            error=str(e),
            data={"traceback": error_detail}
        )


@app.post("/api/v1/podcast/character", response_model=ApiResponse)
async def generate_character_podcast(request: CharacterRequest, background_tasks: BackgroundTasks):
    """
    生成自定义角色播客（子题目2）
    
    - **characters**: 角色列表（至少2个，最多4个），每个角色必须提供voice_url（云存储URL）
    - **text**: 文本素材（必需）
    - **topic**: 播客主题（可选，主要用于背景音乐选择）
    - **silence_interval**: 角色切换静音间隔（毫秒）
    
    注意：本接口仅支持云存储URL，不再支持base64编码的音频文件
    """
    # 立即创建初始进度，确保前端轮询时能立即获取到状态
    _update_progress(request.job_id, "queued", 1, "任务已提交，准备开始处理")
    start_time = time.time()
    
    # 检查输入：必须提供文本素材
    has_text = request.text and request.text.strip()
    
    if not has_text:
        raise HTTPException(status_code=400, detail="必须提供文本素材（text字段）")
    
    logger.info(f"开始生成自定义角色播客: 角色数量={len(request.characters)}, 文本素材长度={len(request.text)}, 主题={request.topic}, 使用云存储")
    
    try:
        gen = get_generator()
        processor = TextProcessor()
        api_client = get_client()
        
        # 从云存储URL下载音频文件并构建角色信息
        temp_files = []
        character_descriptions = {}
        role_voices = {}
        
        try:
            _update_progress(request.job_id, "downloading_voices", 5, "正在下载角色音色文件")
            
            # 使用并发下载以提高速度
            import concurrent.futures
            import time as time_module
            
            def download_character_voice(char):
                voice_download_start = time_module.time()
                logger.info(f"开始下载角色 '{char.name}' 的音频文件: {char.voice_url}")
                try:
                    temp_file = download_audio_from_url(char.voice_url)
                    voice_download_time = time_module.time() - voice_download_start
                    logger.info(f"角色 '{char.name}' 音频文件下载完成，耗时: {voice_download_time:.2f}s")
                    return char, temp_file, voice_download_time
                except Exception as e:
                    logger.error(f"角色 '{char.name}' 音频文件下载失败: {str(e)}")
                    raise
            
            # 并发下载所有角色的音色文件
            logger.info(f"使用并发下载 {len(request.characters)} 个角色音色文件...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(5, len(request.characters))) as executor:
                future_to_char = {executor.submit(download_character_voice, char): char.name for char in request.characters}
                for future in concurrent.futures.as_completed(future_to_char):
                    char_name = future_to_char[future]
                    try:
                        char, temp_file, voice_download_time = future.result()
                        temp_files.append(temp_file)
                        role_voices[char.name] = temp_file
                        
                        character_descriptions[char.name] = {
                            "identity": char.identity or "",
                            "personality": char.personality or "",
                            "catchphrase": char.catchphrase or "",
                            "speaking_style": char.speaking_style or "",
                            "relationship": char.relationship or ""
                        }
                    except Exception as e:
                        logger.error(f"角色 '{char_name}' 下载失败: {str(e)}")
                        raise
            
            # 获取文本素材
            text_material = request.text
            logger.info(f"使用直接输入的文本素材: {len(text_material)} 字符")
            
            # 生成对话文本
            logger.info("调用混元大模型生成高度拟人化角色互动对话...")
            prompt = processor.build_character_prompt(
                character_descriptions,
                text_material=text_material,
                topic=request.topic if not text_material else None  # 如果有文本素材，不使用主题
            )
            
            text_generation_start = time.time()
            generated_text = api_client.generate_text(
                prompt=prompt,
                temperature=0.8,
                max_tokens=3000  # 增加到3000以支持更长的对话（5-6分钟播客）
            )
            text_generation_time = time.time() - text_generation_start
            logger.info(f"对话文本生成完成，耗时: {text_generation_time:.2f}s，文本长度: {len(generated_text)}")
            
            cleaned_text = processor.clean_text(generated_text)
            
            # 输出完整脚本内容到控制台
            logger.info("=" * 60)
            logger.info("【完整脚本内容】")
            logger.info(cleaned_text)
            logger.info("=" * 60)
            
            # 自动选择背景音乐（在AI生成对话之后，使用完整的文本内容）
            background_music_path = None
            try:
                _update_progress(request.job_id, "selecting_music", 22, "正在选择背景音乐")
                logger.info("开始自动选择背景音乐...")
                music_selection_start = time.time()
                music_selector = MusicSelector(use_cloud_storage=False)
                selected_music = music_selector.select_music_by_ai(
                    text=cleaned_text,  # 使用完整的文本内容（包括AI生成的对话）
                    podcast_name=None,
                    topic=request.topic,
                    scene_types=None,
                    category=request.category,
                    num_music=1
                )
                music_selection_time = time.time() - music_selection_start
                logger.info(f"背景音乐选择完成，耗时: {music_selection_time:.2f}s")
                
                if selected_music and len(selected_music) > 0:
                    background_music_path = selected_music[0]
                    logger.info(f"✓ 自动选择背景音乐: {os.path.basename(background_music_path)}")
                    # 验证文件是否存在
                    if not os.path.exists(background_music_path):
                        logger.warning(f"⚠️ 背景音乐文件不存在: {background_music_path}")
                        background_music_path = None
                else:
                    logger.warning("⚠️ 未找到合适的背景音乐，将不使用背景音乐")
                    background_music_path = None
            except Exception as e:
                logger.warning(f"⚠️ 自动选择背景音乐失败: {str(e)}，将不使用背景音乐")
                import traceback
                logger.debug(f"错误详情: {traceback.format_exc()}")
                background_music_path = None
            
            # 生成播客
            logger.info("开始生成播客音频...")
            generation_start = time.time()
            output_path = gen.generate_from_text(
                text=cleaned_text,
                role_voices=role_voices,
                silence_interval=request.silence_interval,
                background_music=background_music_path,
                background_volume=request.background_volume,
                background_mode="single",  # 单个背景音乐，使用single模式
                verbose=True
            )
            generation_time = time.time() - generation_start
            logger.info(f"播客音频生成完成，耗时: {generation_time:.2f}s")
            
            # 编码输出音频
            logger.info("编码输出音频文件...")
            audio_base64 = encode_file_to_base64(output_path)
            file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
            total_time = time.time() - start_time
            logger.info(f"自定义角色播客生成成功，总耗时: {total_time:.2f}s，输出文件大小: {file_size:.2f} MB")
            
            # 尝试启动后台 AGC 上传任务（不阻塞主请求）
            agc_result = None
            try:
                agc_storage_url = os.getenv('AGC_STORAGE_URL')
                agc_bucket = os.getenv('AGC_BUCKET')
                agc_domain = os.getenv('AGC_DOMAIN', 'connect-api.cloud.huawei.com')
                agc_client_id = os.getenv('AGC_CLIENT_ID')
                agc_client_secret = os.getenv('AGC_CLIENT_SECRET')
                agc_product_id = os.getenv('AGC_PRODUCT_ID')

                if not agc_client_id or not agc_client_secret:
                    cfg_path = _find_agc_client_json()
                    if cfg_path:
                        cid, csecret, proj = _load_agc_credentials_from_file(cfg_path)
                        agc_client_id = agc_client_id or cid
                        agc_client_secret = agc_client_secret or csecret
                        agc_product_id = agc_product_id or proj

                if agc_storage_url and agc_bucket:
                    # 使用正斜杠构建云存储路径，避免 Windows 反斜杠问题
                    object_name = f"outputs/podcasts/{os.path.basename(output_path)}"
                    try:
                        if request.wait_for_upload:
                            # 同步上传，等待完成（阻塞，超时由 upload_timeout 控制）
                            logger.info("请求要求等待上传完成，开始同步上传...")
                            # 计算超时时间：如果为0则根据文件大小自动计算，否则使用指定值
                            actual_timeout = calculate_upload_timeout(output_path, request.upload_timeout) if request.upload_timeout == 0 else request.upload_timeout
                            file_size_mb = os.path.getsize(output_path) / (1024 * 1024) if os.path.exists(output_path) else 0
                            logger.info(f"文件大小: {file_size_mb:.2f}MB, 使用超时时间: {actual_timeout}秒")
                            # 通过线程执行并等待指定超时，超时后改为后台继续上传
                            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                                future = executor.submit(agc_upload_client,
                                                          output_path=output_path,
                                                          storage_url=agc_storage_url,
                                                          bucket=agc_bucket,
                                                          product_id=agc_product_id,
                                                          domain=agc_domain,
                                                          client_id=agc_client_id,
                                                          client_secret=agc_client_secret)
                                try:
                                    res = future.result(timeout=actual_timeout)
                                    agc_result = {
                                        'status': 'uploaded',
                                        'bucket': agc_bucket,
                                        'object': object_name,
                                        'http_status': res.get('http_status'),
                                        'response_text': res.get('response_text'),
                                        'url': f"{agc_storage_url.rstrip('/')}/{agc_bucket}/{object_name}"
                                    }
                                    logger.info(f"同步 AGC 上传完成: {agc_result}")
                                except concurrent.futures.TimeoutError:
                                    logger.warning(f"同步上传超时（{actual_timeout}秒），文件大小: {file_size_mb:.2f}MB，已改为后台继续上传")
                                    # 改为后台继续上传
                                    background_tasks.add_task(do_agc_upload, output_path, agc_storage_url, agc_bucket,
                                                              agc_product_id, agc_domain, agc_client_id, agc_client_secret)
                                    agc_result = {
                                        'status': 'timeout_and_background',
                                        'bucket': agc_bucket,
                                        'object': object_name,
                                        'url': f"{agc_storage_url.rstrip('/')}/{agc_bucket}/{object_name}",
                                        'message': f'上传超时，已在后台继续上传（文件大小: {file_size_mb:.2f}MB）'
                                    }
                                except Exception as e:
                                    logger.exception(f"同步上传失败: {e}")
                                    agc_result = {'status': 'failed', 'reason': str(e)}
                        else:
                            # 后台异步上传（默认）
                            background_tasks.add_task(do_agc_upload, output_path, agc_storage_url, agc_bucket,
                                                      agc_product_id, agc_domain, agc_client_id, agc_client_secret)
                            logger.info("已在后台启动 AGC 上传任务")
                            agc_result = {
                                'status': 'started',
                                'bucket': agc_bucket,
                                'object': object_name,
                                'url': f"{agc_storage_url.rstrip('/')}/{agc_bucket}/{object_name}"
                            }
                    except Exception as e:
                        logger.warning(f"准备 AGC 上传任务时出错（不影响主流程）: {str(e)}")
                else:
                    logger.debug("未检测到 AGC 存储配置，跳过后台上传")
            except Exception as e:
                logger.warning(f"准备 AGC 上传任务时出错（不影响主流程）: {str(e)}")

            data = {
                    "audio_base64": audio_base64,
                "audio_path": output_path,  # 默认使用本地路径
                    "file_size_mb": round(file_size, 2),
                    "script": cleaned_text,
                    "characters": [char.name for char in request.characters]
                }
            if agc_result:
                data['agc_upload_status'] = agc_result
                # 如果上传成功，使用云存储路径作为 audio_path
                if isinstance(agc_result, dict) and agc_result.get('object'):
                    data['audio_path'] = agc_result['object']
                # 便于前端直接播放的直链
                if isinstance(agc_result, dict) and agc_result.get('url'):
                    data['audio_url'] = agc_result['url']

            return ApiResponse(success=True, message="播客生成成功", data=data)
        finally:
            # 清理临时文件
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except:
                    pass
                    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        total_time = time.time() - start_time
        logger.error(f"自定义角色播客生成失败，耗时: {total_time:.2f}s，错误: {str(e)}")
        logger.error(f"错误详情:\n{error_detail}")
        return ApiResponse(
            success=False,
            message="播客生成失败",
            error=str(e),
            data={"traceback": error_detail}
        )


@app.post("/api/v1/podcast/deep", response_model=ApiResponse)
async def generate_deep_podcast(request: DeepPodcastRequest, background_tasks: BackgroundTasks):
    """
    生成主题深度播客（子题目3）
    
    - **topic**: 播客主题
    - **role_voice_urls**: 角色音色映射，键为角色名，值为云存储下载URL（必需）
    - **num_characters**: 角色数量（1-3个）
    - **depth_level**: 深度级别（深度/中等/浅层）
    - **silence_interval**: 角色切换静音间隔（毫秒）
    
    注意：本接口仅支持云存储URL，不再支持base64编码的音频文件
    """
    # 立即创建初始进度，确保前端轮询时能立即获取到状态
    _update_progress(request.job_id, "queued", 1, "任务已提交，准备开始处理")
    start_time = time.time()
    
    # 验证云存储URL
    if not request.role_voice_urls or len(request.role_voice_urls) == 0:
        raise HTTPException(status_code=400, detail="至少需要提供一个角色的音色文件URL（role_voice_urls）")
    
    logger.info(f"开始生成主题深度播客: 主题={request.topic}, 角色数量={request.num_characters}, 深度级别={request.depth_level}, 使用云存储")
    
    try:
        gen = get_generator()
        processor = TextProcessor()
        api_client = get_client()
        
        # 从云存储URL下载音频文件
        temp_files = []
        role_voices = {}
        
        try:
            _update_progress(request.job_id, "downloading_voices", 5, "正在下载角色音色文件")
            
            # 使用并发下载以提高速度
            import concurrent.futures
            import time as time_module
            
            role_names = ["角色A", "角色B", "角色C"][:request.num_characters]
            
            # 验证所有角色都有音色URL
            for role_name in role_names:
                if role_name not in request.role_voice_urls:
                    raise HTTPException(status_code=400, detail=f"缺少角色 '{role_name}' 的音色文件URL")
            
            def download_role_voice(role_name):
                voice_url = request.role_voice_urls[role_name]
                voice_download_start = time_module.time()
                logger.info(f"开始下载角色 '{role_name}' 的音频文件: {voice_url}")
                try:
                    temp_file = download_audio_from_url(voice_url)
                    voice_download_time = time_module.time() - voice_download_start
                    logger.info(f"角色 '{role_name}' 音频文件下载完成，耗时: {voice_download_time:.2f}s")
                    return role_name, temp_file, voice_download_time
                except Exception as e:
                    logger.error(f"角色 '{role_name}' 音频文件下载失败: {str(e)}")
                    raise
            
            # 并发下载所有角色的音色文件
            logger.info(f"使用并发下载 {len(role_names)} 个角色音色文件...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(5, len(role_names))) as executor:
                future_to_role = {executor.submit(download_role_voice, role_name): role_name for role_name in role_names}
                for future in concurrent.futures.as_completed(future_to_role):
                    role_name = future_to_role[future]
                    try:
                        role_name_result, temp_file, voice_download_time = future.result()
                        temp_files.append(temp_file)
                        role_voices[role_name_result] = temp_file
                    except Exception as e:
                        logger.error(f"角色 '{role_name}' 下载失败: {str(e)}")
                        raise
            
            # 生成对话文本
            logger.info("调用混元大模型生成深度对话文本...")
            prompt = processor.build_deep_podcast_prompt(
                request.topic,
                request.depth_level,
                request.num_characters
            )
            
            text_generation_start = time.time()
            generated_text = api_client.generate_text(
                prompt=prompt,
                temperature=0.7,
                max_tokens=3000  # 增加到3000以支持更长的对话（5-6分钟播客）
            )
            text_generation_time = time.time() - text_generation_start
            logger.info(f"对话文本生成完成，耗时: {text_generation_time:.2f}s，文本长度: {len(generated_text)}")
            
            cleaned_text = processor.clean_text(generated_text)
            
            # 输出完整脚本内容到控制台
            logger.info("=" * 60)
            logger.info("【完整脚本内容】")
            logger.info(cleaned_text)
            logger.info("=" * 60)
            
            # 自动选择背景音乐（在AI生成对话之后，使用完整的文本内容）
            background_music_path = None
            try:
                _update_progress(request.job_id, "selecting_music", 22, "正在选择背景音乐")
                logger.info("开始自动选择背景音乐...")
                music_selection_start = time.time()
                music_selector = MusicSelector(use_cloud_storage=False)
                selected_music = music_selector.select_music_by_ai(
                    text=cleaned_text,  # 使用完整的文本内容（包括AI生成的对话）
                    podcast_name=None,
                    topic=request.topic,
                    scene_types=None,
                    category=request.category,
                    num_music=1
                )
                music_selection_time = time.time() - music_selection_start
                logger.info(f"背景音乐选择完成，耗时: {music_selection_time:.2f}s")
                
                if selected_music and len(selected_music) > 0:
                    background_music_path = selected_music[0]
                    logger.info(f"✓ 自动选择背景音乐: {os.path.basename(background_music_path)}")
                    # 验证文件是否存在
                    if not os.path.exists(background_music_path):
                        logger.warning(f" 背景音乐文件不存在: {background_music_path}")
                        background_music_path = None
                else:
                    logger.warning(" 未找到合适的背景音乐，将不使用背景音乐")
                    background_music_path = None
            except Exception as e:
                logger.warning(f" 自动选择背景音乐失败: {str(e)}，将不使用背景音乐")
                import traceback
                logger.debug(f"错误详情: {traceback.format_exc()}")
                background_music_path = None
            
            # 生成播客
            logger.info("开始生成播客音频...")
            generation_start = time.time()
            output_path = gen.generate_from_text(
                text=cleaned_text,
                role_voices=role_voices,
                silence_interval=request.silence_interval,
                background_music=background_music_path,
                background_volume=request.background_volume,
                background_mode="single",  # 单个背景音乐，使用single模式
                verbose=True
            )
            generation_time = time.time() - generation_start
            logger.info(f"播客音频生成完成，耗时: {generation_time:.2f}s")
            
            # 编码输出音频
            logger.info("编码输出音频文件...")
            audio_base64 = encode_file_to_base64(output_path)
            file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
            total_time = time.time() - start_time
            logger.info(f"主题深度播客生成成功，总耗时: {total_time:.2f}s，输出文件大小: {file_size:.2f} MB")
            
            # 尝试启动后台 AGC 上传任务（不阻塞主请求）
            agc_result = None
            try:
                agc_storage_url = os.getenv('AGC_STORAGE_URL')
                agc_bucket = os.getenv('AGC_BUCKET')
                agc_domain = os.getenv('AGC_DOMAIN', 'connect-api.cloud.huawei.com')
                agc_client_id = os.getenv('AGC_CLIENT_ID')
                agc_client_secret = os.getenv('AGC_CLIENT_SECRET')
                agc_product_id = os.getenv('AGC_PRODUCT_ID')

                if not agc_client_id or not agc_client_secret:
                    cfg_path = _find_agc_client_json()
                    if cfg_path:
                        cid, csecret, proj = _load_agc_credentials_from_file(cfg_path)
                        agc_client_id = agc_client_id or cid
                        agc_client_secret = agc_client_secret or csecret
                        agc_product_id = agc_product_id or proj

                if agc_storage_url and agc_bucket:
                    # 使用正斜杠构建云存储路径，避免 Windows 反斜杠问题
                    object_name = f"outputs/podcasts/{os.path.basename(output_path)}"
                    try:
                        if request.wait_for_upload:
                            # 同步上传，等待完成（阻塞，超时由 upload_timeout 控制）
                            logger.info("请求要求等待上传完成，开始同步上传...")
                            # 计算超时时间：如果为0则根据文件大小自动计算，否则使用指定值
                            actual_timeout = calculate_upload_timeout(output_path, request.upload_timeout) if request.upload_timeout == 0 else request.upload_timeout
                            file_size_mb = os.path.getsize(output_path) / (1024 * 1024) if os.path.exists(output_path) else 0
                            logger.info(f"文件大小: {file_size_mb:.2f}MB, 使用超时时间: {actual_timeout}秒")
                            # 通过线程执行并等待指定超时，超时后改为后台继续上传
                            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                                future = executor.submit(agc_upload_client,
                                                          output_path=output_path,
                                                          storage_url=agc_storage_url,
                                                          bucket=agc_bucket,
                                                          product_id=agc_product_id,
                                                          domain=agc_domain,
                                                          client_id=agc_client_id,
                                                          client_secret=agc_client_secret)
                                try:
                                    res = future.result(timeout=actual_timeout)
                                    agc_result = {
                                        'status': 'uploaded',
                                        'bucket': agc_bucket,
                                        'object': object_name,
                                        'http_status': res.get('http_status'),
                                        'response_text': res.get('response_text'),
                                        'url': f"{agc_storage_url.rstrip('/')}/{agc_bucket}/{object_name}"
                                    }
                                    logger.info(f"同步 AGC 上传完成: {agc_result}")
                                except concurrent.futures.TimeoutError:
                                    logger.warning(f"同步上传超时（{actual_timeout}秒），文件大小: {file_size_mb:.2f}MB，已改为后台继续上传")
                                    # 改为后台继续上传
                                    background_tasks.add_task(do_agc_upload, output_path, agc_storage_url, agc_bucket,
                                                              agc_product_id, agc_domain, agc_client_id, agc_client_secret)
                                    agc_result = {
                                        'status': 'timeout_and_background',
                                        'bucket': agc_bucket,
                                        'object': object_name,
                                        'url': f"{agc_storage_url.rstrip('/')}/{agc_bucket}/{object_name}",
                                        'message': f'上传超时，已在后台继续上传（文件大小: {file_size_mb:.2f}MB）'
                                    }
                                except Exception as e:
                                    logger.exception(f"同步上传失败: {e}")
                                    agc_result = {'status': 'failed', 'reason': str(e)}
                        else:
                            # 后台异步上传（默认）
                            background_tasks.add_task(do_agc_upload, output_path, agc_storage_url, agc_bucket,
                                                      agc_product_id, agc_domain, agc_client_id, agc_client_secret)
                            logger.info("已在后台启动 AGC 上传任务")
                            agc_result = {
                                'status': 'started',
                                'bucket': agc_bucket,
                                'object': object_name,
                                'url': f"{agc_storage_url.rstrip('/')}/{agc_bucket}/{object_name}"
                            }
                    except Exception as e:
                        logger.warning(f"准备 AGC 上传任务时出错（不影响主流程）: {str(e)}")
                else:
                    logger.debug("未检测到 AGC 存储配置，跳过后台上传")
            except Exception as e:
                logger.warning(f"准备 AGC 上传任务时出错（不影响主流程）: {str(e)}")

            data = {
                    "audio_base64": audio_base64,
                "audio_path": output_path,  # 默认使用本地路径
                    "file_size_mb": round(file_size, 2),
                    "script": cleaned_text,
                    "topic": request.topic,
                    "depth_level": request.depth_level
                }
            if agc_result:
                data['agc_upload_status'] = agc_result
                # 如果上传成功，使用云存储路径作为 audio_path
                if isinstance(agc_result, dict) and agc_result.get('object'):
                    data['audio_path'] = agc_result['object']
                # 便于前端直接播放的直链
                if isinstance(agc_result, dict) and agc_result.get('url'):
                    data['audio_url'] = agc_result['url']

            return ApiResponse(success=True, message="播客生成成功", data=data)
        finally:
            # 清理临时文件
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except:
                    pass
                    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        total_time = time.time() - start_time
        logger.error(f"主题深度播客生成失败，耗时: {total_time:.2f}s，错误: {str(e)}")
        logger.error(f"错误详情:\n{error_detail}")
        return ApiResponse(
            success=False,
            message="播客生成失败",
            error=str(e),
            data={"traceback": error_detail}
        )


class AnalyzeTextRequest(BaseModel):
    """文本分析请求"""
    text: str = Field(..., description="要分析的文本素材")


@app.post("/api/v1/podcast/analyze", response_model=ApiResponse)
async def analyze_text_for_podcast(request: AnalyzeTextRequest):
    """
    分析文本素材，自动推断播客信息
    
    - **text**: 文本素材
    
    返回：
    - **podcast_name**: 播客名称
    - **topic**: 本期主题
    - **characters**: 角色设定列表
    - **scene_types**: 互动场景类型列表
    """
    try:
        processor = TextProcessor()
        api_client = get_client()
        
        logger.info(f"开始分析文本素材: 文本长度={len(request.text)}")
        result = processor.analyze_text_for_podcast(request.text, api_client)
        logger.info("文本分析完成")
        
        return ApiResponse(
            success=True,
            message="分析成功",
            data=result
        )
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"文本分析失败: {str(e)}")
        logger.error(f"错误详情:\n{error_detail}")
        return ApiResponse(
            success=False,
            message="分析失败",
            error=str(e),
            data={"traceback": error_detail}
        )


@app.get("/api/v1/podcast/file/{file_id}")
async def get_podcast_file(file_id: str):
    """
    获取生成的播客文件
    
    - **file_id**: 文件名（相对于输出目录）
    """
    try:
        file_path = os.path.join(OUTPUT_DIR, file_id)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        return FileResponse(
            file_path,
            media_type="audio/wav",
            filename=file_id
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/podcast/progress/{job_id}")
async def get_progress(job_id: str):
    """
    获取任务进度（HTTP轮询方式）
    
    注意：
    - HarmonyOS客户端必须使用此端点进行轮询
    - Web客户端可以使用SSE端点：/api/v1/podcast/progress/{job_id}/stream 获得更好的实时性
    - 此端点的请求日志已被过滤，避免覆盖其他重要日志
    """
    try:
        return _get_progress(job_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/podcast/progress/{job_id}/stream")
async def stream_progress(job_id: str):
    """
    使用 Server-Sent Events (SSE) 实时推送任务进度
    前端通过 EventSource 连接此端点，无需轮询
    
    使用示例（JavaScript）：
    ```javascript
    const eventSource = new EventSource(`/api/v1/podcast/progress/${jobId}/stream`);
    eventSource.onmessage = (event) => {
        const progress = JSON.parse(event.data);
        console.log('进度更新:', progress);
        // 更新UI
    };
    eventSource.onerror = (error) => {
        console.error('SSE连接错误:', error);
        eventSource.close();
    };
    ```
    """
    async def event_generator():
        # 创建SSE队列
        queue = asyncio.Queue(maxsize=10)  # 设置队列大小，避免内存无限增长
        _PROGRESS_SSE_QUEUES[job_id] = queue
        
        last_heartbeat_time = time.time()
        heartbeat_interval = 25.0  # 25秒发送一次心跳（小于30秒超时）
        
        try:
            # 先发送当前进度（如果有）
            current_progress = _get_progress(job_id)
            if current_progress.get("phase") != "unknown":
                yield f"data: {json.dumps(current_progress, ensure_ascii=False)}\n\n"
                logger.info(f"SSE连接已建立，job_id={job_id}，已发送当前进度")
            
            # 持续监听进度更新
            while True:
                try:
                    # 等待进度更新，设置超时以定期发送心跳
                    wait_timeout = heartbeat_interval - (time.time() - last_heartbeat_time)
                    wait_timeout = max(1.0, min(wait_timeout, heartbeat_interval))  # 确保至少1秒，最多25秒
                    
                    progress_data = await asyncio.wait_for(queue.get(), timeout=wait_timeout)
                    yield f"data: {json.dumps(progress_data, ensure_ascii=False)}\n\n"
                    last_heartbeat_time = time.time()  # 更新心跳时间
                    
                    # 如果任务完成或失败，关闭连接
                    if progress_data.get("done", False):
                        logger.info(f"SSE任务完成，job_id={job_id}，关闭连接")
                        break
                except asyncio.TimeoutError:
                    # 定期发送心跳保持连接
                    current_time = time.time()
                    if current_time - last_heartbeat_time >= heartbeat_interval:
                        yield f": heartbeat {int(current_time)}\n\n"
                        last_heartbeat_time = current_time
                        logger.debug(f"SSE发送心跳，job_id={job_id}")
                    continue
        except asyncio.CancelledError:
            # 客户端断开连接
            logger.info(f"SSE客户端断开连接，job_id={job_id}")
            pass
        except Exception as e:
            logger.error(f"SSE事件生成器异常，job_id={job_id}，错误: {str(e)}")
        finally:
            # 清理SSE队列
            if job_id in _PROGRESS_SSE_QUEUES:
                del _PROGRESS_SSE_QUEUES[job_id]
                logger.info(f"SSE队列已清理，job_id={job_id}")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用nginx缓冲
        }
    )


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="混元AI播客生成API服务")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="API服务主机")
    parser.add_argument("--port", type=int, default=8000, help="API服务端口")
    args = parser.parse_args()
    
    print(f"🚀 启动混元AI播客生成API服务")
    print(f"📡 API地址: http://{args.host}:{args.port}")
    print(f"📚 API文档: http://{args.host}:{args.port}/docs")
    print(f"💡 健康检查: http://{args.host}:{args.port}/health")
    
    uvicorn.run(app, host=args.host, port=args.port)


