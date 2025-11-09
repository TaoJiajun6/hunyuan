"""
混元AI播客生成系统 - REST API服务
提供REST API接口供工作流系统调用
"""
import os
import sys
import base64
import tempfile
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from .podcast_generator import PodcastGenerator
from .config import INDEXTTS_CONFIG_PATH, INDEXTTS_MODEL_DIR, OUTPUT_DIR
from .text_processor import TextProcessor
from .api_client import get_client


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


def get_generator() -> PodcastGenerator:
    """获取或创建生成器实例"""
    global generator
    if generator is None:
        generator = PodcastGenerator(
            tts_config_path=INDEXTTS_CONFIG_PATH,
            tts_model_dir=INDEXTTS_MODEL_DIR
        )
    return generator


# ============ 请求模型 ============

class MultiRoleRequest(BaseModel):
    """多角色互动播客请求"""
    text: str = Field(..., description="播客文本（支持角色标记或普通文本）")
    role_voices: Dict[str, str] = Field(..., description="角色音色映射，base64编码的音频文件")
    silence_interval: int = Field(300, description="角色切换静音间隔（毫秒）", ge=100, le=1000)


class CharacterInfo(BaseModel):
    """角色信息"""
    name: str = Field(..., description="角色名称")
    identity: Optional[str] = Field(None, description="身份/职业")
    personality: Optional[str] = Field(None, description="核心性格")
    catchphrase: Optional[str] = Field(None, description="口头禅/说话习惯")
    speaking_style: Optional[str] = Field(None, description="说话风格")
    relationship: Optional[str] = Field(None, description="与其他角色的关系")
    voice: str = Field(..., description="音色文件，base64编码")


class CharacterRequest(BaseModel):
    """自定义角色播客请求"""
    characters: List[CharacterInfo] = Field(..., description="角色列表", min_items=2, max_items=3)
    topic: Optional[str] = Field(None, description="播客主题（可选）")
    silence_interval: int = Field(300, description="角色切换静音间隔（毫秒）", ge=100, le=1000)


class DeepPodcastRequest(BaseModel):
    """主题深度播客请求"""
    topic: str = Field(..., description="播客主题")
    role_voices: Dict[str, str] = Field(..., description="角色音色映射，base64编码的音频文件")
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
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_file.write(audio_data)
        temp_file.close()
        return temp_file.name
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"音频解码失败: {str(e)}")


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
                "health": "/health",
                "docs": "/docs"
            }
        }
    )


@app.get("/health")
async def health():
    """健康检查端点"""
    return {"status": "healthy", "service": "混元AI播客生成API"}


@app.post("/api/v1/podcast/multi_role", response_model=ApiResponse)
async def generate_multi_role_podcast(request: MultiRoleRequest):
    """
    生成多角色互动播客（子题目1）
    
    - **text**: 播客文本（支持角色标记或普通文本）
    - **role_voices**: 角色音色映射，键为角色名，值为base64编码的音频文件
    - **silence_interval**: 角色切换静音间隔（毫秒）
    """
    try:
        gen = get_generator()
        processor = TextProcessor()
        
        # 解码音频文件
        temp_files = []
        role_voices = {}
        try:
            for role, voice_base64 in request.role_voices.items():
                temp_file = decode_base64_audio(voice_base64)
                temp_files.append(temp_file)
                role_voices[role] = temp_file
            
            # 解析文本中的角色
            roles = processor.extract_roles(request.text)
            
            # 如果没有找到角色标记，使用混元大模型自动转换为多角色对话
            if not roles:
                api_client = get_client()
                num_characters = min(len(role_voices), 3)
                
                prompt = processor.build_text_to_dialogue_prompt(
                    text=request.text,
                    num_characters=num_characters,
                    style="自然互动"
                )
                
                generated_text = api_client.generate_text(
                    prompt=prompt,
                    temperature=0.8,
                    max_tokens=2500
                )
                
                generated_text = processor.clean_text(generated_text)
                request.text = generated_text
                roles = processor.extract_roles(request.text)
            
            # 生成播客
            output_path = gen.generate_from_text(
                text=request.text,
                role_voices=role_voices,
                silence_interval=request.silence_interval,
                verbose=True
            )
            
            # 编码输出音频
            audio_base64 = encode_file_to_base64(output_path)
            file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
            
            return ApiResponse(
                success=True,
                message="播客生成成功",
                data={
                    "audio_base64": audio_base64,
                    "audio_path": output_path,
                    "file_size_mb": round(file_size, 2),
                    "script": request.text,
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
                    
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
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
    
    - **characters**: 角色列表（至少2个，最多3个）
    - **topic**: 播客主题（可选）
    - **silence_interval**: 角色切换静音间隔（毫秒）
    """
    try:
        gen = get_generator()
        processor = TextProcessor()
        api_client = get_client()
        
        # 解码音频文件并构建角色信息
        temp_files = []
        character_descriptions = {}
        role_voices = {}
        
        try:
            for char in request.characters:
                temp_file = decode_base64_audio(char.voice)
                temp_files.append(temp_file)
                role_voices[char.name] = temp_file
                
                character_descriptions[char.name] = {
                    "identity": char.identity or "",
                    "personality": char.personality or "",
                    "catchphrase": char.catchphrase or "",
                    "speaking_style": char.speaking_style or "",
                    "relationship": char.relationship or ""
                }
            
            # 生成对话文本
            prompt = processor.build_character_prompt(
                character_descriptions,
                request.topic if request.topic else None
            )
            
            generated_text = api_client.generate_text(
                prompt=prompt,
                temperature=0.8,
                max_tokens=2500
            )
            
            cleaned_text = processor.clean_text(generated_text)
            
            # 生成播客
            output_path = gen.generate_from_text(
                text=cleaned_text,
                role_voices=role_voices,
                silence_interval=request.silence_interval,
                verbose=True
            )
            
            # 编码输出音频
            audio_base64 = encode_file_to_base64(output_path)
            file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
            
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
                    
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
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
    - **role_voices**: 角色音色映射，键为角色名，值为base64编码的音频文件
    - **num_characters**: 角色数量（2-3个）
    - **depth_level**: 深度级别（深度/中等/浅层）
    - **silence_interval**: 角色切换静音间隔（毫秒）
    """
    try:
        gen = get_generator()
        processor = TextProcessor()
        api_client = get_client()
        
        # 解码音频文件
        temp_files = []
        role_voices = {}
        
        try:
            role_names = ["角色A", "角色B", "角色C"][:request.num_characters]
            for i, role_name in enumerate(role_names):
                if role_name in request.role_voices:
                    temp_file = decode_base64_audio(request.role_voices[role_name])
                    temp_files.append(temp_file)
                    role_voices[role_name] = temp_file
            
            # 生成对话文本
            prompt = processor.build_deep_podcast_prompt(
                request.topic,
                request.depth_level,
                request.num_characters
            )
            
            generated_text = api_client.generate_text(
                prompt=prompt,
                temperature=0.7,
                max_tokens=2500
            )
            
            cleaned_text = processor.clean_text(generated_text)
            
            # 生成播客
            output_path = gen.generate_from_text(
                text=cleaned_text,
                role_voices=role_voices,
                silence_interval=request.silence_interval,
                verbose=True
            )
            
            # 编码输出音频
            audio_base64 = encode_file_to_base64(output_path)
            file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
            
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
                    
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return ApiResponse(
            success=False,
            message="播客生成失败",
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


