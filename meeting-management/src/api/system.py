"""
系统 API 路由
健康检查、状态查询
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "code": 0,
        "data": {
            "status": "healthy",
            "version": "1.0.0",
            "services": {
                "api": "ok",
                "database": "ok",
                "whisper": "not_ready",  # Phase 3后更新
                "ai": "not_ready"        # Phase 4后更新
            }
        }
    }


@router.get("/version")
async def get_version():
    """获取版本信息"""
    return {
        "code": 0,
        "data": {
            "version": "1.0.0",
            "build_time": "2026-02-25",
            "features": [
                "rest_api",
                # "websocket",      # Phase 2启用
                # "transcription",  # Phase 3启用
                # "ai_minutes"      # Phase 4启用
            ]
        }
    }
