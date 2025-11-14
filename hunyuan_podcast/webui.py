"""
混元AI播客生成系统 - WebUI界面
基于Gradio创建独立Web界面，实现三个功能标签页
"""
import os
import sys
import argparse
import re
from typing import Dict, Optional, Tuple, List, Union

# gradio 将在 create_webui 函数中导入，以便提供更好的错误提示

from .podcast_generator import PodcastGenerator
from .config import SOULX_PODCAST_MODEL_DIR, SOULX_PODCAST_LLM_ENGINE, SOULX_PODCAST_FP16_FLOW
from .text_processor import TextProcessor


# 全局播客生成器实例
podcast_gen: Optional[PodcastGenerator] = None
# 全局生成器配置
_generator_config: Optional[dict] = None


def init_generator(llm_engine: Optional[str] = None, fp16_flow: Optional[bool] = None, device: Optional[str] = None):
    """
    初始化播客生成器
    如果参数为None，则使用全局配置
    """
    global podcast_gen, _generator_config
    
    # 如果已有配置，使用配置中的值（如果参数为None）
    if _generator_config is not None:
        llm_engine = llm_engine if llm_engine is not None else _generator_config.get('llm_engine', None)
        fp16_flow = fp16_flow if fp16_flow is not None else _generator_config.get('fp16_flow', None)
        device = device if device is not None else _generator_config.get('device', None)
    
    if podcast_gen is None:
        print("正在初始化播客生成器...")
        podcast_gen = PodcastGenerator(
            tts_model_dir=SOULX_PODCAST_MODEL_DIR,
            llm_engine=llm_engine,
            fp16_flow=fp16_flow,
            device=device
        )
        print("播客生成器初始化完成！")
    return podcast_gen


def set_generator_config(llm_engine: Optional[str] = None, fp16_flow: Optional[bool] = None, device: Optional[str] = None):
    """设置全局生成器配置"""
    global _generator_config
    _generator_config = {
        'llm_engine': llm_engine,
        'fp16_flow': fp16_flow,
        'device': device
    }


def wrap_multi_role_podcast(
    text, role_a_voice, role_b_voice, role_c_voice, silence_interval,
    podcast_name, topic,
    character_1_name, character_1_personality, character_1_speaking_style,
    character_2_name, character_2_personality, character_2_speaking_style,
    character_3_name, character_3_personality, character_3_speaking_style,
    scene_types, auto_select_music, background_music, background_volume,
    background_mode, progress=None
):
    """包装函数，格式化脚本输出"""
    # 处理多文件上传（Gradio File 组件返回文件对象列表）
    def process_file_input(file_input):
        if not file_input:
            return None
        if isinstance(file_input, list):
            # 如果是列表，提取文件路径
            paths = [f.name if hasattr(f, 'name') else str(f) for f in file_input if f]
            return paths if paths else None
        elif hasattr(file_input, 'name'):
            return file_input.name
        else:
            return str(file_input) if file_input else None
    
    # 如果启用AI自动选择音乐，则忽略手动上传的音乐
    background_music_processed = None
    if auto_select_music:
        # AI自动选择音乐
        try:
            print("=" * 60)
            print("开始AI自动选择背景音乐...")
            from .music_selector import MusicSelector
            selector = MusicSelector(use_cloud_storage=True)
            background_music_processed = selector.select_music_by_ai(
                text=text,
                podcast_name=podcast_name if podcast_name and podcast_name.strip() else None,
                topic=topic if topic and topic.strip() else None,
                scene_types=scene_types if scene_types else None,
                num_music=1
            )
            # 如果AI选择返回空列表，设置为None
            if isinstance(background_music_processed, list) and len(background_music_processed) == 0:
                print("⚠️ AI选择音乐返回空列表")
                background_music_processed = None
            elif background_music_processed:
                print(f"✓ AI选择的背景音乐: {background_music_processed}")
                for i, music_path in enumerate(background_music_processed, 1):
                    if music_path and os.path.exists(music_path):
                        print(f"  [{i}] {os.path.basename(music_path)} ({music_path})")
                    else:
                        print(f"  [{i}] ⚠️ 文件不存在: {music_path}")
            else:
                print("⚠️ AI选择音乐返回None")
            print("=" * 60)
        except Exception as e:
            import traceback
            print(f"✗ AI自动选择音乐失败: {str(e)}")
            print(f"  错误详情: {traceback.format_exc()}")
            background_music_processed = None
    else:
        # 手动上传的音乐
        background_music_processed = process_file_input(background_music)
        print(f"手动上传的背景音乐: {background_music_processed}")
    
    audio_path, status, script = generate_multi_role_podcast(
        text, role_a_voice, role_b_voice, role_c_voice, silence_interval,
        podcast_name, topic,
        character_1_name, character_1_personality, character_1_speaking_style,
        character_2_name, character_2_personality, character_2_speaking_style,
        character_3_name, character_3_personality, character_3_speaking_style,
        scene_types, background_music_processed, background_volume, background_mode, progress
    )
    if script:
        formatted_script = format_script_for_display(script)
    else:
        formatted_script = "<div style='padding: 20px; color: #666; text-align: center;'>脚本生成失败或为空</div>"
    return audio_path, status, formatted_script

def analyze_text_for_podcast_ui(text, progress=None):
    """
    在WebUI中调用自动分析功能
    
    Args:
        text: 文本素材
        progress: Gradio进度条
    
    Returns:
        分析结果，用于填充UI字段
    """
    if not text or not text.strip():
        return (
            "",  # podcast_name
            "",  # topic
            "", "", "",  # character_1
            "", "", "",  # character_2
            "", "", "",  # character_3
            []   # scene_types
        )
    
    try:
        from .api_client import get_client
        from .text_processor import TextProcessor
        
        api_client = get_client()
        processor = TextProcessor()
        
        if progress:
            progress(0.5, desc="正在分析文本素材...")
        
        result = processor.analyze_text_for_podcast(text, api_client)
        
        if progress:
            progress(1.0, desc="分析完成！")
        
        # 提取角色信息
        characters = result.get("characters", [])
        char_1 = characters[0] if len(characters) > 0 else {}
        char_2 = characters[1] if len(characters) > 1 else {}
        char_3 = characters[2] if len(characters) > 2 else {}
        
        return (
            result.get("podcast_name", ""),
            result.get("topic", ""),
            char_1.get("name", ""),
            char_1.get("personality", ""),
            char_1.get("speaking_style", ""),
            char_2.get("name", ""),
            char_2.get("personality", ""),
            char_2.get("speaking_style", ""),
            char_3.get("name", ""),
            char_3.get("personality", ""),
            char_3.get("speaking_style", ""),
            result.get("scene_types", [])
        )
    except Exception as e:
        print(f"自动分析失败: {str(e)}")
        return (
            "", "", "", "", "", "", "", "", "", "", "", []
        )

def wrap_character_podcast(
    character_a_name, character_a_identity, character_a_personality,
    character_a_catchphrase, character_a_speaking_style, character_a_relationship, character_a_voice,
    character_b_name, character_b_identity, character_b_personality,
    character_b_catchphrase, character_b_speaking_style, character_b_relationship, character_b_voice,
    character_c_name, character_c_identity, character_c_personality,
    character_c_catchphrase, character_c_speaking_style, character_c_relationship, character_c_voice,
    topic, progress=None
):
    """包装函数，格式化脚本输出"""
    audio_path, status, script = generate_character_podcast(
        character_a_name, character_a_identity, character_a_personality,
        character_a_catchphrase, character_a_speaking_style, character_a_relationship, character_a_voice,
        character_b_name, character_b_identity, character_b_personality,
        character_b_catchphrase, character_b_speaking_style, character_b_relationship, character_b_voice,
        character_c_name, character_c_identity, character_c_personality,
        character_c_catchphrase, character_c_speaking_style, character_c_relationship, character_c_voice,
        topic, progress
    )
    if script:
        formatted_script = format_script_for_display(script)
    else:
        formatted_script = "<div style='padding: 20px; color: #666; text-align: center;'>脚本生成失败或为空</div>"
    return audio_path, status, formatted_script

