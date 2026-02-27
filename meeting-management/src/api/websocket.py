# -*- coding: utf-8 -*-
"""
WebSocket 路由处理
实时音频流接收与转写推送
"""

import json
import base64
import asyncio
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from logger_config import get_logger
from services.websocket_manager import websocket_manager

logger = get_logger(__name__)
router = APIRouter()

# WebSocket 消息大小限制 (1MB)
MAX_MESSAGE_SIZE = 1024 * 1024

# 会话处理锁，确保每个会话的消息串行处理
_session_locks = {}

# 会话生命周期锁，防止 init/finalize 并发冲突
_lifecycle_locks = {}


async def handle_start_message(websocket: WebSocket, session_id: str, data: dict):
    """
    处理开始会议消息
    
    创建会议会话，初始化音频文件
    """
    # 获取生命周期锁，确保与 end 互斥
    lock = _get_lifecycle_lock(session_id)
    
    async with lock:
        try:
            title = data.get("title", "未命名会议")
            user_id = data.get("user_id", "anonymous")
            
            # 导入并调用 meeting_skill 初始化
            from meeting_skill import init_meeting_session
            audio_path = init_meeting_session(session_id, title=title, user_id=user_id)
            
            # 建立 WebSocket 连接
            await websocket_manager.connect(session_id, user_id, websocket)
            
            # 发送 started 消息
            await websocket_manager.send_custom_message(session_id, {
                "type": "started",
                "meeting_id": session_id,
                "audio_path": audio_path
            })
            
            logger.info(f"[{session_id}] 会议已启动: {title}")
            
        except Exception as e:
            logger.error(f"[{session_id}] 启动会议失败: {e}", exc_info=True)
            await websocket.send_json({
                "type": "error",
                "code": "START_FAILED",
                "message": f"启动会议失败: {str(e)}"
            })


def _get_session_lock(session_id: str) -> asyncio.Lock:
    """获取会话的锁，不存在则创建"""
    if session_id not in _session_locks:
        _session_locks[session_id] = asyncio.Lock()
    return _session_locks[session_id]


def _get_lifecycle_lock(session_id: str) -> asyncio.Lock:
    """获取会话生命周期锁，确保 init/finalize 互斥"""
    if session_id not in _lifecycle_locks:
        _lifecycle_locks[session_id] = asyncio.Lock()
    return _lifecycle_locks[session_id]


async def handle_chunk_message(session_id: str, data: dict):
    """
    处理音频块消息
    
    解码音频数据，追加到文件，触发转写
    """
    # 获取会话锁，确保与 end 消息互斥
    lock = _get_session_lock(session_id)
    
    # 如果锁被占用（正在处理 end），则跳过此 chunk
    if lock.locked():
        logger.debug(f"[{session_id}] 会话正在结束，跳过 chunk")
        return
    
    async with lock:
        try:
            seq = data.get("sequence", 0)
            audio_b64 = data.get("data", "")
            
            if not audio_b64:
                logger.warning(f"[{session_id}] 收到空音频数据")
                return
            
            # Base64 解码
            try:
                chunk_bytes = base64.b64decode(audio_b64)
            except Exception as e:
                logger.error(f"[{session_id}] 音频 Base64 解码失败: {e}")
                await websocket_manager.send_error(
                    session_id,
                    "DECODE_ERROR",
                    "音频解码失败",
                    recoverable=True
                )
                return
            
            # 调用 meeting_skill 追加音频块（同步函数用 run_in_executor）
            from meeting_skill import append_audio_chunk
            transcript_text = await asyncio.get_event_loop().run_in_executor(
                None, append_audio_chunk, session_id, chunk_bytes, seq
            )
            
            # 如果有转写结果，推送客户端
            if transcript_text:
                await websocket_manager.send_custom_message(session_id, {
                    "type": "transcript",
                    "text": transcript_text,
                    "sequence": seq,
                    "is_final": False
                })
            
        except Exception as e:
            logger.error(f"[{session_id}] 处理音频块失败: {e}", exc_info=True)
            await websocket_manager.send_error(
                session_id,
                "CHUNK_ERROR",
                f"处理音频块失败: {str(e)}",
                recoverable=True
            )


