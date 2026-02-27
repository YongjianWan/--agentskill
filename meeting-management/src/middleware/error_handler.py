# -*- coding: utf-8 -*-
"""
全局错误处理中间件

功能:
- 捕获所有未处理的异常
- 返回统一的错误格式
- 包含详细的错误信息（开发模式）
- 便于前端排查问题

使用方法:
    from middleware import ErrorHandlerMiddleware
    app.add_middleware(ErrorHandlerMiddleware)
"""

import traceback
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from logger_config import get_logger

logger = get_logger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    全局错误处理中间件
    
    返回格式:
    {
        "code": -1,
        "message": "错误描述",
        "data": {
            "error_type": "异常类型",
            "error_detail": "详细错误信息（仅开发模式）",
            "request_id": "请求ID",
            "suggestion": "解决建议"
        }
    }
    """
    
    def __init__(self, app: ASGIApp, debug: bool = True):
        super().__init__(app)
        self.debug = debug
    
    def _get_error_suggestion(self, error_type: str, error_message: str) -> str:
        """根据错误类型返回解决建议"""
        suggestions = {
            "ValidationError": "请求参数格式错误，请检查 API 文档",
            "HTTPException": "请求不符合规范，请检查请求方法和参数",
            "ConnectionError": "数据库连接失败，请联系管理员",
            "TimeoutError": "请求超时，请稍后重试",
            "ValueError": "参数值错误，请检查输入数据",
            "KeyError": "缺少必要参数，请检查 API 文档",
            "FileNotFoundError": "请求的资源不存在",
        }
        
        for error_name, suggestion in suggestions.items():
            if error_name in error_type:
                return suggestion
        
        return "未知错误，请联系后端开发人员"
    
    async def dispatch(self, request: Request, call_next) -> JSONResponse:
        try:
            return await call_next(request)
            
        except Exception as exc:
            # 获取请求 ID
            request_id = getattr(request.state, 'request_id', 'unknown')
            
            # 获取异常信息
            error_type = type(exc).__name__
            error_message = str(exc)
            
            # 获取堆栈信息（仅开发模式）
            error_detail = traceback.format_exc() if self.debug else None
            
            # 构建错误响应
            error_data = {
                "error_type": error_type,
                "error_message": error_message,
                "request_id": request_id,
                "suggestion": self._get_error_suggestion(error_type, error_message),
            }
            
            # 开发模式下添加堆栈
            if self.debug:
                error_data["error_detail"] = error_detail
                error_data["path"] = str(request.url)
                error_data["method"] = request.method
            
            # 确定 HTTP 状态码
            status_code = 500
            if hasattr(exc, 'status_code'):
                status_code = exc.status_code
            elif error_type == 'ValidationError':
                status_code = 422
            elif error_type == 'FileNotFoundError':
                status_code = 404
            
            # 记录错误日志
            logger.error(
                f"[{request_id}] 未处理异常: {error_type}: {error_message[:200]}",
                exc_info=True
            )
            
            # 返回错误响应
            return JSONResponse(
                status_code=status_code,
                content={
                    "code": -1,
                    "message": f"服务器错误: {error_message[:100]}",
                    "data": error_data
                }
            )