def wrap_deep_podcast(topic, role_a_voice, role_b_voice, role_c_voice, num_characters, depth_level, progress=None):
    """包装函数，格式化脚本输出"""
    audio_path, status, script = generate_deep_podcast(topic, role_a_voice, role_b_voice, role_c_voice, num_characters, depth_level, progress)
    if script:
        formatted_script = format_script_for_display(script)
    else:
        formatted_script = "<div style='padding: 20px; color: #666; text-align: center;'>脚本生成失败或为空</div>"
    return audio_path, status, formatted_script

def format_script_for_display(text: str) -> str:
    """
    格式化脚本文本，用于在WebUI中显示
    为不同角色分配颜色标记，支持情绪标注和音效标注
    
    Args:
        text: 原始脚本文本
    
    Returns:
        格式化后的HTML文本
    """
    import re
    lines = text.split('\n')
    formatted_lines = []
    
    # 角色颜色映射
    role_colors = {
        '角色A': '#3b82f6',  # 蓝色
        '角色B': '#ef4444',  # 红色
        '角色C': '#10b981',  # 绿色
    }
    
    # 提取所有角色
    role_pattern = re.compile(r'\[([^\]]+)\]')
    roles_found = set()
    for line in lines:
        matches = role_pattern.findall(line)
        roles_found.update(matches)
    
    # 为未定义的角色分配颜色
    color_palette = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899']
    color_idx = 0
    for role in sorted(roles_found):
        if role not in role_colors:
            role_colors[role] = color_palette[color_idx % len(color_palette)]
            color_idx += 1
    
    # 处理每行
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 匹配音效标注：[音效：xxx]
        sound_effect_match = re.match(r'^\[音效[：:]([^\]]+)\]$', line)
        if sound_effect_match:
            sound_name = sound_effect_match.group(1)
            formatted_lines.append(
                f'<div style="margin: 6px 0; padding: 6px; background: #fff3cd; border-left: 3px solid #ffc107; border-radius: 4px;">'
                f'<span style="color: #856404; font-size: 0.9em;">🔊 音效：{sound_name}</span></div>'
            )
            continue
        
        # 匹配带情绪标注的格式：[角色名]（情绪地）：内容
        emotion_match = re.match(r'\[([^\]]+)\]\s*（([^）]+)地）\s*[:：]?\s*(.*)', line)
        if emotion_match:
            role_name = emotion_match.group(1)
            emotion = emotion_match.group(2)
            content = emotion_match.group(3)
            color = role_colors.get(role_name, '#6b7280')
            
            # 处理内容中的音效标注
            content_with_sound = re.sub(
                r'\[音效[：:]([^\]]+)\]',
                r'<span style="background: #fff3cd; padding: 2px 6px; border-radius: 3px; font-size: 0.85em; color: #856404;">🔊 \1</span>',
                content
            )
            
            formatted_lines.append(
                f'<div style="margin: 8px 0; padding: 8px; border-left: 3px solid {color}; background: {color}10;">'
                f'<span style="color: {color}; font-weight: bold;">●{role_name}</span> '
                f'<span style="color: #6b7280; font-size: 0.9em;">（{emotion}）</span> '
                f'<span>{content_with_sound}</span></div>'
            )
            continue
        
        # 匹配普通格式：[角色名]内容
        role_match = re.match(r'\[([^\]]+)\]\s*(.*)', line)
        if role_match:
            role_name = role_match.group(1)
            content = role_match.group(2)
            color = role_colors.get(role_name, '#6b7280')
            
            # 处理内容中的音效标注
            content_with_sound = re.sub(
                r'\[音效[：:]([^\]]+)\]',
                r'<span style="background: #fff3cd; padding: 2px 6px; border-radius: 3px; font-size: 0.85em; color: #856404;">🔊 \1</span>',
                content
            )
            
            formatted_lines.append(
                f'<div style="margin: 8px 0; padding: 8px; border-left: 3px solid {color}; background: {color}10;">'
                f'<span style="color: {color}; font-weight: bold;">●{role_name}</span> '
                f'<span>{content_with_sound}</span></div>'
            )
        else:
            # 普通文本（可能是音乐提示等）
            if '[音乐' in line or '音乐' in line:
                formatted_lines.append(
                    f'<div style="margin: 6px 0; padding: 6px; background: #e7f3ff; border-left: 3px solid #3b82f6; border-radius: 4px; color: #1e40af; font-style: italic;">🎵 {line}</div>'
                )
            else:
                formatted_lines.append(f'<div style="margin: 4px 0; padding: 4px; color: #666;">{line}</div>')
    
    return '<div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; line-height: 1.6;">' + \
           ''.join(formatted_lines) + '</div>'


