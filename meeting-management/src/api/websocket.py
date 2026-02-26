"""
WebSocket 路由处理
实时音频流接收与转写推送
"""

import json
import base64
import asyncio
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from logger_config import get_logger
from database.connection import AsyncSessionLocal
from models.meeting import MeetingModel, MeetingStatus
from services.websocket_manager import websocket_manager
from services.transcription_service import transcription_service

logger = get_logger(__name__)
router = APIRouter()

# WebSocket 消息大小限制 (1MB)
MAX_MESSAGE_SIZE = 1024 * 1024


async def handle_audio_message(session, data: dict, meeting: MeetingModel):
    """
    处理音频数据消息
    
    流程：
    1. 解码 Base64 音频数据
    2. 添加到音频缓存
    3. 检查是否满足转写条件
    4. 执行转写并推送结果
    """
    try:
        seq = data.get("seq", 0)
        timestamp_ms = data.get("timestamp_ms", 0)
        mime_type = data.get("mime_type", "audio/webm")
        audio_b64 = data.get("data", "")
        
        if not audio_b64:
            logger.warning(f"[{session.session_id}] 收到空音频数据")
            return
        
        # Base64 解码
        try:
            audio_data = base64.b64decode(audio_b64)
        except Exception as e:
            logger.error(f"[{session.session_id}] 音频 Base64 解码失败: {e}")
            await websocket_manager.send_error(
                session.session_id,
                "AUDIO_DECODE_ERROR",
                "音频数据解码失败",
                recoverable=True
            )
            return
        
        # 添加到音频缓存
        added = session.add_audio_chunk(seq, timestamp_ms, audio_data, mime_type)
        
        # 如果缓存已满，立即触发转写
        if not added:
            logger.warning(f"[{session.session_id}] 音频缓存已满，立即触发转写")
            await perform_transcription(session, meeting)
            # 再次尝试添加
            added = session.add_audio_chunk(seq, timestamp_ms, audio_data, mime_type)
        
        # 检查是否满足转写条件
        if session.should_transcribe():
            await perform_transcription(session, meeting)
        
    except Exception as e:
        logger.error(f"[{session.session_id}] 处理音频消息失败: {e}", exc_info=True)
        await websocket_manager.send_error(
            session.session_id,
            "PROCESSING_ERROR",
            f"音频处理失败: {str(e)}",
            recoverable=True
        )


async def perform_transcription(session, meeting: MeetingModel):
    """
    执行转写并推送结果
    
    1. 获取并清空音频缓存
    2. 调用转写服务
    3. 保存转写结果到数据库
    4. 推送转写结果到客户端
    """
    try:
        # 获取音频缓存
        audio_chunks = session.get_and_clear_buffer()
        if not audio_chunks:
            return
        
        # 计算基准时间戳
        base_timestamp_ms = audio_chunks[0].get("timestamp_ms", 0)
        
        logger.info(f"[{session.session_id}] 开始转写: {len(audio_chunks)} 段音频")
        
        # 调用转写服务（带超时保护）
        try:
            results = await asyncio.wait_for(
                transcription_service.transcribe(audio_chunks, base_timestamp_ms),
                timeout=60.0  # 转写超时 60 秒
            )
        except asyncio.TimeoutError:
            logger.error(f"[{session.session_id}] 转写服务超时")
            await websocket_manager.send_error(
                session.session_id,
                "TRANSCRIPTION_TIMEOUT",
                "转写服务响应超时，请稍后重试",
                recoverable=True
            )
            # 将音频数据放回缓存，下次重试
            for chunk in audio_chunks:
                session.audio_buffer.append(chunk)
                session.audio_buffer_size += len(chunk.get("data", b""))
            return
        
        if not results:
            logger.warning(f"[{session.session_id}] 转写结果为空")
            return
        
        # 保存到数据库并推送
        async with AsyncSessionLocal() as db:
            # 重新加载会议记录
            result = await db.execute(
                select(MeetingModel).where(MeetingModel.session_id == session.session_id)
            )
            meeting = result.scalar_one_or_none()
            
            if not meeting:
                logger.error(f"[{session.session_id}] 会议记录不存在")
                return
            
            for transcript_result in results:
                # 添加到会话
                segment = session.add_transcript(
                    text=transcript_result.text,
                    start_ms=transcript_result.start_ms,
                    end_ms=transcript_result.end_ms,
                    speaker_id=transcript_result.speaker_id
                )
                
                # 更新数据库
                meeting.transcript_segments = [
                    seg.model_dump() for seg in session.transcript_segments
                ]
                meeting.full_text = session.full_text
                meeting.updated_at = datetime.utcnow()
                
                # 推送实时转写结果
                await websocket_manager.send_transcript(
                    session.session_id,
                    segment,
                    is_final=True
                )
            
            await db.commit()
        
        logger.info(f"[{session.session_id}] 转写完成: {len(results)} 句")
        
        # 推送状态更新
        await websocket_manager.broadcast_status(
            session.session_id,
            MeetingStatus.RECORDING,
            session.transcript_segments[-1].end_time_ms if session.transcript_segments else 0,
            len(session.transcript_segments)
        )
        
    except Exception as e:
        logger.error(f"[{session.session_id}] 转写失败: {e}", exc_info=True)
        await websocket_manager.send_error(
            session.session_id,
            "TRANSCRIPTION_ERROR",
            f"转写失败: {str(e)}",
            recoverable=True
        )


