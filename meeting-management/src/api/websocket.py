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


async def handle_start_message(websocket: WebSocket, session_id: str, data: dict):
    """
    处理开始会议消息
    
    创建会议会话，初始化音频文件
    """
    try:
        title = data.get("title", "未命名会议")
        user_id = data.get("user_id", "anonymous")
        
        # 导入并调用 meeting_skill 初始化
        from meeting_skill import init_meeting_session
        audio_path = init_meeting_session(session_id, title=title, user_id=user_id)
        
        # 建立 WebSocket 连接
        await websocket_manager.connect(session_id, user_id, websocket)
        
        # 发送 started 消息
        await websocket.send_json({
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


async def handle_chunk_message(session_id: str, data: dict):
    """
    处理音频块消息
    
    解码音频数据，追加到文件，触发转写
    """
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
            await websocket_manager.send_json(session_id, {
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
    
    关闭文件，全量转写，生成纪要
    """
    try:
        logger.info(f"[{session_id}] 结束会议...")
        
        # 调用 meeting_skill 结束会议（同步函数用 run_in_executor）
        from meeting_skill import finalize_meeting
        result = await asyncio.get_event_loop().run_in_executor(
            None, finalize_meeting, session_id
        )
        
        # 发送 completed 消息
        await websocket_manager.send_json(session_id, {
            "type": "completed",
            "meeting_id": session_id,
            "full_text": result["full_text"],
            "minutes_path": result["minutes_path"],
            "chunk_count": result["chunk_count"]
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
    """
    connection_accepted = False
    
    try:
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
        # 如果会议还在进行中，需要清理
        from meeting_skill import _audio_sessions
        if session_id in _audio_sessions:
            logger.warning(f"[{session_id}] 会议进行中客户端断开，清理资源")
            # 这里可以选择是否自动结束会议
            # await handle_end_message(session_id)
    
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