def generate_multi_role_podcast(
    text: str,
    role_a_voice: Optional[str],
    role_b_voice: Optional[str],
    role_c_voice: Optional[str],
    silence_interval: int = 600,  # 默认600ms，增加角色之间的间隔
    podcast_name: Optional[str] = None,
    topic: Optional[str] = None,
    character_1_name: Optional[str] = None,
    character_1_personality: Optional[str] = None,
    character_1_speaking_style: Optional[str] = None,
    character_2_name: Optional[str] = None,
    character_2_personality: Optional[str] = None,
    character_2_speaking_style: Optional[str] = None,
    character_3_name: Optional[str] = None,
    character_3_personality: Optional[str] = None,
    character_3_speaking_style: Optional[str] = None,
    scene_types: Optional[List[str]] = None,
    background_music: Optional[Union[str, List[str]]] = None,
    background_volume: float = 0.3,
    background_mode: str = "random",
    progress=None
) -> Tuple[str, str, str]:
    """
    生成多角色互动播客（子题目1）
    
    Args:
        text: 包含角色标记的文本
        role_a_voice: 角色A的音色文件
        role_b_voice: 角色B的音色文件
        role_c_voice: 角色C的音色文件
        silence_interval: 静音间隔（毫秒）
        progress: Gradio进度条
    
    Returns:
        (输出音频路径, 状态信息)
    """
    try:
        # 先不加载TTS模型，只初始化API客户端和文本处理器
        # 这样可以先调用混元模型生成文本，失败时不需要加载TTS模型
        from .api_client import get_client
        from .text_processor import TextProcessor
        
        api_client = get_client()
        processor = TextProcessor()
        
        verbose = True  # 启用详细输出
        
        # 检查文本是否为空
        if not text or not text.strip():
            return None, "错误：请输入播客文本内容", ""
        
        # 解析文本中的角色
        roles = processor.extract_roles(text)
        
        # 如果没有找到角色标记，使用混元大模型自动转换为多角色对话
        if not roles:
            if progress:
                progress(0.1, desc="检测到普通文本，正在调用混元模型转换为多角色对话...")
            
            # 检查是否有音色文件
            voice_files = [role_a_voice, role_b_voice, role_c_voice]
            num_voices = sum(1 for v in voice_files if v)
            
            if num_voices < 2:
                return None, """错误：需要至少上传2个角色的音色文件

提示：
- 如果输入的是普通文本（没有角色标记），系统会自动调用混元大模型将其转换为多角色对话
- 需要至少上传2个角色的音色文件（角色A和角色B）
- 系统会自动将文本内容分配给多个角色进行互动讨论""", ""
            
            # 确定角色数量（根据上传的音色文件数量）
            num_characters = min(num_voices, 3)
            
            if verbose:
                print(f"检测到普通文本，将使用混元模型转换为{num_characters}角色对话")
            
            # 构建角色描述字典
            character_descriptions = {}
            characters = [
                (character_1_name, character_1_personality, character_1_speaking_style),
                (character_2_name, character_2_personality, character_2_speaking_style),
                (character_3_name, character_3_personality, character_3_speaking_style),
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
            
            # 调用混元模型将文本转换为多角色对话
            try:
                prompt = processor.build_text_to_dialogue_prompt(
                    text=text,
                    num_characters=num_characters,
                    podcast_name=podcast_name if podcast_name and podcast_name.strip() else None,
                    topic=topic if topic and topic.strip() else None,
                    character_descriptions=character_descriptions if character_descriptions else None,
                    scene_types=scene_types if scene_types else None
                )
                
                if progress:
                    progress(0.2, desc=f"正在调用混元模型转换为{num_characters}角色对话...")
                
                if verbose:
                    print(f"发送给混元模型的提示词:\n{prompt[:200]}...")
                
                try:
                    generated_text = api_client.generate_text(
                        prompt=prompt,
                        temperature=0.8,
                        max_tokens=3000  # 降低以加快生成速度，仍支持3-4分钟对话
                    )
                    
                    if verbose:
                        print(f"混元模型原始输出:\n{generated_text}")
                        print(f"\n原始输出长度: {len(generated_text)}")
                    
                    # 检查返回内容是否为空
                    if not generated_text or len(generated_text.strip()) == 0:
                        raise ValueError("混元模型返回了空内容，可能是API调用失败或网络问题")
                        
                except Exception as api_error:
                    error_detail = str(api_error)
                    if verbose:
                        import traceback
                        print(f"API调用异常详情:\n{traceback.format_exc()}")
                    
                    return None, f"""错误：调用混元模型失败

错误详情：{error_detail}

可能的原因：
1. API调用失败（请检查配置文件中的 API 密钥）
2. 网络连接问题
3. API服务暂时不可用
4. 请求参数错误

解决方案：
1. 检查网络连接
2. 检查配置文件中的 API 密钥是否正确（hunyuan_podcast/config.py）
3. 查看终端完整错误信息
4. 或手动添加角色标记，格式：[角色A]内容 [角色B]内容""", ""
                
                # 清理生成的文本
                generated_text = processor.clean_text(generated_text)
                
                if verbose:
                    print(f"\n清理后的文本:\n{generated_text}")
                    print(f"清理后长度: {len(generated_text)}")
                
                # 使用生成的对话文本替换原始文本
                text = generated_text
                
                # 重新解析角色
                roles = processor.extract_roles(text)
                
                if verbose:
                    print(f"\n解析到的角色: {roles}")
                
                if not roles:
                    # 尝试更宽松的解析：查找任何包含方括号的内容
                    bracket_pattern = re.compile(r'\[([^\]]+)\]')
                    potential_roles = bracket_pattern.findall(text)
                    
                    if potential_roles:
                        error_msg = f"""错误：混元模型生成的对话格式不正确

检测到可能的角色标记：{', '.join(set(potential_roles[:5]))}

生成的文本预览：
{text[:300]}...

可能的原因：
- 角色名称格式不符合要求
- 文本格式异常

解决方案：
1. 检查网络连接，重新尝试
2. 简化输入文本内容
3. 手动添加角色标记，格式：[角色A]内容 [角色B]内容"""
                    else:
                        error_msg = f"""错误：混元模型未能生成有效的角色对话

生成的文本预览：
{text[:300]}...

可能的原因：
- 模型返回的文本不包含角色标记
- 网络连接问题导致响应不完整
- API调用失败

解决方案：
1. 检查网络连接
2. 重新输入文本（可以尝试更短的文本）
3. 手动添加角色标记，格式：[角色A]内容 [角色B]内容
4. 检查配置文件中的 API 密钥是否正确"""
                    
                    if verbose:
                        print(f"\n错误详情: {error_msg}")
                    
                    return None, error_msg, ""
                
                if progress:
                    progress(0.3, desc=f"已转换为{len(roles)}个角色的对话，开始生成音频...")
                    
            except Exception as e:
                error_msg = f"调用混元模型失败：{str(e)}\n\n💡 请检查：\n- 网络连接是否正常\n- 配置文件中的 API 密钥是否正确（hunyuan_podcast/config.py）\n- 或手动添加角色标记格式"
                if verbose:
                    import traceback
                    traceback.print_exc()
                return None, error_msg, ""
        
        # 构建角色音色映射（按角色顺序分配音色文件）
        role_voices = {}
        voice_files = [role_a_voice, role_b_voice, role_c_voice]
        
        for i, role in enumerate(roles):
            if i < len(voice_files) and voice_files[i]:
                role_voices[role] = voice_files[i]
        
        # 检查是否有足够的音色文件
        if len(role_voices) < len(roles):
            missing_roles = [r for r in roles if r not in role_voices]
            error_msg = f"""错误：以下角色缺少音色文件：{', '.join(missing_roles)}

检测到的角色：{', '.join(roles)}

解决方案：
- 请为每个角色上传对应的音色参考音频
- 角色顺序：第一个角色使用"角色A音色"，第二个角色使用"角色B音色"，以此类推
- 如果只有2个角色，只需上传角色A和角色B的音色即可
- 如果只有1个角色，只需上传角色A的音色即可
"""
            return None, error_msg, ""
        
        if progress:
            progress(0.4, desc=f"正在加载SoulX-Podcast模型...")
        
        # 现在才初始化生成器（延迟加载TTS模型）
        generator = init_generator()
        
        if progress:
            progress(0.5, desc=f"正在为 {len(roles)} 个角色生成播客音频...")
        
        # 生成播客
        try:
            output_path = generator.generate_from_text(
                text=text,
                role_voices=role_voices,
                silence_interval=silence_interval,
                background_music=background_music,
                background_volume=background_volume,
                background_mode=background_mode,
                verbose=True
            )
            
            if progress:
                progress(1.0, desc="生成完成！")
            
            # 确保输出路径是绝对路径
            abs_output_path = os.path.abspath(output_path)
            file_size = os.path.getsize(abs_output_path) / (1024 * 1024)  # MB
            
            success_msg = f"""播客生成成功！

统计信息：
- 角色数量：{len(roles)}
- 角色列表：{', '.join(roles)}
- 输出文件：{abs_output_path}
- 文件大小：{file_size:.2f} MB

提示：文件已保存，可以在WebUI中播放或下载"""
            
            return abs_output_path, success_msg, text
        except Exception as e:
            error_msg = f"生成失败：{str(e)}\n\n 请检查：\n- 音色文件是否正确上传\n- 文本格式是否正确\n- 网络连接是否正常"
            import traceback
            traceback.print_exc()
            return None, error_msg, ""
    
    except Exception as e:
        error_msg = f"生成失败：{str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return None, error_msg, ""


def generate_character_podcast(
    character_a_name: str,
    character_a_identity: str,
    character_a_personality: str,
    character_a_catchphrase: str,
    character_a_speaking_style: str,
    character_a_relationship: str,
    character_a_voice: Optional[str],
    character_b_name: str,
    character_b_identity: str,
    character_b_personality: str,
    character_b_catchphrase: str,
    character_b_speaking_style: str,
    character_b_relationship: str,
    character_b_voice: Optional[str],
    character_c_name: str,
    character_c_identity: str,
    character_c_personality: str,
    character_c_catchphrase: str,
    character_c_speaking_style: str,
    character_c_relationship: str,
    character_c_voice: Optional[str],
    topic: str,
    progress=None
) -> Tuple[str, str, str]:
    """
    生成自定义角色播客（子题目2）
    
    Args:
        character_a_name: 角色A名称
        character_a_identity: 角色A身份/职业
        character_a_personality: 角色A核心性格
        character_a_catchphrase: 角色A口头禅
        character_a_speaking_style: 角色A说话习惯
        character_a_relationship: 角色A与其他角色的关系
        character_a_voice: 角色A音色文件
        (character_b/c 参数类似)
        topic: 播客主题
        progress: Gradio进度条
    
    Returns:
        (输出音频路径, 状态信息, 生成的脚本文本)
    """
    try:
        generator = init_generator()
        
        # 构建详细角色人设描述
        character_descriptions = {}
        role_voices = {}
        
        characters = [
            (character_a_name, character_a_identity, character_a_personality, 
             character_a_catchphrase, character_a_speaking_style, character_a_relationship, character_a_voice),
            (character_b_name, character_b_identity, character_b_personality,
             character_b_catchphrase, character_b_speaking_style, character_b_relationship, character_b_voice),
            (character_c_name, character_c_identity, character_c_personality,
             character_c_catchphrase, character_c_speaking_style, character_c_relationship, character_c_voice),
        ]
        
        for name, identity, personality, catchphrase, speaking_style, relationship, voice in characters:
            if name and voice:
                # 构建详细人设字典
                char_desc = {
                    "identity": identity or "",
                    "personality": personality or "",
                    "catchphrase": catchphrase or "",
                    "speaking_style": speaking_style or "",
                    "relationship": relationship or ""
                }
                character_descriptions[name] = char_desc
                role_voices[name] = voice
        
        if len(character_descriptions) < 2:
            return None, "错误：至少需要设置2个角色的名称和音色", ""
        
        if progress:
            progress(0.2, desc="正在调用混元模型生成对话...")
        
        # 生成播客
        try:
            # 先调用API生成文本
            from .api_client import get_client
            api_client = get_client()
            processor = TextProcessor()
            
            prompt = processor.build_character_prompt(character_descriptions, topic if topic.strip() else None)
            
            if progress:
                progress(0.3, desc="正在调用混元模型生成对话文本...")
            
            generated_text = api_client.generate_text(
                prompt=prompt,
                temperature=0.8,
                max_tokens=2000  # 降低以加快生成速度
            )
            
            if progress:
                progress(0.5, desc="正在生成音频...")
            
            # 清理生成的文本
            cleaned_text = processor.clean_text(generated_text)
            
            # 从生成的文本生成音频
            output_path = generator.generate_from_text(
                text=cleaned_text,
                role_voices=role_voices,
                verbose=True
            )
            
            if progress:
                progress(1.0, desc="生成完成！")
            
            # 确保输出路径是绝对路径
            abs_output_path = os.path.abspath(output_path)
            file_size = os.path.getsize(abs_output_path) / (1024 * 1024)  # MB
            
            success_msg = f"""播客生成成功！

统计信息：
- 角色数量：{len(character_descriptions)}
- 输出文件：{abs_output_path}
- 文件大小：{file_size:.2f} MB

提示：文件已保存，可以在WebUI中播放或下载"""
            
            return abs_output_path, success_msg, cleaned_text
        except Exception as e:
            error_msg = f"生成失败：{str(e)}\n\n💡 请检查：\n- 音色文件是否正确上传\n- 角色信息是否完整\n- 网络连接是否正常"
            import traceback
            traceback.print_exc()
            return None, error_msg, ""
    
    except Exception as e:
        error_msg = f"生成失败：{str(e)}\n\n💡 请检查：\n- 音色文件是否正确上传\n- 角色信息是否完整\n- 网络连接是否正常"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return None, error_msg, ""


def generate_deep_podcast(
    topic: str,
    role_a_voice: Optional[str],
    role_b_voice: Optional[str],
    role_c_voice: Optional[str],
    num_characters: int = 2,
    depth_level: str = "深度",
    progress=None
) -> Tuple[str, str]:
    """
    生成主题深度播客（子题目3）
    
    Args:
        topic: 播客主题
        role_a_voice: 角色A音色文件
        role_b_voice: 角色B音色文件
        role_c_voice: 角色C音色文件
        num_characters: 角色数量
        depth_level: 深度级别
        progress: Gradio进度条
    
    Returns:
        (输出音频路径, 状态信息, 生成的脚本文本)
    """
    try:
        generator = init_generator()
        
        if not topic.strip():
            return None, "错误：请输入播客主题", ""
        
        # 构建角色音色映射
        role_voices = {}
        role_names = ["角色A", "角色B", "角色C"]
        voice_files = [role_a_voice, role_b_voice, role_c_voice]
        
        for i in range(min(num_characters, len(voice_files))):
            if voice_files[i]:
                role_voices[role_names[i]] = voice_files[i]
        
        if len(role_voices) < num_characters:
            return None, f"错误：需要为 {num_characters} 个角色上传音色文件", ""
        
        if progress:
            progress(0.2, desc="正在调用混元模型生成深度对话...")
        
        # 先调用API生成文本
        from .api_client import get_client
        api_client = get_client()
        processor = TextProcessor()
        
        prompt = processor.build_deep_podcast_prompt(topic, depth_level, num_characters)
        
        if progress:
            progress(0.3, desc="正在调用混元模型生成对话文本...")
        
        generated_text = api_client.generate_text(
            prompt=prompt,
            temperature=0.7,
            max_tokens=2500
        )
        
        if progress:
            progress(0.5, desc="正在生成音频...")
        
        # 清理生成的文本
        cleaned_text = processor.clean_text(generated_text)
        
        # 从生成的文本生成音频
        output_path = generator.generate_from_text(
            text=cleaned_text,
            role_voices=role_voices,
            verbose=True
        )
        
        if progress:
            progress(1.0, desc="生成完成！")
        
        # 确保输出路径是绝对路径
        abs_output_path = os.path.abspath(output_path)
        file_size = os.path.getsize(abs_output_path) / (1024 * 1024)  # MB
        
        success_msg = f"""播客生成成功！

统计信息：
- 主题：{topic}
- 角色数量：{num_characters}
- 深度级别：{depth_level}
- 输出文件：{abs_output_path}
- 文件大小：{file_size:.2f} MB

提示：文件已保存，可以在WebUI中播放或下载"""
        
        return abs_output_path, success_msg, cleaned_text
    
    except Exception as e:
        error_msg = f"生成失败：{str(e)}\n\n💡 请检查：\n- 音色文件是否正确上传\n- 主题是否输入\n- 网络连接是否正常"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return None, error_msg, ""


def create_webui():
    """创建WebUI界面"""
    # 检查 gradio 是否安装
    try:
        import gradio as gr
    except ImportError:
        print("错误：未安装 gradio")
        print("\n解决方案：")
        print("   pip install gradio")
        sys.exit(1)
    
    parser = argparse.ArgumentParser(description="混元AI播客生成系统")
    parser.add_argument("--port", type=int, default=7861, help="WebUI端口")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="WebUI主机")
    parser.add_argument("--fp16-flow", action="store_true", dest="fp16_flow", help="使用FP16精度（Flow模型）")
    parser.add_argument("--no-fp16-flow", action="store_true", dest="no_fp16_flow", help="禁用FP16精度（Flow模型）")
    parser.add_argument("--llm-engine", type=str, default=None, choices=["hf", "vllm"], help="LLM引擎类型 (hf 或 vllm)")
    parser.add_argument("--device", type=str, default=None, help="设备类型 (如 'cuda:0', 'cuda', 'cpu')，如果未指定则自动检测GPU")
    args = parser.parse_args()
    
    # 设备检测和配置
    import torch
    device = args.device
    has_gpu = False
    if device is None:
        # 自动检测GPU
        if torch.cuda.is_available():
            device = "cuda:0"
            has_gpu = True
            print(f"🚀 检测到GPU可用，将使用设备: {device}")
            if torch.cuda.device_count() > 1:
                print(f"   检测到 {torch.cuda.device_count()} 个GPU设备")
            print(f"   GPU名称: {torch.cuda.get_device_name(0)}")
        else:
            device = None
            print("⚠️  未检测到GPU，SoulX-Podcast需要GPU支持")
            print("   ⚠️  请确保已安装CUDA和PyTorch GPU版本")
    else:
        print(f"🎯 使用指定设备: {device}")
        if device.startswith("cuda"):
            if torch.cuda.is_available():
                has_gpu = True
            else:
                print(f"⚠️  警告：指定了CUDA设备，但CUDA不可用，将回退到CPU模式")
                device = None
    
    # 配置LLM引擎和FP16 Flow
    llm_engine = args.llm_engine if args.llm_engine else None
    fp16_flow = None
    
    if has_gpu:
        # 自动启用fp16_flow（除非用户明确禁用）
        if args.no_fp16_flow:
            fp16_flow = False
            print("   ⚠️  已禁用FP16 Flow（用户指定）")
        else:
            fp16_flow = args.fp16_flow or True  # 如果用户指定了--fp16-flow则使用，否则自动启用
            if args.fp16_flow:
                print("   ✅ 已启用FP16 Flow（用户指定）")
            else:
                print("   ✅ 已自动启用FP16 Flow（检测到GPU）")
    else:
        # CPU模式，不使用GPU优化
        fp16_flow = False
        if args.fp16_flow:
            print("⚠️  警告: CPU模式不支持FP16 Flow，将忽略 --fp16-flow 参数")
    
    # 检查模型文件（使用绝对路径）
    model_dir = os.path.abspath(SOULX_PODCAST_MODEL_DIR)
    
    if not os.path.exists(model_dir):
        print(f"警告：模型目录不存在 {model_dir}")
        print(f"   请检查路径是否正确，或设置环境变量 SOULX_PODCAST_MODEL_DIR")
        print(f"   模型下载方法：")
        print(f"   cd SoulX-Podcast")
        print(f"   huggingface-cli download --resume-download Soul-AILab/SoulX-Podcast-1.7B --local-dir pretrained_models/SoulX-Podcast-1.7B")
    
    # 更新args中的device，以便后续使用
    args.device = device
    
    # 设置全局生成器配置
    set_generator_config(
        llm_engine=llm_engine,
        fp16_flow=fp16_flow,
        device=device
    )
    
    # 现代化CSS样式
    custom_css = """
    /* 全局样式 */
    .gradio-container {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
        background: #ffffff;
        min-height: 100vh;
    }
    
    /* 主容器 */
    .main-container {
        max-width: 1400px;
        margin: 0 auto;
        padding: 20px;
    }
    
    /* 标题区域 */
    .header-section {
        background: white;
        border-radius: 16px;
        padding: 30px;
        margin-bottom: 24px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        text-align: center;
    }
    
    .header-section h1 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5em;
        font-weight: 700;
        margin: 0;
    }
    
    .header-section p {
        color: #666;
        font-size: 1.1em;
        margin: 10px 0;
    }
    
    /* 标签页样式 */
    .tab-nav {
        background: white;
        border-radius: 12px;
        padding: 8px;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    /* 输入区域 */
    .input-section {
        background: white;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    /* 输出区域 */
    .output-section {
        background: white;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    /* 按钮样式 */
    button.primary {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        font-size: 1em;
        font-weight: 600;
        cursor: pointer;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    
    button.primary:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(102, 126, 234, 0.4);
    }
    
    /* 脚本显示区域 */
    .script-display {
        background: #ffffff;
        border-radius: 12px;
        padding: 24px;
        max-height: 600px;
        overflow-y: auto;
        border: 1px solid #e9ecef;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    /* 音频播放器 */
    .audio-player {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 20px;
        margin: 20px 0;
        border: 1px solid #e9ecef;
    }
    
    /* 状态信息 */
    .status-info {
        background: linear-gradient(135deg, #e7f3ff 0%, #f0f8ff 100%);
        border-left: 4px solid #667eea;
        padding: 16px;
        border-radius: 8px;
        margin: 12px 0;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    /* 输出区域组 */
    .output-group {
        background: #ffffff;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        border: 1px solid #f0f0f0;
    }
    
    /* 输入区域 */
    .input-group {
        background: #ffffff;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
        border: 1px solid #e9ecef;
    }
    
    /* 标签页内容 */
    .tab-content {
        background: #fafafa;
        padding: 24px;
        border-radius: 12px;
        margin-top: 16px;
    }
    
    /* 文本框样式 */
    textarea {
        border-radius: 8px !important;
        border: 1px solid #e0e0e0 !important;
        padding: 12px !important;
    }
    
    textarea:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1) !important;
    }
    
    /* 音频组件样式 */
    .audio-container {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 20px;
        border: 2px dashed #d0d0d0;
        margin: 16px 0;
        transition: all 0.3s ease;
    }
    
    .audio-container:hover {
        border-color: #667eea;
        background: #f0f4ff;
    }
    
    /* 滑块样式 */
    input[type="range"] {
        accent-color: #667eea;
    }
    
    /* Markdown内容样式 */
    .markdown-content {
        background: #ffffff;
        padding: 20px;
        border-radius: 8px;
        line-height: 1.8;
        color: #333;
    }
    
    .markdown-content h3 {
        color: #667eea;
        margin-top: 24px;
        margin-bottom: 16px;
        font-size: 1.3em;
    }
    
    .markdown-content code {
        background: #f4f4f4;
        padding: 2px 6px;
        border-radius: 4px;
        font-family: 'Courier New', monospace;
        color: #e83e8c;
    }
    
    .markdown-content pre {
        background: #f8f9fa;
        padding: 16px;
        border-radius: 8px;
        overflow-x: auto;
        border: 1px solid #e9ecef;
    }
    
    /* 脚本内容样式 */
    .script-content {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        line-height: 1.8;
        color: #333;
    }
    
    .script-content .role-tag {
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 4px;
        margin-right: 8px;
    }
    
    /* 空状态提示 */
    .empty-state {
        text-align: center;
        padding: 40px 20px;
        color: #999;
        font-size: 0.95em;
    }
    
    /* 成功提示 */
    .success-message {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        border-left: 4px solid #28a745;
        padding: 12px 16px;
        border-radius: 6px;
        color: #155724;
        margin: 12px 0;
    }
    
    /* 错误提示 */
    .error-message {
        background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
        border-left: 4px solid #dc3545;
        padding: 12px 16px;
        border-radius: 6px;
        color: #721c24;
        margin: 12px 0;
    }
    """
    
    with gr.Blocks(title="混元AI播客生成系统", theme=gr.themes.Soft(), css=custom_css) as demo:
        gr.HTML('''
        <div class="header-section">
            <h1>🎙️ 混元AI播客生成系统</h1>
            <p style="font-size: 1.2em; color: #667eea; font-weight: 600;">基于混元大模型和SoulX-Podcast的智能播客音频生成工具</p>
            <p style="color: #888;">支持多角色互动、自定义角色人设、主题深度播客生成</p>
            <div style="margin-top: 20px;">
                <span style="background: #667eea; color: white; padding: 6px 12px; border-radius: 20px; margin: 0 8px; display: inline-block;">
                    ✨ 多角色互动
                </span>
                <span style="background: #764ba2; color: white; padding: 6px 12px; border-radius: 20px; margin: 0 8px; display: inline-block;">
                    🎭 自定义角色
                </span>
                <span style="background: #f093fb; color: white; padding: 6px 12px; border-radius: 20px; margin: 0 8px; display: inline-block;">
                    🧠 深度思考
                </span>
            </div>
        </div>
        ''')
        
        gr.Markdown("---")
        
        # 标签页1：多角色互动播客
        with gr.Tab("多角色互动播客", id="multi_role"):
            with gr.Accordion("📖 使用说明", open=False):
                gr.Markdown("""
                ### 子题目1：将文本素材转化为多角色自然互动的播客音频
                
                输入包含角色标记的文本，系统将自动识别角色并生成对应的播客音频。
                
                **文本格式要求：**
                - 使用 `[角色名]` 格式标记每个角色的发言
                - 角色名可以是任意名称，如 `[角色A]`、`[主持人]`、`[嘉宾]` 等
                - 支持多行文本，每行可以包含多个角色的对话
                
                **示例格式：**
                ```
                [角色A]大家好，欢迎收听今天的播客。
                [角色B]是的，今天我们要聊一个很有趣的话题。
                [角色A]没错，让我们开始吧！
                ```
                
                **使用步骤：**
                1. 在文本框中输入文本（普通文本或带角色标记的文本）
                2. 为每个角色上传或录制音色参考音频（至少2个，按角色顺序：第一个角色→角色A音色，第二个角色→角色B音色）
                   - 可以上传音频文件
                   - 也可以点击麦克风图标直接录制（需要浏览器授权麦克风权限）
                3. 点击"生成播客"按钮
                4. 如果是普通文本，系统会自动转换为多角色对话
                
                **录制音频提示：**
                - 录制时请保持环境安静，说话清晰
                - 建议录制3-10秒的音频
                - 录制完成后可以播放预览，确认无误后再生成播客
                """)
            
            with gr.Row():
                with gr.Column(scale=1):
                    input_text = gr.Textbox(
                        label="📝 播客文本",
                        placeholder="例如：\n中科曙光发布640卡超节点，算力密度提升20倍。在2025世界互联网大会乌镇峰会上，中科曙光正式发布全球首款单机柜级640卡超节点scaleX640。\n\n或者手动标记：\n[角色A]大家好，欢迎收听今天的播客。\n[角色B]是的，今天我们要聊一个很有趣的话题。",
                        lines=12,
                        value="中科曙光发布640卡超节点，算力密度提升20倍。在2025世界互联网大会乌镇峰会上，中科曙光正式发布全球首款单机柜级640卡超节点scaleX640。这款基于开放系统硬件架构打造的产品，采用一拖二高密架构设计，实现单机柜内640张加速卡的超高速互连，算力密度较同类产品提升20倍。",
                        info="💡 提示：可以直接输入普通文本，系统会自动调用混元大模型转换为多角色互动对话。也可以手动使用[角色名]格式标记角色。",
                        elem_classes=["input-group"]
                    )
                    
                    # 自动分析按钮
                    analyze_button = gr.Button(
                        "🤖 自动分析文本",
                        variant="secondary",
                        size="sm"
                    )
                    analyze_status = gr.Textbox(
                        label="分析状态",
                        lines=1,
                        interactive=False,
                        visible=False
                    )
                    
                    # 高级设置（折叠面板）
                    with gr.Accordion("⚙️ 高级设置（可选）", open=False):
                        podcast_name = gr.Textbox(
                            label="播客名称",
                            placeholder="例如：科技前沿、商业观察",
                            info="留空则自动推断",
                            lines=1
                        )
                        topic = gr.Textbox(
                            label="本期主题",
                            placeholder="例如：AI技术的发展",
                            info="留空则自动推断",
                            lines=1
                        )
                        
                        scene_types = gr.CheckboxGroup(
                            label="互动场景类型",
                            choices=[
                                "接梗玩梗的轻松交流",
                                "立场冲突的激烈辩论",
                                "愉快合作的访谈对话",
                                "不愉快的质疑访谈"
                            ],
                            info="可选择多种场景类型，留空则自动推断",
                            value=[]
                        )
                        
                        gr.Markdown("### 👤 角色设定（可选）")
                        with gr.Row():
                            with gr.Column():
                                character_1_name = gr.Textbox(
                                    label="角色1名称",
                                    placeholder="例如：主持人",
                                    lines=1
                                )
                                character_1_personality = gr.Textbox(
                                    label="性格特点",
                                    placeholder="例如：外向幽默、喜欢开玩笑",
                                    lines=1
                                )
                                character_1_speaking_style = gr.Textbox(
                                    label="说话风格",
                                    placeholder="例如：语速较快，常用网络流行语",
                                    lines=1
                                )
                            with gr.Column():
                                character_2_name = gr.Textbox(
                                    label="角色2名称",
                                    placeholder="例如：专家",
                                    lines=1
                                )
                                character_2_personality = gr.Textbox(
                                    label="性格特点",
                                    placeholder="例如：理性严谨、善于分析",
                                    lines=1
                                )
                                character_2_speaking_style = gr.Textbox(
                                    label="说话风格",
                                    placeholder="例如：语速平稳，逻辑性强",
                                    lines=1
                                )
                            with gr.Column():
                                character_3_name = gr.Textbox(
                                    label="角色3名称（可选）",
                                    placeholder="例如：嘉宾",
                                    lines=1
                                )
                                character_3_personality = gr.Textbox(
                                    label="性格特点",
                                    placeholder="例如：温和中立、善于调解",
                                    lines=1
                                )
                                character_3_speaking_style = gr.Textbox(
                                    label="说话风格",
                                    placeholder="例如：语气柔和，常用提问引导话题",
                                    lines=1
                    )
                    
                    gr.Markdown("### 🎤 角色音色设置")
                    with gr.Row():
                        role_a_voice = gr.Audio(
                            label="🎙️ 角色A音色",
                            sources=["upload", "microphone"],
                            type="filepath",
                            elem_classes=["audio-container"]
                        )
                        role_b_voice = gr.Audio(
                            label="🎙️ 角色B音色",
                            sources=["upload", "microphone"],
                            type="filepath",
                            elem_classes=["audio-container"]
                        )
                    with gr.Row():
                        role_c_voice = gr.Audio(
                            label="🎙️ 角色C音色（可选）",
                            sources=["upload", "microphone"],
                            type="filepath",
                            elem_classes=["audio-container"]
                        )
                    
                    silence_interval = gr.Slider(
                        label="⏱️ 角色切换静音间隔（毫秒）",
                        minimum=200,
                        maximum=1500,
                        value=600,
                        step=50,
                        info="调整角色之间的静音间隔，建议范围：400-800毫秒。较大的间隔可以让对话更清晰，节奏更舒缓。"
                    )
                    
                    # 音效设置（折叠面板）
                    with gr.Accordion("🎵 背景音乐设置（可选）", open=False):
                        gr.Markdown("""
                        **💡 智能背景音乐功能：**
                        - ✅ **自动Ducking效果**：角色说话时，背景音乐音量自动降低，确保对话清晰
                        - ✅ **AI自动匹配**：系统会根据播客内容自动选择最合适的背景音乐
                        - ✅ **手动上传**：也可以手动上传自定义背景音乐
                        """)
                        
                        auto_select_music = gr.Checkbox(
                            label="🤖 AI自动选择背景音乐",
                            value=True,
                            info="启用后，系统会根据播客内容、主题和场景类型，从音乐库中自动选择最合适的背景音乐"
                        )
                        
                        background_music = gr.File(
                            label="🎵 手动上传背景音乐（可多选，仅在AI自动选择关闭时生效）",
                            file_count="multiple",
                            file_types=[".wav", ".mp3", ".m4a", ".flac"],
                            info="如果关闭AI自动选择，可以手动上传背景音乐文件。可以上传多个文件，系统会根据下方模式处理。",
                            elem_classes=["audio-container"]
                        )
                        
                        background_mode = gr.Radio(
                            label="🎛️ 背景音乐处理模式（仅手动上传多个文件时生效）",
                            choices=[
                                ("随机选择", "random"),
                                ("顺序拼接", "concat"),
                                ("混合播放", "mix")
                            ],
                            value="random",
                            info="当手动上传多个背景音乐时：随机选择 = 随机选一个；顺序拼接 = 按顺序播放；混合播放 = 混合所有音乐"
                        )
                        
                        background_volume = gr.Slider(
                            label="🔊 背景音乐基础音量",
                            minimum=0.0,
                            maximum=1.0,
                            value=0.3,
                            step=0.1,
                            info="背景音乐的基础音量（0.0-1.0）。角色说话时，系统会自动降低音量（ducking效果）。建议范围：0.2-0.4"
                        )
                    
                    gen_button_1 = gr.Button(
                        "🚀 生成播客",
                        variant="primary",
                        size="lg",
                        scale=1
                    )
                
                with gr.Column(scale=1):
                    with gr.Group():
                        gr.Markdown("### 📻 生成的播客")
                        output_audio_1 = gr.Audio(
                            label="播客音频",
                            elem_classes=["audio-player"]
                        )
                        status_text_1 = gr.Textbox(
                            label="状态信息",
                            lines=4,
                            interactive=False,
                            elem_classes=["status-info"],
                            placeholder="等待生成..."
                        )
                    
                    with gr.Group():
                        gr.Markdown("### 📝 播客脚本")
                        script_display_1 = gr.HTML(
                            label="脚本内容",
                            value='''
                            <div class="empty-state">
                                <p style="color: #999; font-size: 0.95em; margin: 0;">
                                    📄 生成的脚本将显示在这里<br>
                                    <span style="font-size: 0.85em; color: #bbb;">等待生成播客后，脚本内容会自动显示</span>
                                </p>
                            </div>
                            ''',
                            elem_classes=["script-display"]
                        )
            
            # 自动分析按钮事件
            analyze_button.click(
                fn=analyze_text_for_podcast_ui,
                inputs=[input_text],
                outputs=[
                    podcast_name,
                    topic,
                    character_1_name,
                    character_1_personality,
                    character_1_speaking_style,
                    character_2_name,
                    character_2_personality,
                    character_2_speaking_style,
                    character_3_name,
                    character_3_personality,
                    character_3_speaking_style,
                    scene_types
                ]
            )
            
            # 生成按钮事件
            gen_button_1.click(
                fn=wrap_multi_role_podcast,
                inputs=[
                    input_text,
                    role_a_voice,
                    role_b_voice,
                    role_c_voice,
                    silence_interval,
                    podcast_name,
                    topic,
                    character_1_name,
                    character_1_personality,
                    character_1_speaking_style,
                    character_2_name,
                    character_2_personality,
                    character_2_speaking_style,
                    character_3_name,
                    character_3_personality,
                    character_3_speaking_style,
                    scene_types,
                    auto_select_music,
                    background_music,
                    background_volume,
                    background_mode
                ],
                outputs=[output_audio_1, status_text_1, script_display_1]
            )
        
        # 标签页2：自定义角色播客
        with gr.Tab("自定义角色播客", id="character"):
            with gr.Accordion("📖 使用说明", open=False):
                gr.Markdown("""
                ### 子题目2：根据用户自定义的角色人设和音色生成契合风格的播客音频
                
                为每个角色设置人设描述和音色，系统将根据角色人设生成符合风格的播客对话。
                
                **使用说明：**
                - 为每个角色设置名称、人设描述和音色文件
                - 音色文件可以上传或直接录制（点击麦克风图标）
                - 输入播客主题（可选）
                - 系统会根据角色人设生成符合风格的对话
                
                **录制音频提示：**
                - 录制时请保持环境安静，说话清晰
                - 建议录制3-10秒的音频，包含角色的典型说话风格
                - 录制完成后可以播放预览，确认无误后再生成播客
                """)
            
            with gr.Row():
                with gr.Column(scale=1):
                    with gr.Group():
                        gr.Markdown("### 👤 角色A设置")
                        character_a_name = gr.Textbox(
                            label="角色A名称",
                            value="角色A",
                            placeholder="例如：托尼老师",
                            info="为角色设置一个易于识别的名称"
                        )
                        character_a_identity = gr.Textbox(
                            label="身份/职业",
                            placeholder="例如：时尚潮人、理发店总监",
                            lines=1,
                            info="描述角色的职业或身份"
                        )
                        character_a_personality = gr.Textbox(
                            label="核心性格",
                            placeholder="例如：自信略带浮夸、热心肠",
                            lines=2,
                            info="描述角色的性格特点"
                        )
                        character_a_catchphrase = gr.Textbox(
                            label="口头禅/说话习惯",
                            placeholder="例如：喜欢用夸张的赞美和比喻，语速快，充满激情，常夹杂英文单词和网络流行语",
                            lines=2,
                            info="描述角色的说话习惯和口头禅"
                        )
                        character_a_speaking_style = gr.Textbox(
                            label="说话风格",
                            placeholder="例如：清亮有穿透力的声音，语调起伏大，常带笑意",
                            lines=2,
                            info="描述角色的声音特点和说话风格"
                        )
                        character_a_relationship = gr.Textbox(
                            label="与其他角色的关系",
                            placeholder="例如：与角色B是好友，经常互怼",
                            lines=1,
                            info="描述角色与其他角色的关系"
                        )
                        character_a_voice = gr.Audio(
                            label="🎙️ 角色A音色",
                            sources=["upload", "microphone"],
                            type="filepath",
                            elem_classes=["audio-container"]
                        )
                    
                    with gr.Group():
                        gr.Markdown("### 👤 角色B设置")
                        character_b_name = gr.Textbox(
                            label="角色B名称",
                            value="角色B",
                            placeholder="例如：程序员阿哲",
                            info="为角色设置一个易于识别的名称"
                        )
                        character_b_identity = gr.Textbox(
                            label="身份/职业",
                            placeholder="例如：资深后端工程师",
                            lines=1,
                            info="描述角色的职业或身份"
                        )
                        character_b_personality = gr.Textbox(
                            label="核心性格",
                            placeholder="例如：逻辑控、内向务实、轻微社恐",
                            lines=2,
                            info="描述角色的性格特点"
                        )
                        character_b_catchphrase = gr.Textbox(
                            label="口头禅/说话习惯",
                            placeholder="例如：语速平缓，用词精准，喜欢用'从技术实现上讲...'、'这个需求不明确'等句式",
                            lines=2,
                            info="描述角色的说话习惯和口头禅"
                        )
                        character_b_speaking_style = gr.Textbox(
                            label="说话风格",
                            placeholder="例如：低沉温和的声音，语调平稳，偶尔有思考时的停顿",
                            lines=2,
                            info="描述角色的声音特点和说话风格"
                        )
                        character_b_relationship = gr.Textbox(
                            label="与其他角色的关系",
                            placeholder="例如：与角色A是好友，经常被角色A的热情感染",
                            lines=1,
                            info="描述角色与其他角色的关系"
                        )
                        character_b_voice = gr.Audio(
                            label="🎙️ 角色B音色",
                            sources=["upload", "microphone"],
                            type="filepath",
                            elem_classes=["audio-container"]
                        )
                    
                    with gr.Group():
                        gr.Markdown("### 👤 角色C设置（可选）")
                        character_c_name = gr.Textbox(
                            label="角色C名称",
                            value="角色C",
                            placeholder="例如：小刚",
                            info="为角色设置一个易于识别的名称（可选）"
                        )
                        character_c_identity = gr.Textbox(
                            label="身份/职业",
                            placeholder="例如：年轻的听众",
                            lines=1,
                            info="描述角色的职业或身份（可选）"
                        )
                        character_c_personality = gr.Textbox(
                            label="核心性格",
                            placeholder="例如：充满好奇心，经常提问",
                            lines=2,
                            info="描述角色的性格特点（可选）"
                        )
                        character_c_catchphrase = gr.Textbox(
                            label="口头禅/说话习惯",
                            placeholder="例如：经常问'为什么'、'真的吗'等",
                            lines=2,
                            info="描述角色的说话习惯和口头禅（可选）"
                        )
                        character_c_speaking_style = gr.Textbox(
                            label="说话风格",
                            placeholder="例如：年轻活泼的声音，语速较快",
                            lines=2,
                            info="描述角色的声音特点和说话风格（可选）"
                        )
                        character_c_relationship = gr.Textbox(
                            label="与其他角色的关系",
                            placeholder="例如：是角色A和角色B的听众",
                            lines=1,
                            info="描述角色与其他角色的关系（可选）"
                        )
                        character_c_voice = gr.Audio(
                            label="🎙️ 角色C音色（可选）",
                            sources=["upload", "microphone"],
                            type="filepath",
                            elem_classes=["audio-container"]
                        )
                    
                    topic_input = gr.Textbox(
                        label="📋 播客主题（可选）",
                        placeholder="例如：人工智能的发展与未来",
                        info="如果留空，系统将根据角色人设自由生成对话",
                        lines=2
                    )
                    
                    gen_button_2 = gr.Button(
                        "🚀 生成播客",
                        variant="primary",
                        size="lg"
                    )
                
                with gr.Column(scale=1):
                    with gr.Group():
                        gr.Markdown("### 📻 生成的播客")
                        output_audio_2 = gr.Audio(
                            label="播客音频",
                            elem_classes=["audio-player"]
                        )
                        status_text_2 = gr.Textbox(
                            label="状态信息",
                            lines=4,
                            interactive=False,
                            elem_classes=["status-info"],
                            placeholder="等待生成..."
                        )
                    
                    with gr.Group():
                        gr.Markdown("### 📝 播客脚本")
                        script_display_2 = gr.HTML(
                            label="脚本内容",
                            value='''
                            <div class="empty-state">
                                <p style="color: #999; font-size: 0.95em; margin: 0;">
                                    📄 生成的脚本将显示在这里<br>
                                    <span style="font-size: 0.85em; color: #bbb;">等待生成播客后，脚本内容会自动显示</span>
                                </p>
                            </div>
                            ''',
                            elem_classes=["script-display"]
                        )
            
            gen_button_2.click(
                fn=wrap_character_podcast,
                inputs=[
                    character_a_name, character_a_identity, character_a_personality,
                    character_a_catchphrase, character_a_speaking_style, character_a_relationship, character_a_voice,
                    character_b_name, character_b_identity, character_b_personality,
                    character_b_catchphrase, character_b_speaking_style, character_b_relationship, character_b_voice,
                    character_c_name, character_c_identity, character_c_personality,
                    character_c_catchphrase, character_c_speaking_style, character_c_relationship, character_c_voice,
                    topic_input
                ],
                outputs=[output_audio_2, status_text_2, script_display_2]
            )
        
        # 标签页3：主题深度播客
        with gr.Tab("主题深度播客", id="deep"):
            with gr.Accordion("📖 使用说明", open=False):
                gr.Markdown("""
                ### 子题目3：基于指定主题生成有深度、引发思考的播客音频
                
                输入一个主题，系统将生成有深度、有见地的播客对话，能够引发听众的深度思考。
                
                **使用说明：**
                - 输入播客主题
                - 为每个角色上传或录制音色文件（点击麦克风图标可录制）
                - 选择角色数量和深度级别
                - 系统将生成围绕主题的深度对话
                
                **录制音频提示：**
                - 录制时请保持环境安静，说话清晰
                - 建议录制3-10秒的音频
                - 录制完成后可以播放预览，确认无误后再生成播客
                """)
            
            with gr.Row():
                with gr.Column(scale=1):
                    topic_deep = gr.Textbox(
                        label="📋 播客主题",
                        placeholder="例如：人工智能对人类社会的影响",
                        lines=3,
                        info="输入您想要讨论的主题，系统将生成有深度、有见地的播客对话"
                    )
                    
                    with gr.Row():
                        num_characters = gr.Slider(
                            label="👥 角色数量",
                            minimum=2,
                            maximum=3,
                            value=2,
                            step=1,
                            info="选择参与播客的角色数量（2-3个）"
                        )
                        
                        depth_level = gr.Radio(
                            label="🧠 深度级别",
                            choices=["深度", "中等", "浅层"],
                            value="深度",
                            info="选择内容的深度级别"
                        )
                    
                    gr.Markdown("### 🎤 角色音色设置")
                    with gr.Row():
                        role_a_voice_deep = gr.Audio(
                            label="🎙️ 角色A音色",
                            sources=["upload", "microphone"],
                            type="filepath",
                            elem_classes=["audio-container"]
                        )
                        role_b_voice_deep = gr.Audio(
                            label="🎙️ 角色B音色",
                            sources=["upload", "microphone"],
                            type="filepath",
                            elem_classes=["audio-container"]
                        )
                    with gr.Row():
                        role_c_voice_deep = gr.Audio(
                            label="🎙️ 角色C音色（可选）",
                            sources=["upload", "microphone"],
                            type="filepath",
                            elem_classes=["audio-container"]
                        )
                    
                    gen_button_3 = gr.Button(
                        "🚀 生成播客",
                        variant="primary",
                        size="lg"
                    )
                
                with gr.Column(scale=1):
                    with gr.Group():
                        gr.Markdown("### 📻 生成的播客")
                        output_audio_3 = gr.Audio(
                            label="播客音频",
                            elem_classes=["audio-player"]
                        )
                        status_text_3 = gr.Textbox(
                            label="状态信息",
                            lines=4,
                            interactive=False,
                            elem_classes=["status-info"],
                            placeholder="等待生成..."
                        )
                    
                    with gr.Group():
                        gr.Markdown("### 📝 播客脚本")
                        script_display_3 = gr.HTML(
                            label="脚本内容",
                            value='''
                            <div class="empty-state">
                                <p style="color: #999; font-size: 0.95em; margin: 0;">
                                    📄 生成的脚本将显示在这里<br>
                                    <span style="font-size: 0.85em; color: #bbb;">等待生成播客后，脚本内容会自动显示</span>
                                </p>
                            </div>
                            ''',
                            elem_classes=["script-display"]
                        )
            
            gen_button_3.click(
                fn=wrap_deep_podcast,
                inputs=[
                    topic_deep,
                    role_a_voice_deep,
                    role_b_voice_deep,
                    role_c_voice_deep,
                    num_characters,
                    depth_level
                ],
                outputs=[output_audio_3, status_text_3, script_display_3]
            )
        
        # 页脚
        gr.HTML('''
        <div style="text-align: center; margin-top: 40px; padding: 24px; background: #f8f9fa; border-radius: 12px; border-top: 1px solid #e9ecef;">
            <p style="color: #666; margin: 8px 0; font-size: 0.95em;">
                <strong>混元AI播客生成系统</strong> | 基于混元大模型和SoulX-Podcast
            </p>
            <p style="color: #999; margin: 4px 0; font-size: 0.85em;">
                支持多角色互动、自定义角色人设、主题深度播客生成
            </p>
            <div style="margin-top: 12px;">
                <a href="http://localhost:8000/docs" target="_blank" style="color: #667eea; text-decoration: none; margin: 0 12px; font-size: 0.9em;">
                    📚 API文档
                </a>
                <span style="color: #ddd;">|</span>
                <a href="http://localhost:8000/health" target="_blank" style="color: #667eea; text-decoration: none; margin: 0 12px; font-size: 0.9em;">
                    💚 健康检查
                </a>
            </div>
        </div>
        ''')
    
    return demo, args


if __name__ == "__main__":
    from .config import OUTPUT_DIR
    
    demo, args = create_webui()
    demo.queue(10)
    
    # 添加输出目录到允许的路径列表
    output_dir_abs = os.path.abspath(OUTPUT_DIR)
    demo.launch(
        server_name=args.host,
        server_port=args.port,
        share=False,
        allowed_paths=[output_dir_abs]
    )