async def handle_end_message(session_id: str):
    """
    处理结束会议消息
    
    关闭文件，全量转写，生成纪要（带实时进度推送）
    """
    # 获取生命周期锁，确保与 start 互斥
    lifecycle_lock = _get_lifecycle_lock(session_id)
    
    # 获取会话锁，确保与 chunk 消息互斥
    chunk_lock = _get_session_lock(session_id)
    
    async with lifecycle_lock:
        async with chunk_lock:
            try:
                logger.info(f"[{session_id}] 结束会议...")
                
                # 定义进度回调函数（在同步代码中触发异步发送）
                loop = asyncio.get_event_loop()
                def progress_callback(step: str, message: str):
                    # 使用 run_coroutine_threadsafe 在同步回调中发送消息
                    asyncio.run_coroutine_threadsafe(
                        websocket_manager.send_custom_message(session_id, {
                            "type": "progress",
                            "step": step,
                            "message": message,
                            "timestamp": datetime.utcnow().isoformat()
                        }),
                        loop
                    )
                
                # 发送开始处理消息
                await websocket_manager.send_custom_message(session_id, {
                    "type": "processing",
                    "status": "started",
                    "message": "开始生成会议纪要..."
                })
                
                # 调用 meeting_skill 结束会议（同步函数用 run_in_executor）
                from meeting_skill import finalize_meeting
                logger.info(f"[{session_id}] 调用 finalize_meeting...")
                result = await asyncio.get_event_loop().run_in_executor(
                    None, finalize_meeting, session_id, None, progress_callback
                )
                logger.info(f"[{session_id}] finalize_meeting 完成")
                
                # 发送 completed 消息
                # 检查结果是否使用了降级方案
                is_fallback = result.get("_ai_failed", False) if isinstance(result, dict) else False
                fallback_reason = result.get("_fail_reason", "") if isinstance(result, dict) else ""
                
                await websocket_manager.send_custom_message(session_id, {
                    "type": "completed",
                    "meeting_id": session_id,
                    "full_text": result["full_text"],
                    "minutes_path": result["minutes_path"],
                    "chunk_count": result["chunk_count"],
                    "ai_success": not is_fallback,
                    "fallback_reason": fallback_reason if is_fallback else None
                })
                
                # 如果使用了降级方案，额外发送一个警告
                if is_fallback:
                    await websocket_manager.send_custom_message(session_id, {
                        "type": "warning",
                        "code": "AI_FALLBACK",
                        "message": f"AI生成失败，使用基础模板: {fallback_reason}",
                        "suggestion": "请检查：1.录音是否有声音 2.麦克风权限 3.网络连接"
                    })
                
                # 关闭 WebSocket 连接
                await websocket_manager.close_session(session_id, reason="会议正常结束")
                
                logger.info(f"[{session_id}] 会议已结束，纪要: {result['minutes_path']}")
                
            except Exception as e:
                logger.error(f"[{session_id}] 结束会议失败: {e}", exc_info=True)
                await websocket_manager.send_error(
                    session_id,
                    "END_FAILED",
                    f"结束会议失败: {str(e)}",
                    recoverable=False
                )
                # 即使失败也关闭会话
                await websocket_manager.close_session(session_id, reason=f"结束失败: {e}")


