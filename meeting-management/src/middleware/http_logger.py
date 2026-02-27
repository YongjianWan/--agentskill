# -*- coding: utf-8 -*-
"""
HTTP 请求日志中间件

功能:
- 记录所有 HTTP 请求和响应
- 显示请求耗时
- 统一时间格式
- 便于性能分析和问题排查

使用方法:
    from middleware import HTTPLoggerMiddleware
    app.add_middleware(HTTPLoggerMiddleware)

注意: 必须在 CORS 之后添加！
"""

import time
import json
from typing import Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from logger_config import get_logger

logger = get_logger(__name__)


class HTTPLoggerMiddleware(BaseHTTPMiddleware):
    """
    HTTP 请求日志中间件
    
    记录内容:
    - 请求方法、路径、查询参数
    - 客户端 IP
    - User-Agent
    - 响应状态码
    - 请求耗时
    - 错误详情（如果有）
    """
    
    def __init__(
        self,
        app: ASGIApp,
        exclude_paths: Optional[list] = None,
        slow_threshold: float = 1.0  # 慢请求阈值（秒）
    ):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/docs",      # 排除文档页面
            "/redoc",     # 排除 ReDoc
            "/openapi.json",  # 排除 OpenAPI 规范
            "/system/health",  # 排除健康检查（太多）
        ]
        self.slow_threshold = slow_threshold
    
    def _should_log(self, path: str) -> bool:
        """检查是否应该记录此路径"""
        for exclude in self.exclude_paths:
            if path.startswith(exclude):
                return False
        return True
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # 开始时间
        start_time = time.time()
        
        # 请求信息
        method = request.method
        path = request.url.path
        query_params = str(request.query_params)
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # 跳过不需要记录的路径
        if not self._should_log(path):
            return await call_next(request)
        
        # 生成请求 ID
        request_id = f"{int(start_time * 1000)}"
        request.state.request_id = request_id
        
        # 记录请求开始
        logger.info(
            f"[{request_id}] ➡️  {method} {path} | "
            f"IP: {client_ip} | UA: {user_agent[:50]}..."
        )
        
        try:
            # 执行请求
            response = await call_next(request)
            
            # 计算耗时
            process_time = time.time() - start_time
            
            # 状态码颜色
            status_code = response.status_code
            if status_code < 400:
                status_icon = "✅"
            elif status_code < 500:
                status_icon = "⚠️"
            else:
                status_icon = "❌"
            
            # 慢请求警告
            slow_warning = ""
            if process_time > self.slow_threshold:
                slow_warning = f" [SLOW >{self.slow_threshold}s]"
            
            # 记录响应
            logger.info(
                f"[{request_id}] {status_icon} {method} {path} | "
                f"Status: {status_code} | "
                f"Time: {process_time:.3f}s{slow_warning}"
            )
            
            # 添加响应头
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            # 计算耗时
            process_time = time.time() - start_time
            
            # 记录错误
            logger.error(
                f"[{request_id}] ❌ {method} {path} | "
                f"Error: {type(e).__name__}: {str(e)[:100]} | "
                f"Time: {process_time:.3f}s",
                exc_info=True
            )
            
            # 重新抛出异常，让错误处理中间件处理
            raise
