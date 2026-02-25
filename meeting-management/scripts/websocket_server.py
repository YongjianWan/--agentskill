#!/usr/bin/env python3
"""
Meeting Management WebSocket Server
Receives real-time transcription from Handy and generates meeting minutes.

更新记录:
- 2026-02-25: 添加详细日志、异常处理、会话超时清理

Usage:
    python websocket_server.py [--port 8765] [--host 0.0.0.0]

Endpoints:
    WebSocket: ws://host:port/ws/meeting/{session_id}
    HTTP GET:  http://host:port/health
    HTTP POST: http://host:port/api/meeting/{session_id}/finalize
"""

import asyncio
import json
import logging
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass, field, asdict

import websockets

# 导入日志配置
sys.path.insert(0, str(Path(__file__).parent / ".." / "src"))
try:
    from logger_config import setup_logging, get_logger
except ImportError:
    # 如果导入失败，使用基本日志配置
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    def setup_logging(*args, **kwargs):
        pass
    def get_logger(name):
        return logging.getLogger(name)

# 全局日志记录器（将在 main 中初始化）
logger = logging.getLogger(__name__)

# 常量配置
SESSION_TIMEOUT_MINUTES = 60  # 会话超时时间（分钟）
MAX_MESSAGE_SIZE = 1024 * 1024  # 最大消息大小（1MB）
PING_INTERVAL = 30  # 心跳检测间隔（秒）


@dataclass
class TranscriptionSegment:
    """Single transcription segment."""
    id: str
    text: str
    start_time_ms: int
    is_final: bool
    received_at: datetime = field(default_factory=datetime.now)


@dataclass
class ActionItem:
    """Action item extracted from meeting."""
    action: str
    owner: str
    deadline: Optional[str]
    related_project: Optional[str]
    related_enterprise: Optional[str]
    status: str = "待处理"
    source: str = ""


@dataclass
class MeetingTopic:
    """Meeting topic with discussion points."""
    title: str
    discussion_points: List[str] = field(default_factory=list)
    conclusion: str = ""
    action_items: List[ActionItem] = field(default_factory=list)


@dataclass
class MeetingSession:
    """Active meeting session."""
    session_id: str
    title: str = "未命名会议"
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    participants: List[str] = field(default_factory=list)
    location: str = ""
    segments: List[TranscriptionSegment] = field(default_factory=list)
    topics: List[MeetingTopic] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    pending_confirmations: List[str] = field(default_factory=list)
    is_finalized: bool = False
    last_activity: datetime = field(default_factory=datetime.now)
    client_address: Optional[str] = None
    
    def add_segment(self, segment: TranscriptionSegment):
        """Add a new transcription segment."""
        self.segments.append(segment)
        self.last_activity = datetime.now()
        logger.info(f"[{self.session_id}] New segment #{len(self.segments)}: {segment.text[:50]}...")
    
    def is_expired(self, timeout_minutes: int = SESSION_TIMEOUT_MINUTES) -> bool:
        """Check if session has expired (no activity)."""
        if self.is_finalized:
            return False
        elapsed = datetime.now() - self.last_activity
        return elapsed > timedelta(minutes=timeout_minutes)
    
    def get_duration_seconds(self) -> float:
        """Get meeting duration in seconds."""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
    
    def get_full_text(self) -> str:
        """Get full transcription text."""
        return " ".join([s.text for s in self.segments])
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "title": self.title,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.get_duration_seconds(),
            "participants": self.participants,
            "location": self.location,
            "segment_count": len(self.segments),
            "is_finalized": self.is_finalized,
            "client_address": self.client_address,
            "last_activity": self.last_activity.isoformat()
        }