async def handle_control_message(session_id: str, data: dict):
    """处理控制消息（ping等）"""
    msg_type = data.get("type")
    
    if msg_type == "ping":
        await websocket_manager.send_json(session_id, {
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    elif msg_type == "get_status":
        # 获取会话状态
        session = websocket_manager.get_session(session_id)
        if session:
            await websocket_manager.send_json(session_id, {
                "type": "status",
                "status": "recording" if session.is_active else "inactive",
                "transcript_count": len(session.transcript_segments),
                "audio_buffer_size": session.audio_buffer_size
            })
    
    elif msg_type == "select_minutes_style":
        # 选择纪要模板风格
        style = data.get("style", "detailed")
        from prompts import validate_template, list_templates
        
        if validate_template(style):
            # 保存到会话
            session = websocket_manager.get_session(session_id)
            if session:
                session.minutes_style = style
                await websocket_manager.send_json(session_id, {
                    "type": "style_selected",
                    "style": style,
                    "message": f"已选择模板: {style}"
                })
                logger.info(f"[{session_id}] 纪要模板已选择: {style}")
        else:
            await websocket_manager.send_json(session_id, {
                "type": "error",
                "code": "INVALID_STYLE",
                "message": f"无效的模板风格: {style}",
                "available_styles": [t["id"] for t in list_templates()]
            })
    
    else:
        logger.warning(f"[{session_id}] 未知控制消息类型: {msg_type}")


@router.websocket("/ws/meeting/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    user_id: str = Query(..., description="用户ID")
):
    """
    WebSocket 实时音频流处理端点
    
    连接地址: ws://host:8765/api/v1/ws/meeting/{session_id}?user_id={user_id}
    
    消息协议:
    - 上行:
      - {"type": "start", "title": "会议标题"} - 开始会议
      - {"type": "chunk", "sequence": 1, "data": "base64..."} - 音频块
      - {"type": "end"} - 结束会议
      - {"type": "ping"} - 心跳
    - 下行:
      - {"type": "started", "meeting_id": "..."} - 会议已启动
      - {"type": "transcript", "text": "...", "sequence": 1} - 转写结果
      - {"type": "completed", "full_text": "...", "minutes_path": "..."} - 会议完成
      - {"type": "error", "code": "...", "message": "..."} - 错误
    
    Phase 4 新增:
    - 上行: {"type": "select_minutes_style", "style": "detailed"} - 选择纪要模板
    - 下行: {"type": "style_selected", "style": "..."} - 模板选择确认
    """
    connection_accepted = False
    
    try:
        # 首先接受 WebSocket 连接
        await websocket.accept()
        logger.info(f"[{session_id}] WebSocket 连接已接受")
        
        # 消息循环
        while True:
            try:
                # 接收消息（带大小限制）
                message = await websocket.receive()
                
                # 检查消息大小
                if "text" in message:
                    msg_size = len(message["text"].encode('utf-8'))
                    if msg_size > MAX_MESSAGE_SIZE:
                        logger.warning(f"[{session_id}] 消息过大: {msg_size} bytes")
                        await websocket.send_json({
                            "type": "error",
                            "code": "MESSAGE_TOO_LARGE",
                            "message": f"消息过大，最大允许 {MAX_MESSAGE_SIZE} bytes"
                        })
                        continue
                
                # 处理文本消息（JSON）
                if "text" in message:
                    data = json.loads(message["text"])
                    msg_type = data.get("type")
                    
                    # 新消息路由
                    if msg_type == "start":
                        await handle_start_message(websocket, session_id, data)
                        connection_accepted = True
                    elif msg_type == "chunk":
                        await handle_chunk_message(session_id, data)
                    elif msg_type == "end":
                        await handle_end_message(session_id)
                        break  # 结束消息循环
                    else:
                        await handle_control_message(session_id, data)
                
                # 处理二进制消息（暂不支持）
                elif "bytes" in message:
                    msg_size = len(message["bytes"])
                    if msg_size > MAX_MESSAGE_SIZE:
                        logger.warning(f"[{session_id}] 二进制消息过大: {msg_size} bytes")
                        await websocket.send_json({
                            "type": "error",
                            "code": "MESSAGE_TOO_LARGE",
                            "message": f"消息过大，最大允许 {MAX_MESSAGE_SIZE} bytes"
                        })
                        continue
                    
                    logger.warning(f"[{session_id}] 二进制音频数据暂未支持")
                    await websocket.send_json({
                        "type": "error",
                        "code": "UNSUPPORTED_FORMAT",
                        "message": "二进制音频格式暂未支持，请使用 Base64 JSON 格式"
                    })
                
            except json.JSONDecodeError as e:
                logger.error(f"[{session_id}] JSON 解析失败: {e}")
                await websocket.send_json({
                    "type": "error",
                    "code": "INVALID_MESSAGE",
                    "message": "消息格式错误"
                })
            
            except Exception as e:
                logger.error(f"[{session_id}] 消息处理异常: {e}", exc_info=True)
                await websocket.send_json({
                    "type": "error",
                    "code": "PROCESSING_ERROR",
                    "message": f"处理失败: {str(e)}"
                })
    
    except WebSocketDisconnect:
        logger.info(f"[{session_id}] 客户端断开连接")
        # 清理 WebSocketManager 中的会话（重要：避免 CLOSE_WAIT）
        await websocket_manager.close_session(session_id, reason="客户端断开")
        # 如果会议还在进行中（有音频数据），自动结束会议
        from meeting_skill import _audio_sessions
        if session_id in _audio_sessions:
            session = _audio_sessions[session_id]
            # 【关键】先关闭文件句柄，避免 WinError 32
            fh = session.get("file_handle")
            if fh and not fh.closed:
                try:
                    fh.flush()
                    fh.close()
                    logger.info(f"[{session_id}] 断开连接时关闭音频文件句柄")
                except Exception as e:
                    logger.warning(f"[{session_id}] 关闭文件句柄失败: {e}")
            session["file_handle"] = None
            
            if session.get("chunk_count", 0) > 0:
                logger.warning(f"[{session_id}] 会议进行中客户端断开，自动结束会议")
                try:
                    await handle_end_message(session_id)
                except Exception as e:
                    logger.error(f"[{session_id}] 自动结束会议失败: {e}")
                    # 清理会话避免内存泄漏
                    if session_id in _audio_sessions:
                        del _audio_sessions[session_id]
            else:
                # 没有音频数据，直接清理
                del _audio_sessions[session_id]
    
    except Exception as e:
        logger.error(f"[{session_id}] WebSocket 异常: {e}", exc_info=True)
        if connection_accepted:
            try:
                await websocket.send_json({
                    "type": "error",
                    "code": "INTERNAL_ERROR",
                    "message": "服务器内部错误"
                })
            except Exception:
                pass  # 连接可能已关闭
    
    finally:
        # 清理会话锁，避免内存泄漏
        if session_id in _session_locks:
            del _session_locks[session_id]
            logger.debug(f"[{session_id}] 会话锁已清理")
        if session_id in _lifecycle_locks:
            del _lifecycle_locks[session_id]
            logger.debug(f"[{session_id}] 生命周期锁已清理")
