"""
硅基流动API客户端模块
实现混元大模型tencent/Hunyuan-A13B-Instruct的调用
使用 openai 库的 OpenAI 客户端
"""
from typing import List, Dict, Optional, Iterator
from openai import OpenAI
from .config import SILICONFLOW_API_KEY, SILICONFLOW_API_BASE, SILICONFLOW_MODEL, DEFAULT_TEMPERATURE, DEFAULT_MAX_TOKENS, DEFAULT_TOP_P


class SiliconFlowClient:
    """硅基流动API客户端"""
    
    def __init__(self, api_key: Optional[str] = None, api_base: Optional[str] = None):
        """
        初始化API客户端
        
        Args:
            api_key: API密钥，如果为None则使用配置文件中的密钥
            api_base: API基础URL，如果为None则使用配置文件中的URL
        """
        self.api_key = api_key or SILICONFLOW_API_KEY
        self.api_base = api_base or SILICONFLOW_API_BASE
        self.model = SILICONFLOW_MODEL
        
        # 确保 base_url 以斜杠结尾（openai 库要求）
        if self.api_base and not self.api_base.endswith('/'):
            self.api_base = self.api_base + '/'
        
        # 使用 openai 库的 OpenAI 客户端
        self.client = OpenAI(
            base_url=self.api_base,
            api_key=self.api_key
        )
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        top_p: float = DEFAULT_TOP_P,
        stream: bool = False,
        enable_thinking: Optional[bool] = None,
        thinking_budget: Optional[int] = None
    ):
        """
        调用聊天完成API
        
        Args:
            messages: 对话消息列表，格式为 [{"role": "user", "content": "..."}]
            temperature: 温度参数，控制随机性
            max_tokens: 最大生成token数
            top_p: nucleus sampling参数
            stream: 是否使用流式输出
            enable_thinking: 是否启用思考模式
            thinking_budget: 思考预算
        
        Returns:
            API响应结果（流式时返回迭代器，非流式时返回完整响应）
        """
        # 构建请求参数
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": stream
        }
        
        # 添加扩展参数（如果提供，使用 extra_body 传递）
        extra_body = {}
        if enable_thinking is not None:
            extra_body["enable_thinking"] = enable_thinking
        if thinking_budget is not None:
            extra_body["thinking_budget"] = thinking_budget
        
        if extra_body:
            kwargs["extra_body"] = extra_body
        
        try:
            response = self.client.chat.completions.create(**kwargs)
            return response
        except Exception as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json() if hasattr(e.response, 'json') else {}
                    error_info = error_data.get('error', {})
                    error_msg = error_info.get('message', error_msg)
                except:
                    pass
            raise Exception(f"API调用失败: {error_msg}")
    
    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        top_p: float = DEFAULT_TOP_P,
        enable_thinking: Optional[bool] = None,
        thinking_budget: Optional[int] = None
    ) -> str:
        """
        生成文本的便捷方法（使用流式输出收集完整内容）
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            temperature: 温度参数
            max_tokens: 最大生成token数
            top_p: nucleus sampling参数
            enable_thinking: 是否启用思考模式
            thinking_budget: 思考预算
        
        Returns:
            生成的文本内容
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # 使用流式输出收集完整内容
        content = ""
        reasoning_content = ""
        
        try:
            # 构建请求参数
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": top_p,
                "stream": True  # 启用流式输出
            }
            
            # 添加扩展参数（如果提供，使用 extra_body 传递）
            extra_body = {}
            if enable_thinking is not None:
                extra_body["enable_thinking"] = enable_thinking
            if thinking_budget is not None:
                extra_body["thinking_budget"] = thinking_budget
            
            if extra_body:
                kwargs["extra_body"] = extra_body
            
            response = self.client.chat.completions.create(**kwargs)
            
            # 逐步接收并处理响应
            for chunk in response:
                if not chunk.choices or len(chunk.choices) == 0:
                    continue
                    
                delta = chunk.choices[0].delta
                if not delta:
                    continue
                
                # 收集 content
                if hasattr(delta, 'content') and delta.content:
                    content += delta.content
                
                # 收集 reasoning_content（如果存在，但不影响最终返回）
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    reasoning_content += delta.reasoning_content
            
            # 检查是否收集到内容
            if not content or len(content.strip()) == 0:
                # 如果只有 reasoning_content 但没有 content，可能是模型还在思考
                if reasoning_content:
                    raise Exception("API返回了思考内容但未返回实际内容，可能是模型生成失败或需要更多时间")
                raise Exception("API返回了空内容，可能是模型生成失败")
            
            return content
            
        except Exception as e:
            # 如果是我们自定义的异常，直接抛出
            if isinstance(e, Exception) and ("API返回了" in str(e) or "API调用失败" in str(e)):
                raise
            # 其他异常包装后抛出
            raise Exception(f"API调用失败: {str(e)}")
    
    def generate_streaming(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        top_p: float = DEFAULT_TOP_P,
        enable_thinking: Optional[bool] = None,
        thinking_budget: Optional[int] = None
    ) -> Iterator[str]:
        """
        流式生成文本的便捷方法
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            temperature: 温度参数
            max_tokens: 最大生成token数
            top_p: nucleus sampling参数
            enable_thinking: 是否启用思考模式
            thinking_budget: 思考预算
        
        Yields:
            生成的文本片段
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            # 构建请求参数
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": top_p,
                "stream": True
            }
            
            # 添加扩展参数（如果提供，使用 extra_body 传递）
            extra_body = {}
            if enable_thinking is not None:
                extra_body["enable_thinking"] = enable_thinking
            if thinking_budget is not None:
                extra_body["thinking_budget"] = thinking_budget
            
            if extra_body:
                kwargs["extra_body"] = extra_body
            
            response = self.client.chat.completions.create(**kwargs)
            
            # 初始化标志变量以检测reasoning_content的第一个和最后一个输出
            is_first_reasoning = True
            is_content_start = True
            
            for chunk in response:
                if not chunk.choices or len(chunk.choices) == 0:
                    continue
                    
                delta = chunk.choices[0].delta
                if not delta:
                    continue
                
                # 处理 content
                if hasattr(delta, 'content') and delta.content:
                    if not is_first_reasoning and is_content_start:
                        # 如果之前有 reasoning_content，现在开始输出 content
                        is_content_start = False
                    yield delta.content
                
                # 处理 reasoning_content（可选，用于调试）
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    if is_first_reasoning:
                        # 第一个 reasoning_content 输出
                        is_first_reasoning = False
                    # 注意：这里可以选择是否 yield reasoning_content
                    # 根据需求决定是否输出思考过程
                    # yield f"[思考]{delta.reasoning_content}"
                        
        except Exception as e:
            raise Exception(f"流式API调用失败: {str(e)}")


# 创建全局客户端实例
_client_instance: Optional[SiliconFlowClient] = None

def get_client() -> SiliconFlowClient:
    """获取全局API客户端实例"""
    global _client_instance
    if _client_instance is None:
        _client_instance = SiliconFlowClient()
    return _client_instance