async def handle_control_message(session, data: dict):
    """处理控制消息（ping等）"""
    msg_type = data.get("type")
    
    if msg_type == "ping":
        await session.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})
    
    elif msg_type == "get_status":
        # 返回当前状态
        await session.send_json({
            "type": "status",
            "status": "recording" if session.is_active else "inactive",
            "transcript_count": len(session.transcript_segments),
            "audio_buffer_size": session.audio_buffer_size
        })
    
    else:
        logger.warning(f"[{session.session_id}] 未知控制消息类型: {msg_type}")


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
    - 上行: {"type": "audio", "seq": 1, "timestamp_ms": 1000, "data": "base64...", "mime_type": "audio/webm"}
    - 下行: {"type": "transcript", "segment_id": "seg_001", "text": "...", "timestamp_ms": 1000, "is_final": true}
    """
    session = None
    meeting = None
    connection_accepted = False
    
    try:
        # 1. 验证会议存在且属于该用户
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(MeetingModel).where(MeetingModel.session_id == session_id)
            )
            meeting = result.scalar_one_or_none()
            
            if not meeting:
                await websocket.accept()
                connection_accepted = True
                await websocket.send_json({
                    "type": "error",
                    "code": "SESSION_NOT_FOUND",
                    "message": "会议不存在"
                })
                await websocket.close(code=4004)
                return
            
            if meeting.user_id != user_id:
                await websocket.accept()
                connection_accepted = True
                await websocket.send_json({
                    "type": "error",
                    "code": "UNAUTHORIZED",
                    "message": "无权访问该会议"
                })
                await websocket.close(code=4003)
                return
        
        # 2. 建立 WebSocket 连接
        session = await websocket_manager.connect(session_id, user_id, websocket)
        
        # 3. 恢复历史转写数据（如果有）
        if meeting.transcript_segments:
            for seg_data in meeting.transcript_segments:
                # 重新构建会话中的转写片段
                from models.meeting import TranscriptSegment
                segment = TranscriptSegment(**seg_data)
                session.transcript_segments.append(segment)
                if session.full_text:
                    session.full_text += "\n"
                session.full_text += f"[{segment.start_time_ms//60000:02d}:{(segment.start_time_ms//1000)%60:02d}] {segment.text}"
        
        # 4. 消息循环
        while True:
            try:
                # 接收消息（带大小限制）
                message = await websocket.receive()
                
                # 检查消息大小
                if "text" in message:
                    msg_size = len(message["text"].encode('utf-8'))
                    if msg_size > MAX_MESSAGE_SIZE:
                        logger.warning(f"[{session_id}] 消息过大: {msg_size} bytes")
                        await websocket_manager.send_error(
                            session_id,
                            "MESSAGE_TOO_LARGE",
                            f"消息过大，最大允许 {MAX_MESSAGE_SIZE} bytes",
                            recoverable=True
                        )
                        continue
                
                # 处理文本消息（JSON）
                if "text" in message:
                    data = json.loads(message["text"])
                    msg_type = data.get("type")
                    
                    if msg_type == "audio":
                        await handle_audio_message(session, data, meeting)
                    else:
                        await handle_control_message(session, data)
                
                # 处理二进制消息（原始音频数据）
                elif "bytes" in message:
                    msg_size = len(message["bytes"])
                    if msg_size > MAX_MESSAGE_SIZE:
                        logger.warning(f"[{session_id}] 二进制消息过大: {msg_size} bytes")
                        await websocket_manager.send_error(
                            session_id,
                            "MESSAGE_TOO_LARGE",
                            f"消息过大，最大允许 {MAX_MESSAGE_SIZE} bytes",
                            recoverable=True
                        )
                        continue
                    
                    # TODO: 支持原始二进制音频数据
                    logger.warning(f"[{session_id}] 二进制音频数据暂未支持")
                    await websocket_manager.send_error(
                        session_id,
                        "UNSUPPORTED_FORMAT",
                        "二进制音频格式暂未支持，请使用 Base64 JSON 格式",
                        recoverable=True
                    )
                
            except json.JSONDecodeError as e:
                logger.error(f"[{session_id}] JSON 解析失败: {e}")
                await websocket_manager.send_error(
                    session_id,
                    "INVALID_MESSAGE",
                    "消息格式错误",
                    recoverable=True
                )
            
            except Exception as e:
                logger.error(f"[{session_id}] 消息处理异常: {e}", exc_info=True)
                await websocket_manager.send_error(
                    session_id,
                    "PROCESSING_ERROR",
                    f"处理失败: {str(e)}",
                    recoverable=True
                )
    
    except WebSocketDisconnect:
        logger.info(f"[{session_id}] 客户端断开连接")
        await websocket_manager.disconnect(session_id)
    
    except Exception as e:
        logger.error(f"[{session_id}] WebSocket 异常: {e}", exc_info=True)
        if session and connection_accepted:
            try:
                await websocket_manager.send_error(
                    session_id,
                    "INTERNAL_ERROR",
                    "服务器内部错误",
                    recoverable=False
                )
            except Exception:
                pass  # 连接可能已关闭
        await websocket_manager.close_session(session_id, reason=f"异常: {e}")


async def flush_remaining_audio(session_id: str):
    """
    刷新剩余音频缓存（会议结束时调用）
    
    确保所有缓存的音频都被转写并保存
    """
    session = websocket_manager.get_session(session_id)
    if not session or not session.audio_buffer:
        return
    
    logger.info(f"[{session_id}] 刷新剩余音频: {len(session.audio_buffer)} 段")
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(MeetingModel).where(MeetingModel.session_id == session_id)
        )
        meeting = result.scalar_one_or_none()
        
        if meeting:
            await perform_transcription(session, meeting)
