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
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
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
from .config import INDEXTTS_CONFIG_PATH, INDEXTTS_MODEL_DIR, OUTPUT_DIR
from .text_processor import TextProcessor
from .api_client import get_client


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============ 进度管理 ============
_PROGRESS_DIR = os.path.join(os.getcwd(), 'outputs', 'progress')
os.makedirs(_PROGRESS_DIR, exist_ok=True)
_PROGRESS_CACHE: Dict[str, Dict[str, Any]] = {}
_JOB_RESULT_DIR = os.path.join(os.getcwd(), 'outputs', 'jobs')
os.makedirs(_JOB_RESULT_DIR, exist_ok=True)

def _progress_path(job_id: str) -> str:
    return os.path.join(_PROGRESS_DIR, f"{job_id}.json")

def _update_progress(job_id: Optional[str], phase: str, percent: int, message: str, done: bool = False, error: Optional[str] = None):
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
    _PROGRESS_CACHE[job_id] = data
    try:
        with open(_progress_path(job_id), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass

def _get_progress(job_id: str) -> Dict[str, Any]:
    if job_id in _PROGRESS_CACHE:
        return _PROGRESS_CACHE[job_id]
    try:
        with open(_progress_path(job_id), 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"job_id": job_id, "phase": "unknown", "percent": 0, "message": "未开始或任务ID不存在", "done": False}

def _job_result_path(job_id: str) -> str:
    return os.path.join(_JOB_RESULT_DIR, f"{job_id}.json")

def _save_job_result(job_id: Optional[str], data: Dict[str, Any]) -> None:
    if not job_id:
        return
    try:
        with open(_job_result_path(job_id), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        logger.warning("保存任务结果失败", exc_info=True)

def _get_job_result(job_id: str) -> Optional[Dict[str, Any]]:
    try:
        with open(_job_result_path(job_id), 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None

# 文件大小限制（字节）
MAX_AUDIO_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_REQUEST_BODY_SIZE = 100 * 1024 * 1024  # 100MB

app = FastAPI(
    title="混元AI播客生成API",
    description="基于混元大模型和IndexTTS-2的智能播客音频生成API",
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
use_fp16 = os.getenv("USE_FP16", "false").lower() == "true"
use_cuda_kernel = os.getenv("USE_CUDA_KERNEL", "false").lower() == "true"
device = os.getenv("DEVICE", None)


def get_generator() -> PodcastGenerator:
    """获取或创建生成器实例"""
    global generator
    if generator is None:
        logger.info("初始化PodcastGenerator...")
        logger.info(f"GPU配置: use_fp16={use_fp16}, use_cuda_kernel={use_cuda_kernel}, device={device}")
        generator = PodcastGenerator(
            tts_config_path=INDEXTTS_CONFIG_PATH,
            tts_model_dir=INDEXTTS_MODEL_DIR,
            use_fp16=use_fp16,
            use_cuda_kernel=use_cuda_kernel,
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
    
    # 记录请求信息
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
                        has_text = body_json.get("text") and str(body_json.get("text")).strip()
                        has_text_file = body_json.get("text_file_url") and str(body_json.get("text_file_url")).strip()
                        has_voice_urls = body_json.get("role_voice_urls") and len(body_json.get("role_voice_urls", {})) > 0
                        has_voices = body_json.get("role_voices") and len(body_json.get("role_voices", {})) > 0
                        
                        if not has_text and not has_text_file:
                            logger.error("缺少必需字段: text 或 text_file_url 至少需要一个")
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
    logger.info(f"请求完成: {method} {path} - 状态码: {response.status_code} - 耗时: {process_time:.2f}s")
    
    return response


# ============ 请求模型 ============

class MultiRoleRequest(BaseModel):
    """多角色互动播客请求"""
    text: Optional[str] = Field(None, description="播客文本（支持角色标记或普通文本，如果使用text_file_url，此字段可为空）")
    text_file_url: Optional[str] = Field(None, description="文本文件云存储URL（.txt或Word文件，如果提供，优先使用）")
    role_voice_urls: Optional[Dict[str, str]] = Field(None, description="角色音色映射，云存储URL（如果使用云存储，键为角色名，值为云存储下载URL）")
    role_voices: Optional[Dict[str, str]] = Field(None, description="[已废弃] 角色音色映射，base64编码的音频文件（已废弃，请使用role_voice_urls）")
    silence_interval: int = Field(300, description="角色切换静音间隔（毫秒）", ge=100, le=1000)
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
    intro_music: Optional[str] = Field(None, description="[已废弃] 开场音乐，base64编码的音频文件（已废弃）")
    outro_music: Optional[str] = Field(None, description="[已废弃] 结尾音乐，base64编码的音频文件（已废弃）")
    background_music: Optional[str] = Field(None, description="[已废弃] 背景音乐，base64编码的音频文件（已废弃）")
    background_volume: float = Field(0.3, description="背景音乐音量（0.0-1.0）", ge=0.0, le=1.0)
    # 如果为 True，则在生成完成后等待上传到 AGC 完成（同步），超时由 upload_timeout 控制（秒）。
    wait_for_upload: bool = Field(True, description="是否等待上传到云存储完成（可选，默认false）")
    upload_timeout: int = Field(30, description="等待上传完成的超时时间（秒）", ge=1, le=600)
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
    characters: List[CharacterInfo] = Field(..., description="角色列表", min_items=2, max_items=3)
    topic: Optional[str] = Field(None, description="播客主题（可选）")
    silence_interval: int = Field(300, description="角色切换静音间隔（毫秒）", ge=100, le=1000)
    job_id: Optional[str] = Field(None, description="可选任务ID，用于前端轮询进度")


class DeepPodcastRequest(BaseModel):
    """主题深度播客请求"""
    topic: str = Field(..., description="播客主题")
    role_voice_urls: Dict[str, str] = Field(..., description="角色音色映射，云存储URL（必需，键为角色名，值为云存储下载URL）")
    role_voices: Optional[Dict[str, str]] = Field(None, description="[已废弃] 角色音色映射，base64编码的音频文件（已废弃，请使用role_voice_urls）")
    num_characters: int = Field(2, description="角色数量", ge=2, le=3)
    depth_level: str = Field("深度", description="深度级别", pattern="^(深度|中等|浅层)$")
    silence_interval: int = Field(300, description="角色切换静音间隔（毫秒）", ge=100, le=1000)
    wait_for_upload: bool = Field(False, description="是否等待上传到云存储完成（可选，默认false）")
    upload_timeout: int = Field(30, description="等待上传完成的超时时间（秒）", ge=1, le=600)
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


def download_audio_from_url(url: str, suffix: str = ".wav", timeout: int = 60) -> str:
    """从URL下载音频文件并保存到临时文件
    
    注意：华为AGC云存储的下载URL通常可以直接访问，不需要额外认证。
    如果下载失败（如403 Forbidden），可能需要检查云存储的安全规则配置。
    """
    try:
        logger.info(f"从URL下载音频文件: {url}")
        
        # 下载文件（华为AGC云存储的下载URL通常可以直接访问）
        # 如果URL需要认证，可以在headers中添加Authorization头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, timeout=timeout, stream=True, headers=headers)
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
        
        # 保存到临时文件
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        
        # 流式下载
        downloaded_size = 0
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                temp_file.write(chunk)
                downloaded_size += len(chunk)
                # 检查下载大小
                if downloaded_size > MAX_AUDIO_FILE_SIZE:
                    temp_file.close()
                    os.unlink(temp_file.name)
                    raise HTTPException(
                        status_code=400,
                        detail=f"音频文件过大: {downloaded_size / (1024 * 1024):.2f} MB (限制: {MAX_AUDIO_FILE_SIZE / 1024 / 1024:.2f} MB)"
                    )
        
        temp_file.close()
        
        file_size_mb = downloaded_size / (1024 * 1024)
        logger.info(f"音频文件已下载到临时文件: {temp_file.name}, 大小: {file_size_mb:.2f} MB")
        return temp_file.name
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            logger.error(f"下载音频文件失败: 403 Forbidden - 可能是云存储安全规则限制或需要认证")
            logger.error(f"请检查华为AGC云存储的安全规则配置，确保下载URL可以公开访问")
            raise HTTPException(status_code=400, detail=f"下载音频文件失败: 403 Forbidden - 请检查云存储安全规则配置")
        else:
            logger.error(f"下载音频文件失败: HTTP {e.response.status_code} - {str(e)}")
            raise HTTPException(status_code=400, detail=f"下载音频文件失败: HTTP {e.response.status_code} - {str(e)}")
    except requests.exceptions.RequestException as e:
        logger.error(f"下载音频文件失败: {str(e)}")
        raise HTTPException(status_code=400, detail=f"下载音频文件失败: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载音频文件异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"下载音频文件异常: {str(e)}")


def download_text_from_url(url: str, timeout: int = 60) -> str:
    """从URL下载文本文件并返回内容（支持.txt和Word文件）
    
    Args:
        url: 文本文件的云存储URL
        timeout: 超时时间（秒）
        
    Returns:
        文本内容（字符串）
    
    注意：华为AGC云存储的下载URL通常可以直接访问，不需要额外认证。
    如果下载失败（如403 Forbidden），可能需要检查云存储的安全规则配置。
    """
    try:
        logger.info(f"从URL下载文本文件: {url}")
        
        # 下载文件（华为AGC云存储的下载URL通常可以直接访问）
        # 如果URL需要认证，可以在headers中添加Authorization头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, timeout=timeout, stream=True, headers=headers)
        response.raise_for_status()
        
        # 检查Content-Type
        content_type = response.headers.get("content-type", "").lower()
        file_extension = url.lower().split('.')[-1] if '.' in url else ''
        
        # 读取文件内容
        content_bytes = response.content
        
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
        project_id = j.get('project_id') or j.get('project_id') or j.get('project_id')
        return client_id, client_secret, project_id
    except Exception:
        return None, None, None


def encode_file_to_base64(file_path: str) -> str:
    """将文件编码为base64"""
    try:
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件编码失败: {str(e)}")


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
                "multi_role_async": "/api/v1/podcast/multi_role_async",
                "character": "/api/v1/podcast/character",
                "deep": "/api/v1/podcast/deep",
                "analyze": "/api/v1/podcast/analyze",
                "health": "/health",
                "progress": "/api/v1/podcast/progress/{job_id}",
                "result": "/api/v1/podcast/result/{job_id}",
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
    start_time = time.time()
    _update_progress(request.job_id, "queued", 1, "任务已排队")
    
    # 验证文本输入（text或text_file_url至少有一个）
    has_text = request.text and request.text.strip()
    has_text_file = request.text_file_url and request.text_file_url.strip()
    
    if not has_text and not has_text_file:
        raise HTTPException(status_code=400, detail="text或text_file_url至少需要提供一个")
    
    # 获取文本内容
    if has_text_file:
        # 从云存储URL读取文本文件
        logger.info(f"从云存储URL读取文本文件: {request.text_file_url}")
        try:
            text_content = download_text_from_url(request.text_file_url)
            logger.info(f"文本文件读取成功: {len(text_content)} 字符")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"读取文本文件失败: {str(e)}")
            raise HTTPException(status_code=400, detail=f"读取文本文件失败: {str(e)}")
    else:
        # 使用直接输入的文本
        text_content = request.text
        logger.info(f"使用直接输入的文本: {len(text_content)} 字符")
    
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
        
        try:
            _update_progress(request.job_id, "downloading_voices", 5, "正在下载角色音色文件")
            for role, voice_data in role_voice_data.items():
                logger.info(f"获取角色 '{role}' 的音频文件...")
                if use_cloud_storage:
                    # 从云存储URL下载
                    logger.info(f"从云存储下载: {voice_data}")
                    temp_file = download_audio_from_url(voice_data)
                else:
                    # 从base64解码
                    logger.info(f"从base64解码")
                    temp_file = decode_base64_audio(voice_data)
                temp_files.append(temp_file)
                role_voices[role] = temp_file
                logger.info(f"角色 '{role}' 音频文件获取完成")
            
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
                    scene_types=request.scene_types if request.scene_types else None
                )
                
                generated_text = api_client.generate_text(
                    prompt=prompt,
                    temperature=0.8,
                    max_tokens=2500
                )
                
                generated_text = processor.clean_text(generated_text)
                text_content = generated_text
                roles = processor.extract_roles(text_content)
            
            # 生成播客
            logger.info("开始生成播客音频...")
            _update_progress(request.job_id, "generating", 25, "正在生成语音与合成音频")
            generation_start = time.time()
            output_path = gen.generate_from_text(
                text=text_content,
                role_voices=role_voices,
                silence_interval=request.silence_interval,
                intro_music=intro_music_path,
                outro_music=outro_music_path,
                background_music=background_music_path,
                background_volume=request.background_volume,
                verbose=True
            )
            generation_time = time.time() - generation_start
            logger.info(f"播客音频生成完成，耗时: {generation_time:.2f}s")
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
                    object_name = os.path.join('outputs', 'podcasts', os.path.basename(output_path))
                    try:
                        if request.wait_for_upload:
                            logger.info("请求要求等待上传完成，开始同步上传...")
                            _update_progress(request.job_id, "uploading", 90, "正在上传到云存储（同步）")
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
                                    res = future.result(timeout=request.upload_timeout)
                                    agc_result = {
                                        'status': 'uploaded',
                                        'bucket': agc_bucket,
                                        'object': object_name,
                                        'http_status': res.get('http_status'),
                                        'response_text': res.get('response_text'),
                                        'url': f"{agc_storage_url.rstrip('/')}/{agc_bucket}/{object_name}"
                                    }
                                    logger.info(f"同步 AGC 上传完成: {agc_result}")
                                    _update_progress(request.job_id, "completed", 100, "生成完成", done=True)
                                except concurrent.futures.TimeoutError:
                                    logger.warning("同步上传超时，已改为后台继续上传")
                                    background_tasks.add_task(do_agc_upload, output_path, agc_storage_url, agc_bucket,
                                                              agc_product_id, agc_domain, agc_client_id, agc_client_secret)
                                    agc_result = {
                                        'status': 'timeout_and_background',
                                        'bucket': agc_bucket,
                                        'object': object_name,
                                        'url': f"{agc_storage_url.rstrip('/')}/{agc_bucket}/{object_name}"
                                    }
                                    _update_progress(request.job_id, "uploading", 95, "上传将在后台完成", done=True)
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
                            _update_progress(request.job_id, "uploading", 95, "后台上传已开始", done=True)
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
                "audio_path": output_path,
                "file_size_mb": round(file_size, 2),
                "script": text_content,
                "roles": list(roles)
            }
            if agc_result:
                data['agc_upload_status'] = agc_result
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
    
    - **characters**: 角色列表（至少2个，最多3个），每个角色必须提供voice_url（云存储URL）
    - **topic**: 播客主题（可选）
    - **silence_interval**: 角色切换静音间隔（毫秒）
    
    注意：本接口仅支持云存储URL，不再支持base64编码的音频文件
    """
    start_time = time.time()
    logger.info(f"开始生成自定义角色播客: 角色数量={len(request.characters)}, 主题={request.topic}, 使用云存储")
    
    try:
        gen = get_generator()
        processor = TextProcessor()
        api_client = get_client()
        
        # 从云存储URL下载音频文件并构建角色信息
        temp_files = []
        character_descriptions = {}
        role_voices = {}
        
        try:
            for char in request.characters:
                logger.info(f"从云存储下载角色 '{char.name}' 的音频文件: {char.voice_url}")
                # 从云存储URL下载
                temp_file = download_audio_from_url(char.voice_url)
                temp_files.append(temp_file)
                role_voices[char.name] = temp_file
                logger.info(f"角色 '{char.name}' 音频文件下载完成")
                
                character_descriptions[char.name] = {
                    "identity": char.identity or "",
                    "personality": char.personality or "",
                    "catchphrase": char.catchphrase or "",
                    "speaking_style": char.speaking_style or "",
                    "relationship": char.relationship or ""
                }
            
            # 生成对话文本
            logger.info("调用混元大模型生成对话文本...")
            prompt = processor.build_character_prompt(
                character_descriptions,
                request.topic if request.topic else None
            )
            
            text_generation_start = time.time()
            generated_text = api_client.generate_text(
                prompt=prompt,
                temperature=0.8,
                max_tokens=2500
            )
            text_generation_time = time.time() - text_generation_start
            logger.info(f"对话文本生成完成，耗时: {text_generation_time:.2f}s，文本长度: {len(generated_text)}")
            
            cleaned_text = processor.clean_text(generated_text)
            
            # 生成播客
            logger.info("开始生成播客音频...")
            generation_start = time.time()
            output_path = gen.generate_from_text(
                text=cleaned_text,
                role_voices=role_voices,
                silence_interval=request.silence_interval,
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
                    object_name = os.path.join('outputs', 'podcasts', os.path.basename(output_path))
                    try:
                        if request.wait_for_upload:
                            # 同步上传，等待完成（阻塞，超时由 upload_timeout 控制）
                            logger.info("请求要求等待上传完成，开始同步上传...")
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
                                    res = future.result(timeout=request.upload_timeout)
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
                                    logger.warning("同步上传超时，已改为后台继续上传")
                                    # 改为后台继续上传
                                    background_tasks.add_task(do_agc_upload, output_path, agc_storage_url, agc_bucket,
                                                              agc_product_id, agc_domain, agc_client_id, agc_client_secret)
                                    agc_result = {
                                        'status': 'timeout_and_background',
                                        'bucket': agc_bucket,
                                        'object': object_name,
                                        'url': f"{agc_storage_url.rstrip('/')}/{agc_bucket}/{object_name}"
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
                "audio_path": output_path,
                "file_size_mb": round(file_size, 2),
                "script": cleaned_text,
                "characters": [char.name for char in request.characters]
            }
            if agc_result:
                data['agc_upload_status'] = agc_result

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
    - **num_characters**: 角色数量（2-3个）
    - **depth_level**: 深度级别（深度/中等/浅层）
    - **silence_interval**: 角色切换静音间隔（毫秒）
    
    注意：本接口仅支持云存储URL，不再支持base64编码的音频文件
    """
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
            role_names = ["角色A", "角色B", "角色C"][:request.num_characters]
            for i, role_name in enumerate(role_names):
                if role_name in request.role_voice_urls:
                    voice_url = request.role_voice_urls[role_name]
                    logger.info(f"从云存储下载角色 '{role_name}' 的音频文件: {voice_url}")
                    # 从云存储URL下载
                    temp_file = download_audio_from_url(voice_url)
                    temp_files.append(temp_file)
                    role_voices[role_name] = temp_file
                    logger.info(f"角色 '{role_name}' 音频文件下载完成")
                else:
                    raise HTTPException(status_code=400, detail=f"缺少角色 '{role_name}' 的音色文件URL")
            
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
                max_tokens=2500
            )
            text_generation_time = time.time() - text_generation_start
            logger.info(f"对话文本生成完成，耗时: {text_generation_time:.2f}s，文本长度: {len(generated_text)}")
            
            cleaned_text = processor.clean_text(generated_text)
            
            # 生成播客
            logger.info("开始生成播客音频...")
            generation_start = time.time()
            output_path = gen.generate_from_text(
                text=cleaned_text,
                role_voices=role_voices,
                silence_interval=request.silence_interval,
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
                    object_name = os.path.join('outputs', 'podcasts', os.path.basename(output_path))
                    try:
                        if request.wait_for_upload:
                            # 同步上传，等待完成（阻塞，超时由 upload_timeout 控制）
                            logger.info("请求要求等待上传完成，开始同步上传...")
                            try:
                                res = agc_upload_client(
                                    output_path=output_path,
                                    storage_url=agc_storage_url,
                                    bucket=agc_bucket,
                                    product_id=agc_product_id,
                                    domain=agc_domain,
                                    client_id=agc_client_id,
                                    client_secret=agc_client_secret,
                                )
                                agc_result = {
                                    'status': 'uploaded',
                                    'bucket': agc_bucket,
                                    'object': object_name,
                                    'http_status': res.get('http_status'),
                                    'response_text': res.get('response_text'),
                                    'url': f"{agc_storage_url.rstrip('/')}/{agc_bucket}/{object_name}"
                                }
                                logger.info(f"同步 AGC 上传完成: {agc_result}")
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
                "audio_path": output_path,
                "file_size_mb": round(file_size, 2),
                "script": cleaned_text,
                "topic": request.topic,
                "depth_level": request.depth_level
            }
            if agc_result:
                data['agc_upload_status'] = agc_result

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
    获取任务进度（前端可每秒轮询）
    """
    try:
        return _get_progress(job_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/podcast/result/{job_id}", response_model=ApiResponse)
async def get_podcast_result(job_id: str):
    """
    获取异步任务的最终结果
    """
    try:
        data = _get_job_result(job_id)
        if not data:
            return ApiResponse(success=False, message="结果尚不可用", error="not_ready")
        return ApiResponse(success=True, message="ok", data=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _run_multi_role_job(request_dict: Dict[str, Any], job_id: str):
    """
    后台线程执行多角色播客生成任务，将结果写入 job 结果文件中
    """
    try:
        # 将请求字典映射到模型
        req = MultiRoleRequest(**request_dict)
        # 直接调用现有的生成流程，但在本函数内复用主要逻辑代码片段
        # 为避免重复，调用生成端点的核心流程：复制必要片段（较短化）
        start_time = time.time()
        _update_progress(job_id, "queued", 1, "任务已排队")

        has_text = req.text and req.text.strip()
        has_text_file = req.text_file_url and req.text_file_url.strip()
        if not has_text and not has_text_file:
            raise ValueError("text或text_file_url至少需要提供一个")

        if has_text_file:
            text_content = download_text_from_url(req.text_file_url)
        else:
            text_content = req.text

        has_voice_urls = req.role_voice_urls and len(req.role_voice_urls) > 0
        has_voices = req.role_voices and len(req.role_voices) > 0
        if not has_voice_urls and not has_voices:
            raise ValueError("至少需要提供一个角色的音色文件（role_voice_urls或role_voices）")

        use_cloud_storage = has_voice_urls
        role_voice_data = req.role_voice_urls if use_cloud_storage else req.role_voices

        gen = get_generator()
        processor = TextProcessor()

        temp_files = []
        role_voices = {}
        try:
            _update_progress(job_id, "downloading_voices", 5, "正在下载角色音色文件")
            for role, voice_data in role_voice_data.items():
                if use_cloud_storage:
                    temp_file = download_audio_from_url(voice_data)
                else:
                    temp_file = decode_base64_audio(voice_data)
                temp_files.append(temp_file)
                role_voices[role] = temp_file

            roles = processor.extract_roles(text_content)
            if not roles:
                api_client = get_client()
                num_characters = min(len(role_voices), 3)
                character_descriptions = {}
                characters = [
                    (req.character_1_name, req.character_1_personality, req.character_1_speaking_style),
                    (req.character_2_name, req.character_2_personality, req.character_2_speaking_style),
                    (req.character_3_name, req.character_3_personality, req.character_3_speaking_style),
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
                    podcast_name=req.podcast_name if req.podcast_name else None,
                    topic=req.topic if req.topic else None,
                    character_descriptions=character_descriptions if character_descriptions else None,
                    scene_types=req.scene_types if req.scene_types else None
                )
                generated_text = get_client().generate_text(prompt=prompt, temperature=0.8, max_tokens=2500)
                text_content = processor.clean_text(generated_text)
                roles = processor.extract_roles(text_content)

            _update_progress(job_id, "generating", 25, "正在生成语音与合成音频")
            output_path = gen.generate_from_text(
                text=text_content,
                role_voices=role_voices,
                silence_interval=req.silence_interval,
                background_volume=req.background_volume,
                verbose=True
            )
            _update_progress(job_id, "saving", 85, "保存音频文件")

            # 上传
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
                if agc_storage_url and agc_bucket and agc_upload_client:
                    object_name = os.path.join('outputs', 'podcasts', os.path.basename(output_path))
                    # 异步任务采用后台上传（不阻塞）
                    try:
                        res = agc_upload_client(
                            output_path=output_path,
                            storage_url=agc_storage_url,
                            bucket=agc_bucket,
                            product_id=agc_product_id,
                            domain=agc_domain,
                            client_id=agc_client_id,
                            client_secret=agc_client_secret,
                        )
                        agc_result = {
                            'status': 'uploaded',
                            'bucket': agc_bucket,
                            'object': object_name,
                            'http_status': res.get('http_status'),
                            'response_text': res.get('response_text'),
                            'url': f"{agc_storage_url.rstrip('/')}/{agc_bucket}/{object_name}"
                        }
                    except Exception as e:
                        agc_result = {'status': 'failed', 'reason': str(e)}
            except Exception:
                pass

            audio_base64 = encode_file_to_base64(output_path)
            file_size = os.path.getsize(output_path) / (1024 * 1024)
            data = {
                "audio_base64": audio_base64,
                "audio_path": output_path,
                "file_size_mb": round(file_size, 2),
                "script": text_content,
                "roles": list(roles)
            }
            if agc_result:
                data['agc_upload_status'] = agc_result
                if isinstance(agc_result, dict) and agc_result.get('url'):
                    data['audio_url'] = agc_result['url']

            _save_job_result(job_id, data)
            _update_progress(job_id, "completed", 100, "生成完成", done=True)
        finally:
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except:
                    pass
    except Exception as e:
        _update_progress(job_id, "failed", 100, f"生成失败: {str(e)}", done=True, error=str(e))

@app.post("/api/v1/podcast/multi_role_async")
async def generate_multi_role_podcast_async(request: MultiRoleRequest, background_tasks: BackgroundTasks):
    """
    异步版本：立即返回 job_id，后台执行生成流程
    """
    # 创建/使用 job_id
    job_id = request.job_id or f"job_{int(time.time()*1000)}"
    _update_progress(job_id, "queued", 1, "任务已排队")
    # 入队后台任务
    background_tasks.add_task(_run_multi_role_job, request.model_dump(), job_id)
    return {"success": True, "message": "queued", "data": {"job_id": job_id}}

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


