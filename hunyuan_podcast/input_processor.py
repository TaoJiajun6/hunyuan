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

# 尝试导入可选的依赖库
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    logger.warning("BeautifulSoup4未安装，将使用基础HTML解析")

try:
    import html2text
    HAS_HTML2TEXT = True
except ImportError:
    HAS_HTML2TEXT = False
    logger.warning("html2text未安装，将使用基础文本提取")

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    logger.warning("Playwright未安装，无法处理需要JavaScript渲染的网页")


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
    
    def _extract_with_playwright(self, url: str, timeout: int = 30) -> Optional[str]:
        """
        使用Playwright提取需要JavaScript渲染的网页内容
        
        Args:
            url: 网页URL
            timeout: 超时时间（秒）
        
        Returns:
            提取的文本内容，如果失败返回None
        """
        if not HAS_PLAYWRIGHT:
            return None
        
        try:
            logger.info(f"尝试使用Playwright提取网页内容: {url}")
            with sync_playwright() as p:
                # 启动浏览器（使用chromium）
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                page = context.new_page()
                
                # 访问页面并等待内容加载
                page.goto(url, wait_until='networkidle', timeout=timeout * 1000)
                
                # 等待页面内容加载（额外等待2秒）
                page.wait_for_timeout(2000)
                
                # 获取页面HTML
                html = page.content()
                
                browser.close()
                
                # 使用BeautifulSoup或html2text提取文本
                if HAS_BS4:
                    soup = BeautifulSoup(html, 'lxml')
                    # 移除脚本和样式
                    for script in soup(["script", "style", "noscript", "iframe"]):
                        script.decompose()
                    # 提取文本
                    text = soup.get_text(separator='\n', strip=True)
                elif HAS_HTML2TEXT:
                    h = html2text.HTML2Text()
                    h.ignore_links = True
                    h.ignore_images = True
                    text = h.handle(html)
                else:
                    # 基础方法
                    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
                    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
                    text = re.sub(r'<[^>]+>', '', html)
                
                # 清理文本
                text = re.sub(r'\s+', ' ', text)
                text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
                text = text.strip()
                
                if len(text) > 100:
                    logger.info(f"Playwright提取成功: {len(text)} 字符")
                    return text
                else:
                    logger.warning(f"Playwright提取的内容过短: {len(text)} 字符")
                    return None
                    
        except PlaywrightTimeoutError:
            logger.warning(f"Playwright超时: {url}")
            return None
        except Exception as e:
            logger.warning(f"Playwright提取失败: {str(e)}")
            return None
    
    def extract_text_from_webpage(self, url: str, timeout: int = 30) -> str:
        """
        从网页URL提取文本内容
        支持多种提取策略：
        1. 使用requests + BeautifulSoup（标准网页）
        2. 使用Playwright（需要JavaScript渲染的网页）
        
        Args:
            url: 网页URL
            timeout: 请求超时时间（秒）
        
        Returns:
            提取的文本内容
        """
        try:
            logger.info(f"正在提取网页内容: {url}")
            
            # 检测特殊网站（需要JavaScript渲染的网站）
            url_lower = url.lower()
            special_sites = {
                'weibo.com': '微博网站需要JavaScript渲染',
                'twitter.com': 'Twitter网站需要JavaScript渲染',
                'facebook.com': 'Facebook网站需要JavaScript渲染',
                'instagram.com': 'Instagram网站需要JavaScript渲染',
                'mbd.baidu.com': '百度移动端网页需要JavaScript渲染',
            }
            
            needs_js = any(site_key in url_lower for site_key in special_sites.keys())
            
            # 如果检测到需要JavaScript的网站，优先使用Playwright
            if needs_js and HAS_PLAYWRIGHT:
                logger.info(f"检测到需要JavaScript渲染的网站，使用Playwright提取")
                text = self._extract_with_playwright(url, timeout)
                if text and len(text) > 100:
                    return text
            
            # 方法1: 使用requests获取HTML
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Referer': 'https://www.google.com/'
            }
            
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            # 处理编码问题
            html = None
            if response.encoding:
                try:
                    html = response.text
                except (UnicodeDecodeError, UnicodeError):
                    html = None
            
            if html is None:
                try:
                    import chardet
                    detected = chardet.detect(response.content)
                    if detected and detected.get('encoding'):
                        response.encoding = detected['encoding']
                        html = response.text
                        logger.info(f"使用chardet检测到编码: {detected['encoding']}")
                except ImportError:
                    pass
                except Exception:
                    pass
            
            if html is None:
                for encoding in ['utf-8', 'gbk', 'gb2312', 'gb18030', 'big5']:
                    try:
                        response.encoding = encoding
                        html = response.text
                        logger.info(f"使用编码 {encoding} 成功")
                        break
                    except (UnicodeDecodeError, UnicodeError):
                        continue
            
            if html is None:
                raise Exception("无法确定网页编码，请检查网页是否可访问")
            
            logger.info(f"网页编码: {response.encoding}, HTML长度: {len(html)} 字符")
            
            # 检查是否是空页面
            if len(html) < 500:
                # 如果内容过短且需要JavaScript，尝试使用Playwright
                if needs_js and HAS_PLAYWRIGHT:
                    logger.info("HTML内容过短，尝试使用Playwright")
                    text = self._extract_with_playwright(url, timeout)
                    if text and len(text) > 100:
                        return text
                raise Exception(f'网页内容为空或过短，可能是需要JavaScript渲染的动态网站。建议：1) 复制网页文本内容直接输入；2) 使用"文字+指令"类型；3) 或提供PC版网页URL')
            
            # 使用BeautifulSoup提取文本（如果可用）
            if HAS_BS4:
                try:
                    soup = BeautifulSoup(html, 'lxml')
                    
                    # 移除脚本、样式等
                    for element in soup(["script", "style", "noscript", "iframe", "nav", "header", "footer", "aside"]):
                        element.decompose()
                    
                    # 尝试找到主要内容区域
                    content_selectors = [
                        'main',
                        'article',
                        '[class*="content"]',
                        '[class*="article"]',
                        '[class*="post"]',
                        '[class*="entry"]',
                        '[id*="content"]',
                        '[id*="article"]',
                    ]
                    
                    content_element = None
                    for selector in content_selectors:
                        try:
                            elements = soup.select(selector)
                            for elem in elements:
                                text_len = len(elem.get_text(strip=True))
                                if text_len > 200:
                                    content_element = elem
                                    break
                            if content_element:
                                break
                        except Exception:
                            continue
                    
                    # 如果找到内容区域，使用它；否则使用body
                    if content_element:
                        text = content_element.get_text(separator='\n', strip=True)
                    else:
                        body = soup.find('body')
                        if body:
                            text = body.get_text(separator='\n', strip=True)
                        else:
                            text = soup.get_text(separator='\n', strip=True)
                    
                    # 清理文本
                    text = re.sub(r'\s+', ' ', text)
                    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
                    text = text.strip()
                    
                    if len(text) > 100:
                        logger.info(f"BeautifulSoup提取成功: {len(text)} 字符")
                        return text
                except Exception as e:
                    logger.warning(f"BeautifulSoup提取失败: {str(e)}，尝试其他方法")
            
            # 使用html2text提取（如果可用）
            if HAS_HTML2TEXT:
                try:
                    h = html2text.HTML2Text()
                    h.ignore_links = True
                    h.ignore_images = True
                    h.body_width = 0  # 不限制行宽
                    text = h.handle(html)
                    text = re.sub(r'\s+', ' ', text)
                    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
                    text = text.strip()
                    
                    if len(text) > 100:
                        logger.info(f"html2text提取成功: {len(text)} 字符")
                        return text
                except Exception as e:
                    logger.warning(f"html2text提取失败: {str(e)}，尝试基础方法")
            
            # 基础方法：使用正则表达式
            html_clean = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            html_clean = re.sub(r'<style[^>]*>.*?</style>', '', html_clean, flags=re.DOTALL | re.IGNORECASE)
            html_clean = re.sub(r'<iframe[^>]*>.*?</iframe>', '', html_clean, flags=re.DOTALL | re.IGNORECASE)
            html_clean = re.sub(r'<noscript[^>]*>.*?</noscript>', '', html_clean, flags=re.DOTALL | re.IGNORECASE)
            
            # 尝试提取主要内容区域
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
                match = re.search(pattern, html_clean, re.DOTALL | re.IGNORECASE)
                if match:
                    content_html = match.group(1)
                    if len(content_html) > 200:
                        break
            
            if not content_html:
                body_match = re.search(r'<body[^>]*>(.*?)</body>', html_clean, re.DOTALL | re.IGNORECASE)
                if body_match:
                    content_html = body_match.group(1)
                else:
                    content_html = html_clean
            
            # 转换HTML标签为文本
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
            
            # 如果提取的文本过短，尝试使用Playwright
            if len(text) < 100:
                logger.warning(f"基础方法提取的文本过短（{len(text)}字符），尝试使用Playwright")
                if HAS_PLAYWRIGHT:
                    playwright_text = self._extract_with_playwright(url, timeout)
                    if playwright_text and len(playwright_text) > 100:
                        return playwright_text
                
                preview = text[:200] if len(text) > 200 else text
                raise Exception(f'无法从该网页提取有效文本内容（仅提取到{len(text)}字符，内容: "{preview[:50]}..."）。可能原因：1) 网页需要JavaScript渲染（如百度移动端、微博等）；2) 网页有反爬虫保护；3) 网页结构特殊。建议：1) 复制网页文本内容直接输入；2) 使用"文字+指令"类型；3) 或提供PC版网页URL；4) 安装Playwright以支持JavaScript渲染: pip install playwright && playwright install chromium')
            
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
    
    def clean_novel_content(self, text: str) -> str:
        """
        清理小说文本内容，移除中括号标记和无关内容
        
        Args:
            text: 原始文本内容
        
        Returns:
            清理后的文本内容
        """
        if not text:
            return text
        
        lines = text.split('\n')
        cleaned_lines = []
        
        # 需要移除的关键词（包含这些关键词的行会被移除，这些通常是文档结构标记）
        exclude_keywords = [
            '作者公告', '入V章节说明', '入v章节说明', '入V说明', '入v说明',
            '关于简介君', '闲话', '排榜', '致敬汪先生', '声明', '用户上传',
            '八零电子书', 'txt80.cc', '存储空间', '免费下载服务',
            '收藏评论打赏', '古风首饰', '幸运读者', '完本',
            '美男出场惊艳榜', '惊艳程度', '按照本文出场顺序',
            '可曾有一句诗打动你', '可曾有一首诗打动过你'
        ]
        
        # 需要移除的段落起始关键词（包含这些关键词的段落会被整体移除）
        exclude_section_keywords = [
            '作者公告', '入V章节说明', '入v章节说明', '关于简介君', '闲话',
            '排榜', '致敬', '声明', '用户上传之内容开始'
        ]
        
        skip_until_empty = False  # 标记是否在跳过某个段落
        
        for line in lines:
            original_line = line
            line = line.strip()
            
            # 如果遇到空行，结束跳过段落
            if not line:
                skip_until_empty = False
                # 如果上一行不是空行，保留一个空行作为段落分隔
                if cleaned_lines and cleaned_lines[-1]:
                    cleaned_lines.append('')
                continue
            
            # 如果正在跳过段落，继续跳过直到空行
            if skip_until_empty:
                continue
            
            # 检查是否是段落起始关键词（需要移除整个段落）
            is_section_start = False
            for keyword in exclude_section_keywords:
                if keyword in line:
                    is_section_start = True
                    skip_until_empty = True
                    break
            
            if is_section_start:
                continue
            
            # 移除所有中括号标记（【xxx】格式）
            # 匹配全角中括号【】和半角中括号[]
            # 注意：保留角色标记格式 [角色A] 等，只移除其他中括号内容
            # 先检查是否是角色标记格式
            if not re.match(r'^\s*\[角色[ABC]\]', line, re.IGNORECASE):
                # 如果不是角色标记，移除所有中括号内容
                line = re.sub(r'[【\[][^】\]]*[】\]]', '', line)
            
            # 如果移除中括号后行变空，跳过这一行
            if not line.strip():
                continue
            
            # 检查是否包含需要排除的关键词（这些通常是文档结构标记行）
            should_exclude = False
            for keyword in exclude_keywords:
                if keyword in line:
                    should_exclude = True
                    break
            
            # 如果包含排除关键词，跳过这一行
            if should_exclude:
                continue
            
            # 检查是否是分隔线（多个连续的符号）
            if re.match(r'^[-=*_]{3,}$', line):
                continue
            
            # 检查是否是明显的文档结构标记
            if line.startswith('------------') or line.startswith('==========') or line.startswith('********'):
                continue
            
            # 保留清理后的行
            cleaned_lines.append(line)
        
        # 合并清理后的行
        cleaned_text = '\n'.join(cleaned_lines)
        
        # 清理多余的空行（多个连续空行合并为两个）
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
        
        # 移除首尾空白
        cleaned_text = cleaned_text.strip()
        
        logger.info(f"文本清理完成: 原始长度 {len(text)} 字符，清理后 {len(cleaned_text)} 字符")
        
        return cleaned_text
    
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
            
            # 如果包含指令标记，解析指令
            if has_instruction:
                extracted_text, extracted_instruction = self.parse_instruction(extracted_text)
            
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

