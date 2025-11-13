"""
输入格式处理模块
支持多种输入格式：文字、PDF、网页、公众号等
"""
import os
import re
import json
import logging
import requests
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlparse
from io import BytesIO

logger = logging.getLogger(__name__)


class InputProcessor:
    """输入格式处理器"""
    
    def __init__(self):
        """初始化输入处理器"""
        pass
    
    def extract_text_from_wechat_article(self, url: str, timeout: int = 30) -> str:
        """
        从微信公众号文章URL提取文本内容
        
        Args:
            url: 微信公众号文章URL
            timeout: 请求超时时间（秒）
        
        Returns:
            提取的文本内容
        """
        try:
            logger.info(f"正在提取微信公众号文章内容: {url}")
            
            # 设置请求头，模拟浏览器访问
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            # 获取文章内容
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            html = response.text
            
            # 微信公众号文章的HTML结构：内容通常在 <div id="js_content"> 或类似的容器中
            # 尝试多种可能的选择器
            import re
            
            # 方法1: 查找 js_content 容器
            content_match = re.search(r'<div[^>]*id=["\']js_content["\'][^>]*>(.*?)</div>', html, re.DOTALL | re.IGNORECASE)
            if content_match:
                content_html = content_match.group(1)
            else:
                # 方法2: 查找 rich_media_content 容器
                content_match = re.search(r'<div[^>]*class=["\'][^"]*rich_media_content[^"]*["\'][^>]*>(.*?)</div>', html, re.DOTALL | re.IGNORECASE)
                if content_match:
                    content_html = content_match.group(1)
                else:
                    # 方法3: 尝试查找包含文章正文的区域（通常包含多个段落）
                    # 查找包含 <p> 标签较多的区域
                    content_match = re.search(r'<div[^>]*>(.*?<p[^>]*>.*?</p>.*?)</div>', html, re.DOTALL | re.IGNORECASE)
                    if content_match:
                        content_html = content_match.group(1)
                    else:
                        # 如果都找不到，返回整个HTML让后续处理
                        content_html = html
            
            # 提取纯文本：移除HTML标签
            # 先处理一些特殊的标签
            content_html = re.sub(r'<script[^>]*>.*?</script>', '', content_html, flags=re.DOTALL | re.IGNORECASE)
            content_html = re.sub(r'<style[^>]*>.*?</style>', '', content_html, flags=re.DOTALL | re.IGNORECASE)
            content_html = re.sub(r'<iframe[^>]*>.*?</iframe>', '', content_html, flags=re.DOTALL | re.IGNORECASE)
            
            # 将 <br> 和 <p> 标签转换为换行
            content_html = re.sub(r'<br[^>]*>', '\n', content_html, flags=re.IGNORECASE)
            content_html = re.sub(r'</p>', '\n\n', content_html, flags=re.IGNORECASE)
            content_html = re.sub(r'<p[^>]*>', '', content_html, flags=re.IGNORECASE)
            
            # 移除所有HTML标签
            text = re.sub(r'<[^>]+>', '', content_html)
            
            # 清理文本：移除多余的空白字符
            text = re.sub(r'\s+', ' ', text)  # 多个空格合并为一个
            text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # 多个换行合并为两个
            text = text.strip()
            
            # 如果提取的文本太短（可能是提取失败），尝试其他方法
            if len(text) < 100:
                logger.warning(f"提取的文本内容过短（{len(text)}字符），尝试备用方法")
                # 尝试使用正则表达式直接提取可见文本
                text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r'<[^>]+>', '', text)
                text = re.sub(r'\s+', ' ', text)
                text = text.strip()
            
            logger.info(f"微信公众号文章提取成功: {len(text)} 字符")
            return text
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取微信公众号文章失败: {str(e)}")
            raise Exception(f"获取微信公众号文章失败: {str(e)}")
        except Exception as e:
            logger.error(f"提取微信公众号文章内容失败: {str(e)}")
            raise Exception(f"提取微信公众号文章内容失败: {str(e)}")
    
    def extract_text_from_webpage(self, url: str, timeout: int = 30) -> str:
        """
        从网页URL提取文本内容
        
        Args:
            url: 网页URL
            timeout: 请求超时时间（秒）
        
        Returns:
            提取的文本内容
        """
        try:
            logger.info(f"正在提取网页内容: {url}")
            
            # 设置请求头，模拟浏览器访问
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
            }
            
            # 获取网页内容
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            html = response.text
            
            # 移除脚本和样式
            html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
            html = re.sub(r'<iframe[^>]*>.*?</iframe>', '', html, flags=re.DOTALL | re.IGNORECASE)
            html = re.sub(r'<noscript[^>]*>.*?</noscript>', '', html, flags=re.DOTALL | re.IGNORECASE)
            
            # 尝试提取主要内容区域
            # 常见的内容容器标签和class
            content_patterns = [
                r'<main[^>]*>(.*?)</main>',
                r'<article[^>]*>(.*?)</article>',
                r'<div[^>]*class=["\'][^"]*content[^"]*["\'][^>]*>(.*?)</div>',
                r'<div[^>]*class=["\'][^"]*article[^"]*["\'][^>]*>(.*?)</div>',
                r'<div[^>]*class=["\'][^"]*post[^"]*["\'][^>]*>(.*?)</div>',
                r'<div[^>]*class=["\'][^"]*entry[^"]*["\'][^>]*>(.*?)</div>',
            ]
            
            content_html = None
            for pattern in content_patterns:
                match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
                if match:
                    content_html = match.group(1)
                    if len(content_html) > 200:  # 确保内容足够长
                        break
            
            # 如果没找到内容区域，使用body标签内的内容
            if not content_html:
                body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE)
                if body_match:
                    content_html = body_match.group(1)
                else:
                    content_html = html
            
            # 将常见的HTML标签转换为换行
            content_html = re.sub(r'<br[^>]*>', '\n', content_html, flags=re.IGNORECASE)
            content_html = re.sub(r'</p>', '\n\n', content_html, flags=re.IGNORECASE)
            content_html = re.sub(r'<p[^>]*>', '', content_html, flags=re.IGNORECASE)
            content_html = re.sub(r'</div>', '\n', content_html, flags=re.IGNORECASE)
            content_html = re.sub(r'<div[^>]*>', '', content_html, flags=re.IGNORECASE)
            content_html = re.sub(r'</h[1-6]>', '\n\n', content_html, flags=re.IGNORECASE)
            content_html = re.sub(r'<h[1-6][^>]*>', '\n', content_html, flags=re.IGNORECASE)
            
            # 移除所有HTML标签
            text = re.sub(r'<[^>]+>', '', content_html)
            
            # 清理文本
            text = re.sub(r'&nbsp;', ' ', text)
            text = re.sub(r'&lt;', '<', text)
            text = re.sub(r'&gt;', '>', text)
            text = re.sub(r'&amp;', '&', text)
            text = re.sub(r'&quot;', '"', text)
            text = re.sub(r'&apos;', "'", text)
            text = re.sub(r'\s+', ' ', text)
            text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
            text = text.strip()
            
            logger.info(f"网页内容提取成功: {len(text)} 字符")
            return text
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取网页内容失败: {str(e)}")
            raise Exception(f"获取网页内容失败: {str(e)}")
        except Exception as e:
            logger.error(f"提取网页内容失败: {str(e)}")
            raise Exception(f"提取网页内容失败: {str(e)}")
    
    def extract_text_from_pdf_url(self, url: str, timeout: int = 60) -> str:
        """
        从PDF文件URL提取文本内容
        
        Args:
            url: PDF文件URL
            timeout: 请求超时时间（秒）
        
        Returns:
            提取的文本内容
        """
        try:
            logger.info(f"正在提取PDF文件内容: {url}")
            
            # 下载PDF文件
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=timeout, stream=True)
            response.raise_for_status()
            
            pdf_bytes = response.content
            
            # 使用PyPDF2或pdfplumber提取文本
            try:
                # 尝试使用pdfplumber（更准确）
                import pdfplumber
                text_parts = []
                with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text.strip())
                text = '\n\n'.join(text_parts)
                logger.info(f"使用pdfplumber提取PDF成功: {len(text)} 字符")
                return text
            except ImportError:
                try:
                    # 回退到PyPDF2
                    import PyPDF2
                    pdf_file = BytesIO(pdf_bytes)
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    text_parts = []
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text.strip())
                    text = '\n\n'.join(text_parts)
                    logger.info(f"使用PyPDF2提取PDF成功: {len(text)} 字符")
                    return text
                except ImportError:
                    raise Exception("需要安装PDF处理库: pip install pdfplumber 或 pip install PyPDF2")
            except Exception as e:
                logger.warning(f"使用pdfplumber提取失败: {str(e)}，尝试PyPDF2")
                try:
                    # 回退到PyPDF2
                    import PyPDF2
                    pdf_file = BytesIO(pdf_bytes)
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    text_parts = []
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text.strip())
                    text = '\n\n'.join(text_parts)
                    logger.info(f"使用PyPDF2提取PDF成功: {len(text)} 字符")
                    return text
                except Exception as e2:
                    raise Exception(f"PDF提取失败: {str(e2)}")
                    
        except requests.exceptions.RequestException as e:
            logger.error(f"下载PDF文件失败: {str(e)}")
            raise Exception(f"下载PDF文件失败: {str(e)}")
        except Exception as e:
            logger.error(f"提取PDF内容失败: {str(e)}")
            raise Exception(f"提取PDF内容失败: {str(e)}")
    
    def extract_text_from_pdf_file(self, file_path: str) -> str:
        """
        从本地PDF文件提取文本内容
        
        Args:
            file_path: PDF文件路径
        
        Returns:
            提取的文本内容
        """
        try:
            logger.info(f"正在提取本地PDF文件内容: {file_path}")
            
            # 使用pdfplumber或PyPDF2提取文本
            try:
                import pdfplumber
                text_parts = []
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text.strip())
                text = '\n\n'.join(text_parts)
                logger.info(f"使用pdfplumber提取PDF成功: {len(text)} 字符")
                return text
            except ImportError:
                try:
                    import PyPDF2
                    with open(file_path, 'rb') as pdf_file:
                        pdf_reader = PyPDF2.PdfReader(pdf_file)
                        text_parts = []
                        for page in pdf_reader.pages:
                            page_text = page.extract_text()
                            if page_text:
                                text_parts.append(page_text.strip())
                        text = '\n\n'.join(text_parts)
                        logger.info(f"使用PyPDF2提取PDF成功: {len(text)} 字符")
                        return text
                except ImportError:
                    raise Exception("需要安装PDF处理库: pip install pdfplumber 或 pip install PyPDF2")
            except Exception as e:
                logger.warning(f"使用pdfplumber提取失败: {str(e)}，尝试PyPDF2")
                try:
                    import PyPDF2
                    with open(file_path, 'rb') as pdf_file:
                        pdf_reader = PyPDF2.PdfReader(pdf_file)
                        text_parts = []
                        for page in pdf_reader.pages:
                            page_text = page.extract_text()
                            if page_text:
                                text_parts.append(page_text.strip())
                        text = '\n\n'.join(text_parts)
                        logger.info(f"使用PyPDF2提取PDF成功: {len(text)} 字符")
                        return text
                except Exception as e2:
                    raise Exception(f"PDF提取失败: {str(e2)}")
                    
        except Exception as e:
            logger.error(f"提取PDF内容失败: {str(e)}")
            raise Exception(f"提取PDF内容失败: {str(e)}")
    
    def parse_instruction(self, text_with_instruction: str) -> Tuple[str, Optional[str]]:
        """
        解析包含指令的文本，分离出文本内容和指令
        
        Args:
            text_with_instruction: 包含指令的文本，格式可能是：
                - "文本内容\n\n[指令: 指令内容]"
                - "文本内容\n指令: 指令内容"
                - 其他格式
        
        Returns:
            (文本内容, 指令内容) 元组，如果没有指令则指令内容为None
        """
        # 尝试匹配多种指令格式
        patterns = [
            r'\[指令[：:]\s*(.+?)\]',  # [指令: 内容]
            r'指令[：:]\s*(.+?)(?:\n|$)',  # 指令: 内容（单独一行）
            r'INSTRUCTION[：:]\s*(.+?)(?:\n|$)',  # INSTRUCTION: 内容（英文指令）
            r'instruction[：:]\s*(.+?)(?:\n|$)',  # instruction: 内容（小写）
        ]
        
        instruction = None
        text = text_with_instruction
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                instruction = match.group(1).strip()
                # 移除指令部分
                text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
                break
        
        # 清理文本
        text = text.strip()
        
        return text, instruction
    
    def process_input(
        self,
        input_type: str,
        input_content: Optional[str] = None,
        input_url: Optional[str] = None,
        input_file_path: Optional[str] = None,
        instruction: Optional[str] = None
    ) -> Tuple[str, Optional[str]]:
        """
        处理不同类型的输入，提取文本内容
        
        Args:
            input_type: 输入类型，可选值：
                - "文字" / "text"
                - "文字+指令" / "text+instruction"
                - "公众号" / "wechat"
                - "公众号+指令" / "wechat+instruction"
                - "网页" / "webpage"
                - "PDF"
                - "PDF+指令" / "pdf+instruction"
                - "文字+英文指令" / "text+english_instruction"
            input_content: 文本内容（用于"文字"类型）
            input_url: 输入URL（用于"公众号"、"网页"、"PDF"类型）
            input_file_path: 输入文件路径（用于"PDF"类型）
            instruction: 指令内容（可选，如果输入类型中已经包含指令，会从输入中解析）
        
        Returns:
            (提取的文本内容, 指令内容) 元组
        """
        input_type_lower = input_type.lower().strip()
        extracted_text = ""
        extracted_instruction = instruction
        
        # 处理包含指令的类型
        has_instruction = False
        if "+指令" in input_type or "+instruction" in input_type_lower or "+英文指令" in input_type:
            has_instruction = True
        
        # 提取基础类型（去掉指令后缀）
        base_type = input_type_lower
        if "+指令" in input_type:
            base_type = input_type.split("+指令")[0].lower().strip()
        elif "+instruction" in input_type_lower:
            base_type = input_type_lower.split("+instruction")[0].strip()
        elif "+英文指令" in input_type:
            base_type = input_type.split("+英文指令")[0].lower().strip()
        
        # 根据输入类型处理
        if base_type in ["文字", "text"] or input_type_lower in ["文字", "text"]:
            # 纯文字输入
            if not input_content:
                raise ValueError("文字类型需要提供 input_content 参数")
            extracted_text = input_content
            
            # 如果包含指令标记，解析指令
            if has_instruction:
                extracted_text, extracted_instruction = self.parse_instruction(extracted_text)
            
        elif base_type in ["公众号", "wechat", "微信公众号"] or "公众号" in input_type_lower or "wechat" in input_type_lower:
            # 微信公众号文章（支持"公众号"、"公众号+指令"等）
            if not input_url:
                raise ValueError("公众号类型需要提供 input_url 参数")
            extracted_text = self.extract_text_from_wechat_article(input_url)
            
            # 如果包含指令标记，解析指令
            if has_instruction:
                extracted_text, extracted_instruction = self.parse_instruction(extracted_text)
                
        elif base_type in ["网页", "webpage", "web"] or input_type_lower in ["网页", "webpage", "web"]:
            # 网页内容
            if not input_url:
                raise ValueError("网页类型需要提供 input_url 参数")
            extracted_text = self.extract_text_from_webpage(input_url)
            
        elif base_type in ["pdf"] or input_type_lower in ["pdf"]:
            # PDF文件（优先使用文件路径，如果没有则使用URL）
            if input_file_path:
                extracted_text = self.extract_text_from_pdf_file(input_file_path)
            elif input_url:
                extracted_text = self.extract_text_from_pdf_url(input_url)
            else:
                raise ValueError("PDF类型需要提供 input_file_path 或 input_url 参数")
            
            # 如果包含指令标记，解析指令
            if has_instruction:
                extracted_text, extracted_instruction = self.parse_instruction(extracted_text)
                
        else:
            raise ValueError(f"不支持的输入类型: {input_type}")
        
        # 验证提取的文本
        if not extracted_text or len(extracted_text.strip()) < 10:
            raise ValueError(f"提取的文本内容过短或为空（{len(extracted_text)}字符），请检查输入")
        
        return extracted_text.strip(), extracted_instruction
    
    def detect_input_type_from_content(self, content: str, url: Optional[str] = None) -> str:
        """
        自动检测输入类型
        
        Args:
            content: 输入内容
            url: 输入URL（如果有）
        
        Returns:
            检测到的输入类型
        """
        if url:
            url_lower = url.lower()
            if "mp.weixin.qq.com" in url_lower:
                # 检测是否包含指令
                if re.search(r'\[指令[：:]|指令[：:]|INSTRUCTION[：:]|instruction[：:]', content, re.IGNORECASE):
                    return "公众号+指令"
                return "公众号"
            elif url_lower.endswith(".pdf") or ".pdf" in url_lower:
                # 检测是否包含指令
                if re.search(r'\[指令[：:]|指令[：:]|INSTRUCTION[：:]|instruction[：:]', content, re.IGNORECASE):
                    return "PDF+指令"
                return "PDF"
            else:
                # 检测是否包含指令
                if re.search(r'\[指令[：:]|指令[：:]|INSTRUCTION[：:]|instruction[：:]', content, re.IGNORECASE):
                    return "网页+指令"
                return "网页"
        else:
            # 纯文本，检测是否包含指令
            if re.search(r'\[指令[：:]|指令[：:]|INSTRUCTION[：:]|instruction[：:]', content, re.IGNORECASE):
                return "文字+指令"
            return "文字"


def get_processor() -> InputProcessor:
    """获取输入处理器实例（单例模式）"""
    global _processor_instance
    if '_processor_instance' not in globals():
        globals()['_processor_instance'] = InputProcessor()
    return globals()['_processor_instance']

