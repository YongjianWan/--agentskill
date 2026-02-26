# -*- coding: utf-8 -*-
"""
WebSocket 连接管理器
管理会议实时音频流连接
"""

import asyncio
import json
import time
import uuid
from typing import Dict, Optional, List
from datetime import datetime

from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from logger_config import get_logger
from models.meeting import (
    MeetingStatus, WSTranscript, WSStatus, WSResult, WSError,
    TranscriptSegment
)

logger = get_logger(__name__)


class MeetingSession:
    """
    单个会议的 WebSocket 会话状态
    
    管理：
    - WebSocket 连接
    - 音频片段缓存
    - 转写文本累积
    - 会议状态跟踪
    """
    
    def __init__(self, session_id: str, user_id: str):
        self.session_id = session_id
        self.user_id = user_id
        self.websocket: Optional[WebSocket] = None
        self.connected_at: Optional[datetime] = None
        
        # 音频缓存（用于合并后转写）
        self.audio_buffer: List[dict] = []  # [{seq, timestamp_ms, data, mime_type}]
        self.audio_buffer_size = 0  # 字节数
        self.last_transcribe_time = 0  # 上次转写时间戳
        
        # 转写结果
        self.transcript_segments: List[TranscriptSegment] = []
        self.full_text = ""
        self.segment_counter = 0
        
        # 会话超时控制
        self.last_activity = time.time()
        self.is_active = False
        
    def update_activity(self):
        """更新最后活动时间"""
        self.last_activity = time.time()
    
    def is_expired(self, timeout_seconds: int = 3600) -> bool:
        """检查会话是否超时（默认60分钟）"""
        return time.time() - self.last_activity > timeout_seconds
    
    async def send_json(self, data: dict):
        """发送 JSON 消息到客户端"""
        if self.websocket:
            try:
                await self.websocket.send_json(data)
                self.update_activity()
            except Exception as e:
                logger.error(f"[{self.session_id}] WebSocket 发送失败: {e}")
    
    # 音频缓存限制（防止内存溢出）
    MAX_AUDIO_BUFFER_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_AUDIO_CHUNKS = 1000  # 最大片段数
    
    def add_audio_chunk(self, seq: int, timestamp_ms: int, data: bytes, mime_type: str) -> bool:
        """
        添加音频片段到缓存
        
        返回:
            bool: 是否成功添加（如果缓存已满则触发转写并返回False）
        """
        # 检查缓存是否已满
        if self.audio_buffer_size + len(data) > self.MAX_AUDIO_BUFFER_SIZE:
            logger.warning(f"[{self.session_id}] 音频缓存即将溢出 ({self.audio_buffer_size} bytes)，建议立即转写")
            return False
        
        if len(self.audio_buffer) >= self.MAX_AUDIO_CHUNKS:
            logger.warning(f"[{self.session_id}] 音频片段数达到上限 ({self.MAX_AUDIO_CHUNKS})，建议立即转写")
            return False
        
        self.audio_buffer.append({
            "seq": seq,
            "timestamp_ms": timestamp_ms,
            "data": data,
            "mime_type": mime_type,
            "received_at": time.time()
        })
        self.audio_buffer_size += len(data)
        self.update_activity()
        
        logger.debug(f"[{self.session_id}] 音频片段 #{seq} 已缓存，当前缓存 {len(self.audio_buffer)} 段，共 {self.audio_buffer_size} 字节")
        return True
    
    def should_transcribe(self, min_chunks: int = 3, min_bytes: int = 50000, min_interval_ms: int = 5000) -> bool:
        """
        判断是否应该进行转写
        
        - 至少 min_chunks 个片段
        - 或缓存达到 min_bytes 字节
        - 或距离上次转写超过 min_interval_ms 毫秒
        """
        if len(self.audio_buffer) < min_chunks and self.audio_buffer_size < min_bytes:
            return False
        
        if time.time() * 1000 - self.last_transcribe_time > min_interval_ms:
            return True
        
        return len(self.audio_buffer) >= min_chunks or self.audio_buffer_size >= min_bytes
    
    def get_and_clear_buffer(self) -> List[dict]:
        """获取并清空音频缓存"""
        chunks = self.audio_buffer.copy()
        self.audio_buffer = []
        self.audio_buffer_size = 0
        self.last_transcribe_time = time.time() * 1000
        return chunks
    
    def add_transcript(self, text: str, start_ms: int, end_ms: int, speaker_id: Optional[str] = None) -> TranscriptSegment:
        """添加转写结果"""
        self.segment_counter += 1
        segment = TranscriptSegment(
            id=f"seg_{self.session_id}_{self.segment_counter:04d}",
            text=text,
            start_time_ms=start_ms,
            end_time_ms=end_ms,
            speaker_id=speaker_id
        )
        self.transcript_segments.append(segment)
        
        # 更新完整文本
        if self.full_text:
            self.full_text += "\n"
        self.full_text += f"[{self._format_time(start_ms)}] {text}"
        
        self.update_activity()
        return segment
    
    def _format_time(self, ms: int) -> str:
        """格式化毫秒为 MM:SS"""
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    def update_segment(self, segment_id: str, new_text: str) -> bool:
        """更新转写片段文本（支持编辑）"""
        for seg in self.transcript_segments:
            if seg.id == segment_id:
                seg.text = new_text
                self._rebuild_full_text()
                return True
        return False
    
    def _rebuild_full_text(self):
        """重新构建完整文本"""
        lines = []
        for seg in self.transcript_segments:
            lines.append(f"[{self._format_time(seg.start_time_ms)}] {seg.text}")
        self.full_text = "\n".join(lines)


