# -*- coding: utf-8 -*-
"""
系统 API 路由
健康检查、状态查询
"""

import shutil
import time
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, Request

from logger_config import get_logger

logger = get_logger(__name__)

router = APIRouter()

# 版本号
VERSION = "1.2.0"

# 磁盘空间阈值
DISK_MIN_FREE_GB = 1  # 最小剩余空间 1GB
DISK_MAX_USAGE_PERCENT = 90  # 最大使用率 90%


def _get_disk_status(output_dir: str = "output") -> Dict[str, Any]:
    """获取磁盘状态"""
    try:
        # 获取 output 目录所在磁盘的使用情况
        output_path = Path(output_dir).resolve()
        output_path.mkdir(parents=True, exist_ok=True)
        
        disk_usage = shutil.disk_usage(output_path)
        total_gb = disk_usage.total / (1024 ** 3)
        free_gb = disk_usage.free / (1024 ** 3)
        used_gb = disk_usage.used / (1024 ** 3)
        usage_percent = (disk_usage.used / disk_usage.total) * 100
        
        # 判断状态
        if free_gb < DISK_MIN_FREE_GB or usage_percent > DISK_MAX_USAGE_PERCENT:
            status = "degraded"
        else:
            status = "ok"
        
        return {
            "status": status,
            "total_gb": round(total_gb, 2),
            "free_gb": round(free_gb, 2),
            "used_gb": round(used_gb, 2),
            "usage_percent": round(usage_percent, 2)
        }
    except Exception as e:
        logger.error(f"获取磁盘状态失败: {e}")
        return {
            "status": "error",
            "error": str(e),
            "total_gb": 0,
            "free_gb": 0,
            "used_gb": 0,
            "usage_percent": 0
        }


def _get_gpu_available() -> bool:
    """检查 GPU (CUDA) 是否可用"""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


def _determine_overall_status(components: Dict[str, Any]) -> str:
    """
    确定整体状态
    
    状态分级:
    - error: 关键组件故障
    - degraded: 非关键问题（磁盘空间不足、模型未加载）
    - ok: 一切正常
    """
    # 检查是否有 error 状态
    for name, comp in components.items():
        if comp.get("status") == "error":
            return "error"
    
    # 检查是否有 degraded 状态
    for name, comp in components.items():
        if comp.get("status") == "degraded":
            return "degraded"
    
    return "ok"


@router.get("/health")
async def health_check(request: Request):
    """
    健康检查接口
    
    返回系统各组件的健康状态:
    - api: API 服务状态
    - database: 数据库连接状态
    - model: 转写模型状态（Whisper/Mock）
    - disk: 磁盘空间状态
    - websocket: WebSocket 连接状态
    """
    app = request.app
    
    # 计算运行时间
    startup_time = getattr(app.state, "startup_time", None)
    uptime_seconds = 0
    if startup_time:
        uptime_seconds = int(time.time() - startup_time)
    
    # 获取服务实例
    transcription_svc = getattr(app.state, "transcription_service", None)
    ws_manager = getattr(app.state, "websocket_manager", None)
    
    # 1. API 状态（自身状态，始终 ok）
    api_status = {"status": "ok"}
    
    # 2. 数据库状态（简化处理，假设数据库正常）
    # TODO: 可以添加实际的数据库连接检查
    database_status = {"status": "ok"}
    
    # 3. 模型状态
    model_status = {
        "status": "ok",
        "name": "unknown",
        "loaded": False,
        "device": "cpu",
        "gpu_available": False
    }
    
    if transcription_svc:
        svc_status = transcription_svc.get_status()
        model_status["name"] = svc_status.get("config", {}).get("model", "unknown")
        model_status["device"] = svc_status.get("config", {}).get("device", "cpu")
        model_status["loaded"] = svc_status.get("whisper_loaded", False)
        model_status["gpu_available"] = _get_gpu_available()
        
        # 判断模型状态
        if svc_status.get("mode") == "whisper" and not model_status["loaded"]:
            model_status["status"] = "degraded"
    
    # 4. 磁盘状态
    disk_status = _get_disk_status()
    
    # 5. WebSocket 状态
    websocket_status = {"active_sessions": 0}
    if ws_manager:
        websocket_status["active_sessions"] = ws_manager.get_active_sessions_count()
    
    # 组装组件状态
    components = {
        "api": api_status,
        "database": database_status,
        "model": model_status,
        "disk": disk_status,
        "websocket": websocket_status
    }
    
    # 确定整体状态
    overall_status = _determine_overall_status(components)
    
    return {
        "code": 0,
        "data": {
            "status": overall_status,
            "version": VERSION,
            "uptime_seconds": uptime_seconds,
            "components": components
        }
    }


@router.get("/version")
async def get_version():
    """获取版本信息"""
    return {
        "code": 0,
        "data": {
            "version": VERSION,
            "build_time": "2026-02-25",
            "features": [
                "rest_api",
                "websocket",
                "transcription",
                # "ai_minutes"      # Phase 4后启用
            ]
        }
    }