class MeetingManager:
    """Manages active meeting sessions."""
    
    def __init__(self, output_dir: str = "../output"):
        self.sessions: Dict[str, MeetingSession] = {}
        script_dir = Path(__file__).parent
        self.output_dir = script_dir / output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"MeetingManager initialized, output_dir: {self.output_dir}")
        
    def get_or_create_session(self, session_id: str, client_address: str = None) -> MeetingSession:
        """Get existing session or create new one."""
        if session_id not in self.sessions:
            self.sessions[session_id] = MeetingSession(
                session_id=session_id,
                client_address=client_address
            )
            logger.info(f"Created new session: {session_id} from {client_address}")
        else:
            # 更新客户端地址
            if client_address:
                self.sessions[session_id].client_address = client_address
            self.sessions[session_id].last_activity = datetime.now()
        return self.sessions[session_id]
    
    def get_session(self, session_id: str) -> Optional[MeetingSession]:
        """Get session by ID."""
        session = self.sessions.get(session_id)
        if session:
            session.last_activity = datetime.now()
        return session
    
    def finalize_session(self, session_id: str) -> Optional[MeetingSession]:
        """Finalize a meeting session."""
        session = self.sessions.get(session_id)
        if session:
            session.end_time = datetime.now()
            session.is_finalized = True
            session.last_activity = datetime.now()
            logger.info(f"Finalized session: {session_id}, duration: {session.get_duration_seconds():.1f}s, "
                       f"segments: {len(session.segments)}")
        else:
            logger.warning(f"Attempted to finalize non-existent session: {session_id}")
        return session
    
    def remove_session(self, session_id: str) -> bool:
        """Remove a session from memory."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Removed session: {session_id}")
            return True
        return False
    
    def cleanup_expired_sessions(self, timeout_minutes: int = SESSION_TIMEOUT_MINUTES) -> int:
        """Remove expired sessions and return count."""
        expired = [
            sid for sid, session in self.sessions.items()
            if session.is_expired(timeout_minutes)
        ]
        for sid in expired:
            session = self.sessions[sid]
            logger.warning(f"Session expired and removed: {sid}, "
                          f"last activity: {session.last_activity.isoformat()}")
            del self.sessions[sid]
        return len(expired)
    
    def get_stats(self) -> dict:
        """Get manager statistics."""
        active = [s for s in self.sessions.values() if not s.is_finalized]
        finalized = [s for s in self.sessions.values() if s.is_finalized]
        return {
            "total_sessions": len(self.sessions),
            "active_sessions": len(active),
            "finalized_sessions": len(finalized),
            "total_segments": sum(len(s.segments) for s in self.sessions.values())
        }
    
    def save_transcription_log(self, session: MeetingSession) -> Path:
        """Save raw transcription log."""
        try:
            # 按年月组织目录
            now = datetime.now()
            log_dir = self.output_dir / "logs" / str(now.year) / f"{now.month:02d}"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            log_file = log_dir / f"{session.session_id}_stream.log"
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(f"# Session: {session.session_id}\n")
                f.write(f"# Title: {session.title}\n")
                f.write(f"# Start: {session.start_time.isoformat()}\n")
                f.write(f"# Client: {session.client_address}\n")
                f.write(f"# Segments: {len(session.segments)}\n")
                f.write("#" * 50 + "\n\n")
                
                for seg in session.segments:
                    timestamp = seg.received_at.strftime("%H:%M:%S.%f")[:-3]
                    f.write(f"[{timestamp}] {seg.text}\n")
            
            logger.info(f"Saved transcription log: {log_file}")
            return log_file
        except Exception as e:
            logger.error(f"Failed to save transcription log: {e}")
            raise


# Global manager instance
meeting_manager = MeetingManager()


async def handle_websocket(websocket, path: str):
    """Handle WebSocket connections from Handy."""
    # Parse session_id from path: /ws/meeting/{session_id}
    parts = path.strip("/").split("/")
    if len(parts) < 3 or parts[0] != "ws" or parts[1] != "meeting":
        logger.warning(f"Invalid path: {path}")
        await websocket.close(code=4000, reason="Invalid path. Use /ws/meeting/{session_id}")
        return
    
    session_id = parts[2]
    client_address = str(websocket.remote_address) if hasattr(websocket, 'remote_address') else "unknown"
    
    # 验证 session_id
    if not session_id or len(session_id) < 3:
        logger.warning(f"Invalid session_id: {session_id}")
        await websocket.close(code=4001, reason="Invalid session_id")
        return
    
    session = meeting_manager.get_or_create_session(session_id, client_address)
    
    logger.info(f"WebSocket connected: {session_id} from {client_address}")
    
    try:
        async for message in websocket:
            try:
                # 检查消息大小
                if len(message) > MAX_MESSAGE_SIZE:
                    logger.warning(f"Message too large ({len(message)} bytes), rejecting")
                    await websocket.send(json.dumps({
                        "type": "error",
                        "error": "Message too large",
                        "max_size": MAX_MESSAGE_SIZE
                    }))
                    continue
                
                data = json.loads(message)
                msg_type = data.get("type")
                
                if msg_type == "transcription":
                    # Handle transcription segment from Handy
                    seg_data = data.get("segment", {})
                    segment = TranscriptionSegment(
                        id=seg_data.get("id", ""),
                        text=seg_data.get("text", ""),
                        start_time_ms=seg_data.get("start_time_ms", 0),
                        is_final=seg_data.get("is_final", True)
                    )
                    
                    # 验证文本
                    if not segment.text or not segment.text.strip():
                        logger.debug(f"Empty segment received, skipping")
                        continue
                    
                    session.add_segment(segment)
                    
                    # Acknowledge
                    await websocket.send(json.dumps({
                        "type": "ack",
                        "segment_id": segment.id,
                        "received_at": datetime.now().isoformat(),
                        "segment_count": len(session.segments)
                    }))
                    
                elif msg_type == "session_start":
                    # Handy session start
                    old_title = session.title
                    session.title = data.get("title", session.title)
                    if data.get("start_time"):
                        try:
                            session.start_time = datetime.fromisoformat(data["start_time"].replace("Z", "+00:00"))
                        except Exception as e:
                            logger.warning(f"Failed to parse start_time: {e}")
                    logger.info(f"Handy session started: {session_id} - '{old_title}' -> '{session.title}'")
                    
                    await websocket.send(json.dumps({
                        "type": "session_started",
                        "session_id": session_id,
                        "title": session.title
                    }))
                    
                elif msg_type == "session_end":
                    # Handy session end - auto finalize
                    session.end_time = datetime.now()
                    session.is_finalized = True
                    full_text = data.get("full_text", "")
                    logger.info(f"Handy session ended: {session_id}, "
                               f"transcript: {len(full_text)} chars, {len(session.segments)} segments")
                    
                    # Auto-save transcription log
                    try:
                        log_file = meeting_manager.save_transcription_log(session)
                        logger.info(f"Auto-saved transcription log: {log_file}")
                    except Exception as e:
                        logger.error(f"Failed to save transcription log: {e}")
                    
                    # Send confirmation
                    await websocket.send(json.dumps({
                        "type": "session_finalized",
                        "session_id": session_id,
                        "transcription_log": str(log_file) if 'log_file' in locals() else None,
                        "segment_count": len(session.segments),
                        "duration_seconds": session.get_duration_seconds()
                    }))
                    
                elif msg_type == "metadata":
                    # Update meeting metadata
                    old_title = session.title
                    session.title = data.get("title", session.title)
                    session.participants = data.get("participants", [])
                    session.location = data.get("location", "")
                    logger.info(f"Updated metadata for {session_id}: title='{old_title}'->'{session.title}', "
                               f"participants={len(session.participants)}, location='{session.location}'")
                    
                    await websocket.send(json.dumps({
                        "type": "metadata_updated",
                        "session_id": session_id
                    }))
                    
                elif msg_type == "ping":
                    await websocket.send(json.dumps({"type": "pong", "timestamp": datetime.now().isoformat()}))
                    
                else:
                    logger.warning(f"Unknown message type: {msg_type}")
                    await websocket.send(json.dumps({
                        "type": "error",
                        "error": f"Unknown message type: {msg_type}"
                    }))
                    
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON received from {session_id}: {e}, message: {message[:100]}...")
                await websocket.send(json.dumps({
                    "type": "error",
                    "error": "Invalid JSON"
                }))
            except Exception as e:
                logger.error(f"Error processing message from {session_id}: {e}", exc_info=True)
                try:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "error": f"Internal error: {str(e)}"
                    }))
                except:
                    pass  # WebSocket 可能已关闭
                
    except websockets.exceptions.ConnectionClosedOK:
        logger.info(f"WebSocket closed normally: {session_id}")
    except websockets.exceptions.ConnectionClosedError as e:
        logger.warning(f"WebSocket closed with error: {session_id}, code={e.code}, reason={e.reason}")
    except Exception as e:
        logger.error(f"WebSocket error for {session_id}: {e}", exc_info=True)
    finally:
        # 连接关闭后的清理
        logger.info(f"WebSocket connection ended: {session_id}, total segments: {len(session.segments)}")


async def health_handler(websocket, path: str):
    """Simple health check endpoint."""
    if path == "/health":
        stats = meeting_manager.get_stats()
        await websocket.send(json.dumps({
            "status": "healthy",
            **stats,
            "timestamp": datetime.now().isoformat()
        }))
    else:
        await websocket.close(code=4004, reason="Not found")


async def http_handler(scope, receive, send):
    """ASGI HTTP handler for REST API."""
    path = scope["path"]
    method = scope["method"]
    
    # CORS headers
    headers = [
        [b"content-type", b"application/json"],
        [b"access-control-allow-origin", b"*"],
        [b"access-control-allow-methods", b"GET, POST, OPTIONS"],
    ]
    
    if method == "OPTIONS":
        await send({"type": "http.response.start", "status": 200, "headers": headers})
        await send({"type": "http.response.body", "body": b""})
        return
    
    # Health check
    if path == "/health" and method == "GET":
        try:
            stats = meeting_manager.get_stats()
            body = json.dumps({
                "status": "healthy",
                **stats,
                "timestamp": datetime.now().isoformat()
            }).encode()
            headers.append([b"content-length", str(len(body)).encode()])
            await send({"type": "http.response.start", "status": 200, "headers": headers})
            await send({"type": "http.response.body", "body": body})
        except Exception as e:
            logger.error(f"Health check error: {e}")
            body = json.dumps({"status": "error", "error": str(e)}).encode()
            headers.append([b"content-length", str(len(body)).encode()])
            await send({"type": "http.response.start", "status": 500, "headers": headers})
            await send({"type": "http.response.body", "body": body})
        return
    
    # Get session info
    if path.startswith("/api/meeting/") and method == "GET":
        parts = path.split("/")
        if len(parts) >= 4:
            session_id = parts[3]
            session = meeting_manager.get_session(session_id)
            if session:
                body = json.dumps(session.to_dict(), ensure_ascii=False).encode()
            else:
                body = json.dumps({"error": "Session not found"}).encode()
            headers.append([b"content-length", str(len(body)).encode()])
            await send({"type": "http.response.start", "status": 200 if session else 404, "headers": headers})
            await send({"type": "http.response.body", "body": body})
            return
    
    # Finalize session
    if path.startswith("/api/meeting/") and path.endswith("/finalize") and method == "POST":
        parts = path.split("/")
        if len(parts) >= 5:
            session_id = parts[3]
            session = meeting_manager.finalize_session(session_id)
            if session:
                # Save transcription log
                try:
                    log_file = meeting_manager.save_transcription_log(session)
                    body = json.dumps({
                        "success": True,
                        "session": session.to_dict(),
                        "transcription_log": str(log_file)
                    }, ensure_ascii=False).encode()
                except Exception as e:
                    logger.error(f"Failed to save log during finalize: {e}")
                    body = json.dumps({
                        "success": True,
                        "session": session.to_dict(),
                        "error": f"Failed to save log: {e}"
                    }, ensure_ascii=False).encode()
            else:
                body = json.dumps({"error": "Session not found"}).encode()
            headers.append([b"content-length", str(len(body)).encode()])
            await send({"type": "http.response.start", "status": 200 if session else 404, "headers": headers})
            await send({"type": "http.response.body", "body": body})
            return
    
    # Cleanup expired sessions (admin endpoint)
    if path == "/api/admin/cleanup" and method == "POST":
        try:
            count = meeting_manager.cleanup_expired_sessions()
            body = json.dumps({
                "success": True,
                "removed_sessions": count,
                "remaining_sessions": len(meeting_manager.sessions)
            }).encode()
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            body = json.dumps({"error": str(e)}).encode()
        headers.append([b"content-length", str(len(body)).encode()])
        await send({"type": "http.response.start", "status": 200, "headers": headers})
        await send({"type": "http.response.body", "body": body})
        return
    
    # 404 Not Found
    body = b'{"error": "Not found"}'
    headers.append([b"content-length", str(len(body)).encode()])
    await send({"type": "http.response.start", "status": 404, "headers": headers})
    await send({"type": "http.response.body", "body": body})


async def cleanup_task():
    """Background task to cleanup expired sessions."""
    while True:
        try:
            await asyncio.sleep(300)  # 每5分钟检查一次
            count = meeting_manager.cleanup_expired_sessions()
            if count > 0:
                logger.info(f"Cleanup task removed {count} expired sessions")
        except Exception as e:
            logger.error(f"Cleanup task error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Meeting Management WebSocket Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind (default: 8765)")
    parser.add_argument("--output-dir", default="../output", help="Output directory (default: ../output)")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Log level (default: INFO)")
    parser.add_argument("--log-dir", default=None, help="Log directory (default: output_dir/logs)")
    args = parser.parse_args()
    
    # 设置日志
    script_dir = Path(__file__).parent
    log_dir = args.log_dir or (script_dir / args.output_dir / "logs")
    setup_logging(
        log_dir=str(log_dir),
        log_level=args.log_level,
        enable_console=True,
        enable_file=True
    )
    
    global logger
    logger = get_logger(__name__)
    
    # Update output directory (resolve relative to script location)
    script_dir = Path(__file__).parent
    meeting_manager.output_dir = script_dir / args.output_dir
    meeting_manager.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def route_handler(websocket):
        """Route WebSocket connections."""
        # Get path from websocket request headers
        path = websocket.request.path if hasattr(websocket, 'request') else '/'
        
        if path.startswith("/ws/"):
            await handle_websocket(websocket, path)
        elif path == "/health":
            await health_handler(websocket, path)
        else:
            await websocket.close(code=4004, reason="Not found")
    
    async def start_server():
        """Start the WebSocket server."""
        logger.info(f"=" * 60)
        logger.info(f"Meeting Management Server v0.9-beta")
        logger.info(f"=" * 60)
        logger.info(f"Starting WebSocket server on {args.host}:{args.port}")
        logger.info(f"WebSocket endpoint: ws://{args.host}:{args.port}/ws/meeting/{{session_id}}")
        logger.info(f"HTTP health check: http://{args.host}:{args.port}/health")
        logger.info(f"Output directory: {meeting_manager.output_dir}")
        logger.info(f"Log level: {args.log_level}")
        logger.info(f"=" * 60)
        
        # 启动清理任务
        cleanup_coro = asyncio.create_task(cleanup_task())
        
        try:
            async with websockets.serve(route_handler, args.host, args.port):
                await asyncio.Future()  # Run forever
        finally:
            cleanup_coro.cancel()
    
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
