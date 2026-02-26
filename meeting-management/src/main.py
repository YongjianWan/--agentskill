#!/usr/bin/env python3
"""
Meeting Management Backend API
FastAPI + WebSocket + SQLite/瀚高HighGoDB

启动: uvicorn main:app --reload --port 8765

环境变量:
  DB_TYPE=sqlite|highgo  # 切换数据库
  HIGHGO_HOST=localhost  # 瀚高地址
  HIGHGO_PORT=5866       # 瀚高端口
  HIGHGO_USER=highgo     # 瀚高用户名
  HIGHGO_PASSWORD=xxx    # 瀚高密码
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(Path(__file__).parent.parent / ".env")

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.meetings import router as meetings_router
from api.upload import router as upload_router
from api.system import router as system_router
from api.websocket import router as websocket_router
from database.connection import init_db
from services.websocket_manager import websocket_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    await init_db()
    print("✅ Database initialized")
    
    # 启动 WebSocket 管理器
    websocket_manager.start()
    
    yield
    
    # 关闭时清理
    websocket_manager.stop()
    print("👋 Server shutting down")


app = FastAPI(
    title="Meeting Management API",
    description="灵犀会议管理后端服务 - 实时录音转写与纪要生成",
    version="1.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(meetings_router, prefix="/api/v1", tags=["meetings"])
app.include_router(upload_router, prefix="/api/v1", tags=["upload"])
app.include_router(system_router, prefix="/api/v1", tags=["system"])
app.include_router(websocket_router, prefix="/api/v1", tags=["websocket"])


@app.get("/")
async def root():
    """根路径 - API信息"""
    return {
        "name": "Meeting Management API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8765, reload=True)
