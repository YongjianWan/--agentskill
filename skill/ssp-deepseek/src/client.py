#!/usr/bin/env python3
"""
SSP DeepSeek R1 客户端

支持普通对话和流式输出
"""

import requests
import json
import time
import os
from typing import Iterator, Optional, List, Dict, Any
from .auth import SSPAuth


class SSPDeepSeekClient:
    """SSP DeepSeek R1 客户端
    
    使用示例:
        client = SSPDeepSeekClient("access_key", "secret_key")
        
        # 普通对话
        result = client.chat([{"role": "user", "content": "你好"}])
        
        # 流式输出
        for chunk in client.chat_stream([{"role": "user", "content": "讲个故事"}]):
            print(chunk, end="", flush=True)
    """
    
    # DeepSeek V3 端点
    BASE_URL = "https://www.ssfssp.com:8888/ssp/openApi/GkfFhhUy/kvshB4Rh/LNslKxsF"
    CHAT_ENDPOINT = "/v1/chat/completions"
    
    DEFAULT_MODEL = "DeepSeek-V3"
    DEFAULT_MAX_TOKENS = 2000
    DEFAULT_TEMPERATURE = 0.7
    REQUEST_TIMEOUT = 60
    
    def __init__(self, access_key: Optional[str] = None, secret_key: Optional[str] = None):
        """
        初始化客户端
        
        Args:
            access_key: SSP AccessKey（默认从环境变量 SSP_ACCESS_KEY 读取）
            secret_key: SSP SecretKey（默认从环境变量 SSP_SECRET_KEY 读取）
        """
        access_key = access_key or os.getenv("SSP_ACCESS_KEY")
        secret_key = secret_key or os.getenv("SSP_SECRET_KEY")
        
        if not access_key or not secret_key:
            raise ValueError("必须提供 access_key 和 secret_key，或设置环境变量")
        
        self.auth = SSPAuth(access_key, secret_key)
    
    def _get_headers(self) -> dict:
        """获取请求头（自动刷新 Token）"""
        return self.auth.get_auth_header()
    
    def chat(self, 
             messages: List[Dict[str, str]], 
             model: str = DEFAULT_MODEL,
             stream: bool = False,
             max_tokens: int = DEFAULT_MAX_TOKENS,
             temperature: float = DEFAULT_TEMPERATURE) -> Dict[str, Any]:
        """
        发送聊天请求
        
        Args:
            messages: 消息列表，格式 [{"role": "user|assistant", "content": "..."}]
            model: 模型名称（默认 DeepSeek-R1）
            stream: 是否流式响应（默认 False）
            max_tokens: 最大生成 token 数
            temperature: 温度参数（0-1）
        
        Returns:
            API 响应字典，包含 choices 等字段
            
        Raises:
            如果请求失败，返回包含 error 字段的字典
        """
        url = f"{self.BASE_URL}{self.CHAT_ENDPOINT}"
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        try:
            resp = requests.post(
                url, 
                headers=self._get_headers(), 
                json=payload, 
                timeout=self.REQUEST_TIMEOUT
            )
            
            if resp.status_code == 200:
                return resp.json()
            else:
                return {
                    "error": True,
                    "status_code": resp.status_code,
                    "message": resp.text[:500]
                }
                
        except requests.exceptions.Timeout:
            return {"error": True, "message": f"请求超时 (>{self.REQUEST_TIMEOUT}s)"}
        except requests.exceptions.RequestException as e:
            return {"error": True, "message": f"请求异常: {str(e)}"}
    
    def chat_stream(self,
                   messages: List[Dict[str, str]],
                   model: str = DEFAULT_MODEL,
                   max_tokens: int = DEFAULT_MAX_TOKENS) -> Iterator[str]:
        """
        流式聊天（逐字返回）
        
        Args:
            messages: 消息列表
            model: 模型名称
            max_tokens: 最大生成 token 数
        
        Yields:
            每个 chunk 的 content 内容（字符串）
        """
        url = f"{self.BASE_URL}{self.CHAT_ENDPOINT}"
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "max_tokens": max_tokens
        }
        
        try:
            resp = requests.post(
                url,
                headers=self._get_headers(),
                json=payload,
                stream=True,
                timeout=self.REQUEST_TIMEOUT
            )
            
            for line in resp.iter_lines():
                if not line:
                    continue
                    
                line_str = line.decode('utf-8')
                
                # SSE 格式: data: {...}
                if line_str.startswith('data: '):
                    data = line_str[6:]  # 去掉 "data: "
                    
                    if data == '[DONE]':
                        break
                        
                    try:
                        chunk = json.loads(data)
                        if 'choices' in chunk and len(chunk['choices']) > 0:
                            delta = chunk['choices'][0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        continue
                        
        except requests.exceptions.Timeout:
            yield f"\n[错误: 请求超时 (>{self.REQUEST_TIMEOUT}s)]"
        except Exception as e:
            yield f"\n[错误: {str(e)}]"


# CLI 入口
def main():
    """命令行工具"""
    import sys
    
    # 解析参数
    stream_mode = "--stream" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    
    if not args:
        print("Usage: python -m src.client [--stream] '你的问题'")
        print("Environment: SSP_ACCESS_KEY, SSP_SECRET_KEY")
        sys.exit(1)
    
    prompt = args[0]
    
    # 创建客户端
    try:
        client = SSPDeepSeekClient()
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # 获取 Token 并显示
    token = client.auth.get_token()
    print(f"Token: {token[:30]}...\n")
    
    messages = [{"role": "user", "content": prompt}]
    
    if stream_mode:
        print("流式输出:\n")
        for chunk in client.chat_stream(messages):
            print(chunk, end="", flush=True)
        print()
    else:
        print("普通模式:\n")
        start = time.time()
        result = client.chat(messages)
        elapsed = time.time() - start
        
        if result.get("error"):
            print(f"错误: {result.get('message', 'Unknown error')}")
            print(f"Status: {result.get('status_code', 'N/A')}")
        else:
            content = result['choices'][0]['message']['content']
            print(content)
            print(f"\n[{elapsed:.2f}s]")


if __name__ == "__main__":
    main()
