"""
批量更新旧播客的封面图

功能：
1. 从云数据库查询所有没有封面图的播客
2. 为每个播客生成封面图
3. 上传封面图到云存储
4. 更新数据库中的 cover_image_url 字段

使用方法：
    python -m hunyuan_podcast.batch_update_cover_images

或者：
    python hunyuan_podcast/batch_update_cover_images.py
"""

import os
import sys
import json
import time
import logging
import base64
from typing import List, Dict, Any, Optional
from pathlib import Path
from io import BytesIO
from PIL import Image

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from hunyuan_podcast.agc_database import get_database_client
from hunyuan_podcast.api_client import get_client
from hunyuan_podcast.upload_client import upload_generated_podcast, get_agc_token, _find_agc_client_json, _load_agc_credentials_from_file
from hunyuan_podcast.config import OUTPUT_DIR
from hunyuan_podcast.log_config import setup_logging

# 配置日志
setup_logging(log_file="batch_update_cover_images.log")
logger = logging.getLogger(__name__)

# 进度记录文件
PROGRESS_FILE = os.path.join(OUTPUT_DIR, "cover_update_progress.json")


def load_progress() -> Dict[str, Any]:
    """加载进度记录"""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"加载进度文件失败: {e}")
    return {
        "processed_ids": [],
        "failed_ids": [],
        "last_update_time": None
    }


def save_progress(progress: Dict[str, Any]):
    """保存进度记录"""
    try:
        progress["last_update_time"] = time.time()
        with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存进度文件失败: {e}")


