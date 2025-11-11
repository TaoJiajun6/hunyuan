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
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, ValidationError
import uvicorn

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


class DeepPodcastRequest(BaseModel):
    """主题深度播客请求"""
    topic: str = Field(..., description="播客主题")
    role_voice_urls: Dict[str, str] = Field(..., description="角色音色映射，云存储URL（必需，键为角色名，值为云存储下载URL）")
    role_voices: Optional[Dict[str, str]] = Field(None, description="[已废弃] 角色音色映射，base64编码的音频文件（已废弃，请使用role_voice_urls）")
    num_characters: int = Field(2, description="角色数量", ge=2, le=3)
    depth_level: str = Field("深度", description="深度级别", pattern="^(深度|中等|浅层)$")
    silence_interval: int = Field(300, description="角色切换静音间隔（毫秒）", ge=100, le=1000)


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
            logger.warning(f"未知文件类型: {file_extension}，尝试作为文本处理")
            try:
                text = content_bytes.decode('utf-8')
            except UnicodeDecodeError:
                text = content_bytes.decode('utf-8', errors='ignore')
            return text
            
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


def encode_file_to_base64(file_path: str) -> str:
    """将文件编码为base64"""
    try:
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件编码失败: {str(e)}")


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
async def generate_multi_role_podcast(request: MultiRoleRequest):
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
            
            # 编码输出音频
            logger.info("编码输出音频文件...")
            audio_base64 = encode_file_to_base64(output_path)
            file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
            total_time = time.time() - start_time
            logger.info(f"多角色播客生成成功，总耗时: {total_time:.2f}s，输出文件大小: {file_size:.2f} MB")
            
            return ApiResponse(
                success=True,
                message="播客生成成功",
                data={
                    "audio_base64": audio_base64,
                    "audio_path": output_path,
                    "file_size_mb": round(file_size, 2),
                    "script": text_content,
                    "roles": list(roles)
                }
            )
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
        logger.error(f"多角色播客生成失败，耗时: {total_time:.2f}s，错误: {str(e)}")
        logger.error(f"错误详情:\n{error_detail}")
        return ApiResponse(
            success=False,
            message="播客生成失败",
            error=str(e),
            data={"traceback": error_detail}
        )


@app.post("/api/v1/podcast/character", response_model=ApiResponse)
async def generate_character_podcast(request: CharacterRequest):
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
            
            return ApiResponse(
                success=True,
                message="播客生成成功",
                data={
                    "audio_base64": audio_base64,
                    "audio_path": output_path,
                    "file_size_mb": round(file_size, 2),
                    "script": cleaned_text,
                    "characters": [char.name for char in request.characters]
                }
            )
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
async def generate_deep_podcast(request: DeepPodcastRequest):
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
            
            return ApiResponse(
                success=True,
                message="播客生成成功",
                data={
                    "audio_base64": audio_base64,
                    "audio_path": output_path,
                    "file_size_mb": round(file_size, 2),
                    "script": cleaned_text,
                    "topic": request.topic,
                    "depth_level": request.depth_level
                }
            )
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