class WebSocketManager:
    """
    WebSocket 连接管理器（单例）
    
    管理所有活跃的会议会话
    """
    
    def __init__(self):
        # session_id -> MeetingSession
        self.sessions: Dict[str, MeetingSession] = {}
        # user_id -> set of session_ids
        self.user_sessions: Dict[str, set] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
    
    def start(self):
        """启动管理器，开始定时清理任务"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("WebSocket 管理器已启动")
    
    def stop(self):
        """停止管理器"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None
            logger.info("WebSocket 管理器已停止")
    
    async def _cleanup_loop(self):
        """定期清理超时会话"""
        while True:
            try:
                await asyncio.sleep(60)  # 每60秒检查一次
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"清理任务异常: {e}")
    
    async def _cleanup_expired_sessions(self):
        """清理超时会话"""
        expired_sessions = []
        for session_id, session in self.sessions.items():
            if session.is_expired():
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            await self.close_session(session_id, reason="会话超时")
            logger.info(f"[{session_id}] 超时会话已清理")
    
    def get_or_create_session(self, session_id: str, user_id: str) -> MeetingSession:
        """获取或创建会话"""
        if session_id not in self.sessions:
            self.sessions[session_id] = MeetingSession(session_id, user_id)
            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = set()
            self.user_sessions[user_id].add(session_id)
            logger.info(f"[{session_id}] 新会话已创建 (user: {user_id})")
        return self.sessions[session_id]
    
    def get_session(self, session_id: str) -> Optional[MeetingSession]:
        """获取会话"""
        return self.sessions.get(session_id)
    
    async def close_session(self, session_id: str, reason: str = "正常关闭"):
        """关闭会话"""
        session = self.sessions.pop(session_id, None)
        if session:
            # 从用户索引中移除
            user_id = session.user_id
            if user_id in self.user_sessions:
                self.user_sessions[user_id].discard(session_id)
            
            # 关闭 WebSocket
            if session.websocket:
                try:
                    await session.websocket.close()
                except Exception:
                    pass
            
            logger.info(f"[{session_id}] 会话已关闭: {reason}")
    
    async def connect(self, session_id: str, user_id: str, websocket: WebSocket) -> MeetingSession:
        """
        建立 WebSocket 连接（假设已在外部 accept）
        
        流程：
        1. 获取或创建会话
        2. 关联 WebSocket
        3. 发送连接成功消息
        """
        session = self.get_or_create_session(session_id, user_id)
        session.websocket = websocket
        session.connected_at = datetime.utcnow()
        session.is_active = True
        session.update_activity()
        
        # 注意：连接已由外部 accept，不发送 connected 消息
        # 初始化成功后由调用方发送 started 消息
        
        logger.info(f"[{session_id}] WebSocket 已连接 (user: {user_id})")
        return session
    
    async def disconnect(self, session_id: str):
        """断开 WebSocket 连接（但保留会话）"""
        session = self.sessions.get(session_id)
        if session:
            session.websocket = None
            session.is_active = False
            logger.info(f"[{session_id}] WebSocket 已断开，会话保留")
    
    async def broadcast_status(self, session_id: str, status: MeetingStatus, duration_ms: int, transcript_count: int):
        """广播状态更新"""
        session = self.sessions.get(session_id)
        if session and session.is_active:
            await session.send_json({
                "type": "status",
                "status": status,
                "duration_ms": duration_ms,
                "transcript_count": transcript_count
            })
    
    async def send_transcript(self, session_id: str, segment: TranscriptSegment, is_final: bool = True):
        """发送实时转写结果"""
        session = self.sessions.get(session_id)
        if session and session.is_active:
            await session.send_json({
                "type": "transcript",
                "segment_id": segment.id,
                "text": segment.text,
                "timestamp_ms": segment.start_time_ms,
                "is_final": is_final,
                "speaker_id": segment.speaker_id
            })
    
    async def send_result(self, session_id: str, success: bool, minutes: Optional[dict] = None, error: Optional[str] = None):
        """发送会议纪要完成消息"""
        session = self.sessions.get(session_id)
        if session and session.is_active:
            data = {
                "type": "result",
                "success": success
            }
            if minutes:
                data["minutes"] = minutes
            if error:
                data["error"] = error
            if success and minutes:
                data["download_urls"] = {
                    "docx": f"/api/v1/meetings/{session_id}/download?format=docx",
                    "json": f"/api/v1/meetings/{session_id}/download?format=json"
                }
            await session.send_json(data)
    
    async def send_error(self, session_id: str, code: str, message: str, recoverable: bool = True):
        """发送错误消息"""
        session = self.sessions.get(session_id)
        if session and session.is_active:
            await session.send_json({
                "type": "error",
                "code": code,
                "message": message,
                "recoverable": recoverable
            })
    
    async def send_custom_message(self, session_id: str, data: dict):
        """发送自定义消息"""
        session = self.sessions.get(session_id)
        if session and session.is_active:
            await session.send_json(data)
    
    def get_active_sessions_count(self) -> int:
        """获取活跃会话数"""
        return sum(1 for s in self.sessions.values() if s.is_active)
    
    def get_user_sessions(self, user_id: str) -> List[str]:
        """获取用户的所有会话ID"""
        return list(self.user_sessions.get(user_id, set()))


# 全局单例
websocket_manager = WebSocketManager()