def generate_cover_image(
    podcast_id: str,
    podcast_title: str,
    text_content: Optional[str],
    topic: Optional[str],
    category: Optional[str],
    roles: Optional[List[str]]
) -> Optional[str]:
    """
    生成播客封面图
    
    Args:
        podcast_id: 播客ID
        podcast_title: 播客标题
        text_content: 播客文本内容
        topic: 播客主题
        category: 播客分类
        roles: 角色列表
    
    Returns:
        封面图URL（base64或云存储URL），失败返回None
    """
    try:
        import requests
        
        api_client = get_client()
        
        # 收集所有可用信息
        info_parts = []
        if podcast_title:
            info_parts.append(f"播客名称：{podcast_title}")
        if topic:
            info_parts.append(f"主题：{topic}")
        if category:
            info_parts.append(f"分类：{category}")
        if roles:
            info_parts.append(f"角色：{', '.join(roles)}")
        if text_content:
            # 截取文本前200字作为内容摘要
            text_summary = text_content[:200] + "..." if len(text_content) > 200 else text_content
            info_parts.append(f"内容摘要：{text_summary}")
        
        info_text = "\n".join(info_parts) if info_parts else "播客内容"
        
        # 使用混元大模型生成图像提示词
        prompt_generation_prompt = f"""根据以下播客信息，生成一个简洁、吸引人的英文图像生成提示词（prompt），用于生成播客封面图。

播客信息：
{info_text}

要求：
1. 提示词应该是英文，简洁明了（不超过50个单词）
2. 应该包含播客的主题、风格和氛围
3. 适合作为播客封面图，具有视觉吸引力
4. 风格应该是现代、专业、简洁
5. 只返回提示词，不要其他解释

图像生成提示词："""

        logger.info(f"[{podcast_id}] 开始生成封面图提示词...")
        
        try:
            image_prompt = api_client.generate_text(
                prompt=prompt_generation_prompt,
                temperature=0.7,
                max_tokens=200
            ).strip()
            
            # 清理提示词（移除可能的引号或多余内容）
            image_prompt = image_prompt.strip('"').strip("'").strip()
            
            logger.info(f"[{podcast_id}] 生成的图像提示词: {image_prompt}")
        except Exception as e:
            logger.warning(f"[{podcast_id}] 使用混元模型生成提示词失败，使用默认提示词: {e}")
            # 如果生成失败，使用默认提示词
            if topic:
                image_prompt = f"Podcast cover art, {topic}, modern, professional, minimalist design, vibrant colors"
            elif podcast_title:
                image_prompt = f"Podcast cover art, {podcast_title}, modern, professional, minimalist design"
            else:
                image_prompt = "Podcast cover art, modern, professional, minimalist design, vibrant colors"
        
        # 使用SiliconFlow的图像生成API
        siliconflow_api_key = os.getenv("SILICONFLOW_API_KEY", "sk-tpoapasxdwjyexqfagbiigtvwsoydwravbptrmrrmwjfdwbh")
        siliconflow_api_base = "https://api.siliconflow.cn/v1"
        
        if not siliconflow_api_key:
            logger.warning(f"[{podcast_id}] 未配置SILICONFLOW_API_KEY，返回占位图")
            # 创建一个简单的占位图
            img = Image.new('RGB', (512, 512), color=(73, 109, 137))
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            return f"data:image/png;base64,{img_base64}"
        
        # 调用SiliconFlow的图像生成API
        try:
            headers = {
                "Authorization": f"Bearer {siliconflow_api_key}",
                "Content-Type": "application/json"
            }
            
            # 使用Stable Diffusion模型
            payload = {
                "model": "stabilityai/stable-diffusion-xl-base-1.0",
                "prompt": image_prompt,
                "negative_prompt": "blurry, low quality, distorted, ugly, bad anatomy",
                "width": 512,
                "height": 512,
                "num_inference_steps": 20,
                "guidance_scale": 7.5
            }
            
            logger.info(f"[{podcast_id}] 调用SiliconFlow图像生成API...")
            
            response = requests.post(
                f"{siliconflow_api_base}/images/generations",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                if "data" in result and len(result["data"]) > 0:
                    # 获取生成的图像URL或base64
                    image_data = result["data"][0]
                    image_url = image_data.get("url") or image_data.get("b64_json")
                    
                    if image_url and image_url.startswith("data:"):
                        # 已经是base64格式
                        return image_url
                    elif image_url:
                        # 是URL，直接返回
                        return image_url
                    else:
                        # 如果返回的是b64_json字段
                        b64_data = image_data.get("b64_json")
                        if b64_data:
                            return f"data:image/png;base64,{b64_data}"
                        else:
                            raise Exception("API返回的数据格式不正确")
                else:
                    raise Exception("API返回的数据为空")
            else:
                error_msg = response.text
                logger.error(f"[{podcast_id}] SiliconFlow API调用失败: HTTP {response.status_code}, {error_msg}")
                raise Exception(f"图像生成API调用失败: {error_msg}")
                
        except Exception as e:
            logger.error(f"[{podcast_id}] 调用图像生成API失败: {e}")
            # 如果API调用失败，返回占位图
            img = Image.new('RGB', (512, 512), color=(73, 109, 137))
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            return f"data:image/png;base64,{img_base64}"
            
    except Exception as e:
        logger.error(f"[{podcast_id}] 生成封面图失败: {e}", exc_info=True)
        return None


def upload_cover_image(cover_image_url: str, podcast_id: str) -> Optional[str]:
    """
    上传封面图到云存储
    
    Args:
        cover_image_url: 封面图URL（base64或网络URL）
        podcast_id: 播客ID
    
    Returns:
        云存储URL，失败返回None
    """
    try:
        # 如果已经是云存储URL，直接返回
        if cover_image_url.startswith('http') and not cover_image_url.startswith('data:'):
            return cover_image_url
        
        # 如果是base64，先保存为临时文件
        if cover_image_url.startswith('data:image'):
            # 提取base64数据
            header, encoded = cover_image_url.split(',', 1)
            image_data = base64.b64decode(encoded)
            
            # 保存为临时文件
            cover_temp_path = os.path.join(OUTPUT_DIR, f"cover_{podcast_id}.png")
            with open(cover_temp_path, 'wb') as f:
                f.write(image_data)
        else:
            # 如果是网络URL，需要先下载
            import requests
            response = requests.get(cover_image_url, timeout=30)
            response.raise_for_status()
            
            cover_temp_path = os.path.join(OUTPUT_DIR, f"cover_{podcast_id}.png")
            with open(cover_temp_path, 'wb') as f:
                f.write(response.content)
        
        # 上传到云存储
        agc_storage_url = os.getenv('AGC_STORAGE_URL')
        agc_bucket = os.getenv('AGC_BUCKET')
        agc_domain = os.getenv('AGC_STORAGE_DOMAIN') or os.getenv('AGC_DOMAIN', 'connect-api.cloud.huawei.com')
        agc_client_id = os.getenv('AGC_STORAGE_CLIENT_ID') or os.getenv('AGC_CLIENT_ID')
        agc_client_secret = os.getenv('AGC_STORAGE_CLIENT_SECRET') or os.getenv('AGC_CLIENT_SECRET')
        agc_product_id = os.getenv('AGC_PRODUCT_ID')
        
        if not agc_client_id or not agc_client_secret:
            cfg_path = _find_agc_client_json()
            if cfg_path:
                cid, csecret, proj = _load_agc_credentials_from_file(cfg_path)
                agc_client_id = agc_client_id or cid
                agc_client_secret = agc_client_secret or csecret
                agc_product_id = agc_product_id or proj
        
        if not agc_storage_url or not agc_bucket or not agc_client_id or not agc_client_secret:
            logger.warning(f"[{podcast_id}] 未配置云存储，使用base64 URL")
            return cover_image_url
        
        # 上传封面图
        cover_object_name = f"outputs/podcasts/covers/cover_{podcast_id}.png"
        
        logger.info(f"[{podcast_id}] 开始上传封面图到云存储: {cover_object_name}")
        
        result = upload_generated_podcast(
            output_path=cover_temp_path,
            storage_url=agc_storage_url,
            bucket=agc_bucket,
            object_name=cover_object_name,
            product_id=agc_product_id,
            domain=agc_domain,
            client_id=agc_client_id,
            client_secret=agc_client_secret
        )
        
        # 清理临时文件
        try:
            if os.path.exists(cover_temp_path):
                os.remove(cover_temp_path)
        except:
            pass
        
        # 检查上传结果
        if isinstance(result, dict):
            if result.get('status') == 'uploaded' or result.get('status') == 'success':
                # 构建下载URL
                if not agc_storage_url.endswith('/'):
                    agc_storage_url = agc_storage_url + '/'
                download_url = f"{agc_storage_url}{agc_bucket}/{cover_object_name}"
                logger.info(f"[{podcast_id}] 封面图上传成功: {download_url}")
                return download_url
            else:
                logger.error(f"[{podcast_id}] 封面图上传失败: {result}")
                return cover_image_url  # 返回原始URL
        else:
            # 如果返回的不是字典，可能是异常或其他格式
            logger.error(f"[{podcast_id}] 封面图上传返回格式异常: {result}")
            return cover_image_url  # 返回原始URL
            
    except Exception as e:
        logger.error(f"[{podcast_id}] 上传封面图失败: {e}", exc_info=True)
        return cover_image_url  # 返回原始URL


def update_podcast_cover(podcast: Dict[str, Any], cover_image_url: str) -> bool:
    """
    更新播客的封面图URL到数据库
    
    Args:
        podcast: 播客数据
        cover_image_url: 封面图URL
    
    Returns:
        是否更新成功
    """
    try:
        db_client = get_database_client()
        if not db_client:
            logger.error("无法获取数据库客户端")
            return False
        
        # 更新播客数据
        podcast['cover_image_url'] = cover_image_url
        
        success = db_client.save_podcast(podcast)
        if success:
            logger.info(f"[{podcast['id']}] 数据库更新成功")
            return True
        else:
            logger.error(f"[{podcast['id']}] 数据库更新失败")
            return False
    except Exception as e:
        logger.error(f"[{podcast['id']}] 更新数据库失败: {e}", exc_info=True)
        return False


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("开始批量更新播客封面图")
    logger.info("=" * 60)
    
    # 加载进度
    progress = load_progress()
    processed_ids = set(progress.get("processed_ids", []))
    failed_ids = set(progress.get("failed_ids", []))
    
    logger.info(f"已处理: {len(processed_ids)} 个")
    logger.info(f"失败: {len(failed_ids)} 个")
    
    # 获取数据库客户端
    db_client = get_database_client()
    if not db_client:
        logger.error("无法获取数据库客户端，请检查配置")
        return
    
    # 查询所有播客
    logger.info("正在查询所有播客...")
    all_podcasts = db_client.list_podcasts(limit=None)
    logger.info(f"共查询到 {len(all_podcasts)} 个播客")
    
    # 过滤出没有封面图的播客
    podcasts_without_cover = [
        p for p in all_podcasts
        if not p.get('cover_image_url') or p.get('cover_image_url', '').strip() == ''
    ]
    
    # 排除已处理和失败的
    podcasts_to_process = [
        p for p in podcasts_without_cover
        if p['id'] not in processed_ids and p['id'] not in failed_ids
    ]
    
    logger.info(f"需要处理的播客: {len(podcasts_to_process)} 个")
    
    if len(podcasts_to_process) == 0:
        logger.info("没有需要处理的播客")
        return
    
    # 处理每个播客
    success_count = 0
    fail_count = 0
    
    for idx, podcast in enumerate(podcasts_to_process, 1):
        podcast_id = podcast.get('id', 'unknown')
        podcast_title = podcast.get('title', '未知播客')
        
        logger.info("=" * 60)
        logger.info(f"[{idx}/{len(podcasts_to_process)}] 处理播客: {podcast_id}")
        logger.info(f"  标题: {podcast_title}")
        logger.info("=" * 60)
        
        try:
            # 生成封面图
            cover_image_url = generate_cover_image(
                podcast_id=podcast_id,
                podcast_title=podcast_title,
                text_content=podcast.get('script'),
                topic=podcast.get('topic'),
                category=podcast.get('category'),
                roles=podcast.get('roles', [])
            )
            
            if not cover_image_url:
                logger.error(f"[{podcast_id}] 封面图生成失败")
                failed_ids.add(podcast_id)
                fail_count += 1
                save_progress(progress)
                continue
            
            # 上传封面图到云存储
            final_cover_url = upload_cover_image(cover_image_url, podcast_id)
            
            if not final_cover_url:
                logger.error(f"[{podcast_id}] 封面图上传失败")
                failed_ids.add(podcast_id)
                fail_count += 1
                save_progress(progress)
                continue
            
            # 更新数据库
            if update_podcast_cover(podcast, final_cover_url):
                processed_ids.add(podcast_id)
                success_count += 1
                logger.info(f"[{podcast_id}] ✓ 处理成功")
            else:
                failed_ids.add(podcast_id)
                fail_count += 1
                logger.error(f"[{podcast_id}] ✗ 数据库更新失败")
            
            # 更新进度
            progress["processed_ids"] = list(processed_ids)
            progress["failed_ids"] = list(failed_ids)
            save_progress(progress)
            
            # 避免请求过快，添加延迟
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"[{podcast_id}] 处理失败: {e}", exc_info=True)
            failed_ids.add(podcast_id)
            fail_count += 1
            progress["failed_ids"] = list(failed_ids)
            save_progress(progress)
    
    # 输出统计信息
    logger.info("=" * 60)
    logger.info("批量更新完成")
    logger.info(f"成功: {success_count} 个")
    logger.info(f"失败: {fail_count} 个")
    logger.info(f"总计: {len(podcasts_to_process)} 个")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

