#!/usr/bin/env python3
"""
Meeting Management WebSocket Server V2
Support browser front-end direct connection
"""

import asyncio
import json
import logging
import argparse
import sys
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, List, Set
from dataclasses import dataclass, field

import websockets

# Import logger config
sys.path.insert(0, str(Path(__file__).parent / ".." / "src"))
try:
    from logger_config import get_logger
except ImportError:
    logging.basicConfig(level=logging.INFO)
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger(__name__)

# Constants
SESSION_TIMEOUT_MINUTES = 60
MAX_MESSAGE_SIZE = 10 * 1024 * 1024

@dataclass
class AudioChunk:
    seq: int
    timestamp_ms: int
    data: bytes
    mime_type: str
    received_at: datetime = field(default_factory=datetime.now)

@dataclass
class BrowserSession:
    session_id: str
    user_id: str
    websocket = None
    title: str = "Meeting"
    status: str = "preparing"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    audio_chunks: List[AudioChunk] = field(default_factory=list)
    transcripts: List[dict] = field(default_factory=list)
    last_activity: datetime = field(default_factory=datetime.now)
    pending_audio: List[AudioChunk] = field(default_factory=list)
    
    def add_audio_chunk(self, chunk: AudioChunk):
        self.audio_chunks.append(chunk)
        self.pending_audio.append(chunk)
        self.last_activity = datetime.now()
    
    def get_duration_ms(self) -> int:
        if not self.start_time:
            return 0
        end = self.end_time or datetime.now()
        return int((end - self.start_time).total_seconds() * 1000)
    
    def is_expired(self) -> bool:
        elapsed = datetime.now() - self.last_activity
        return elapsed > timedelta(minutes=SESSION_TIMEOUT_MINUTES)
    
    def get_pending_audio(self) -> Optional[bytes]:
        if not self.pending_audio:
            return None
        audio_data = b''.join([chunk.data for chunk in self.pending_audio])
        self.pending_audio = []
        return audio_data

class SessionManager:
    def __init__(self, output_dir: str = "../output"):
        self.sessions: Dict[str, BrowserSession] = {}
        self.user_sessions: Dict[str, Set[str]] = {}
        script_dir = Path(__file__).parent
        self.output_dir = script_dir / output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"SessionManager: {self.output_dir}")
    
    def create_session(self, session_id: str, user_id: str) -> BrowserSession:
        session = BrowserSession(session_id=session_id, user_id=user_id)
        self.sessions[session_id] = session
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = set()
        self.user_sessions[user_id].add(session_id)
        logger.info(f"Created session: {session_id} user={user_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[BrowserSession]:
        session = self.sessions.get(session_id)
        if session:
            session.last_activity = datetime.now()
        return session
    
    def remove_session(self, session_id: str) -> bool:
        session = self.sessions.get(session_id)
        if session:
            del self.sessions[session_id]
            if session.user_id in self.user_sessions:
                self.user_sessions[session.user_id].discard(session_id)
            logger.info(f"Removed: {session_id}")
            return True
        return False

session_manager = SessionManager()

async def send_to_browser(session: BrowserSession, message: dict):
    if session.websocket and session.websocket.open:
        try:
            await session.websocket.send(json.dumps(message, ensure_ascii=False))
        except Exception as e:
            logger.error(f"Send failed: {e}")

async def process_audio_queue(session: BrowserSession):
    """Process audio queue with mock transcription."""
    import random
    mock_texts = [
        "讨论产品方案设计思路",
        "成本需要再评估",
        "下周五完成设计文档",
        "张三负责前端开发",
        "优先级比较高",
    ]
    
    while session.status == "recording":
        await asyncio.sleep(2)
        
        if session.status != "recording":
            break
        
        audio_data = session.get_pending_audio()
        if not audio_data:
            continue
        
        try:
            await asyncio.sleep(0.5)
            
            if random.random() > 0.3:
                text = random.choice(mock_texts)
                segment_id = f"seg_{len(session.transcripts)}"
                
                session.transcripts.append({
                    "id": segment_id,
                    "text": text,
                    "timestamp_ms": session.get_duration_ms(),
                    "is_final": True
                })
                
                await send_to_browser(session, {
                    "type": "transcript",
                    "segment_id": segment_id,
                    "text": text,
                    "timestamp_ms": session.get_duration_ms(),
                    "is_final": True,
                    "speaker_id": None
                })
                
                logger.debug(f"Transcribed: {text[:30]}...")
                
        except Exception as e:
            logger.error(f"Audio error: {e}")

async def generate_minutes(session: BrowserSession):
    """Generate meeting minutes."""
    try:
        full_text = " ".join([t["text"] for t in session.transcripts])
        
        if not full_text:
            logger.warning(f"No transcript: {session.session_id}")
            return
        
        minutes = {
            "title": session.title,
            "date": session.start_time.isoformat() if session.start_time else None,
            "duration_ms": session.get_duration_ms(),
            "participants": [],
            "topics": [
                {
                    "title": "Product Discussion",
                    "discussion_points": ["Design approach", "Cost evaluation"],
                    "conclusion": "Plan approved",
                    "action_items": [
                        {"action": "Complete design doc", "owner": "Alice", "deadline": "2026-03-04"}
                    ]
                }
            ]
        }
        
        await send_to_browser(session, {
            "type": "meeting_result",
            "session_id": session.session_id,
            "success": True,
            "minutes": minutes,
            "download_url": f"/api/meeting/{session.session_id}/download"
        })
        
        logger.info(f"Minutes generated: {session.session_id}")
        
    except Exception as e:
        logger.error(f"Minutes error: {e}")
        await send_to_browser(session, {
            "type": "meeting_result",
            "session_id": session.session_id,
            "success": False,
            "error": str(e)
        })

async def handle_browser(websocket, path: str):
    """Handle browser WebSocket."""
    import urllib.parse
    
    parsed = urllib.parse.urlparse(path)
    path_parts = parsed.path.strip("/").split("/")
    
    if len(path_parts) < 3 or path_parts[0] != "ws" or path_parts[1] != "meeting":
        await websocket.close(code=4000, reason="Invalid path")
        return
    
    session_id = path_parts[2]
    query = urllib.parse.parse_qs(parsed.query)
    user_id = query.get("user_id", ["anonymous"])[0]
    
    session = session_manager.get_session(session_id)
    if not session:
        session = session_manager.create_session(session_id, user_id)
    
    session.websocket = websocket
    client = str(websocket.remote_address) if hasattr(websocket, 'remote_address') else "unknown"
    
    logger.info(f"Browser: {session_id} user={user_id} from={client}")
    
    audio_task = None
    
    try:
        async for message in websocket:
            try:
                if len(message) > MAX_MESSAGE_SIZE:
                    await send_to_browser(session, {
                        "type": "error",
                        "code": "MESSAGE_TOO_LARGE",
                        "message": f"Max {MAX_MESSAGE_SIZE} bytes",
                        "recoverable": True
                    })
                    continue
                
                data = json.loads(message)
                msg_type = data.get("type")
                
                if msg_type == "meeting_start":
                    session.title = data.get("title", "Meeting")
                    session.start_time = datetime.now()
                    session.status = "recording"
                    
                    logger.info(f"Started: {session_id} - '{session.title}'")
                    
                    audio_task = asyncio.create_task(process_audio_queue(session))
                    
                    await send_to_browser(session, {
                        "type": "meeting_status",
                        "session_id": session_id,
                        "status": "recording",
                        "duration_ms": 0,
                        "segment_count": 0
                    })
                
                elif msg_type == "meeting_end":
                    session.status = "processing"
                    session.end_time = datetime.now()
                    
                    logger.info(f"Ended: {session_id}, duration={session.get_duration_ms()}ms")
                    
                    if audio_task:
                        audio_task.cancel()
                        try:
                            await audio_task
                        except asyncio.CancelledError:
                            pass
                    
                    await generate_minutes(session)
                    session.status = "completed"
                
                elif msg_type == "meeting_pause":
                    session.status = "paused"
                    await send_to_browser(session, {
                        "type": "meeting_status",
                        "session_id": session_id,
                        "status": "paused",
                        "duration_ms": session.get_duration_ms()
                    })
                
                elif msg_type == "meeting_resume":
                    session.status = "recording"
                    await send_to_browser(session, {
                        "type": "meeting_status",
                        "session_id": session_id,
                        "status": "recording",
                        "duration_ms": session.get_duration_ms()
                    })
                
                elif msg_type == "audio_chunk":
                    if session.status != "recording":
                        await send_to_browser(session, {
                            "type": "error",
                            "code": "NOT_RECORDING",
                            "message": "Not recording",
                            "recoverable": True
                        })
                        continue
                    
                    try:
                        audio_data = base64.b64decode(data.get("data", ""))
                        chunk = AudioChunk(
                            seq=data.get("seq", 0),
                            timestamp_ms=data.get("timestamp_ms", 0),
                            data=audio_data,
                            mime_type=data.get("mime_type", "audio/webm")
                        )
                        session.add_audio_chunk(chunk)
                        
                        await send_to_browser(session, {
                            "type": "ack",
                            "seq": chunk.seq,
                            "received_at": datetime.now().isoformat()
                        })
                        
                    except Exception as e:
                        logger.error(f"Decode error: {e}")
                        await send_to_browser(session, {
                            "type": "error",
                            "code": "AUDIO_DECODE_ERROR",
                            "message": str(e),
                            "recoverable": True
                        })
                
                elif msg_type == "audio_config":
                    logger.info(f"Config: {session_id}: {data.get('config')}")
                
                elif msg_type == "ping":
                    await send_to_browser(session, {
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })
                
                else:
                    await send_to_browser(session, {
                        "type": "error",
                        "code": "UNKNOWN_TYPE",
                        "message": f"Unknown: {msg_type}",
                        "recoverable": True
                    })
            
            except json.JSONDecodeError as e:
                logger.error(f"JSON error: {e}")
                await send_to_browser(session, {
                    "type": "error",
                    "code": "INVALID_JSON",
                    "message": "Invalid JSON",
                    "recoverable": True
                })
            
            except Exception as e:
                logger.error(f"Process error: {e}")
                await send_to_browser(session, {
                    "type": "error",
                    "code": "INTERNAL_ERROR",
                    "message": str(e),
                    "recoverable": False
                })
    
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WS error: {e}")
    finally:
        session.websocket = None
        if audio_task:
            audio_task.cancel()
        logger.info(f"Closed: {session_id}")

async def cleanup_task():
    """Cleanup expired sessions."""
    while True:
        await asyncio.sleep(300)
        count = session_manager.cleanup_expired_sessions()
        if count > 0:
            logger.info(f"Cleaned {count} expired sessions")

def main():
    parser = argparse.ArgumentParser(description="Meeting Server V2")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    
    async def route_handler(websocket):
        path = websocket.request.path if hasattr(websocket, 'request') else '/'
        if path.startswith("/ws/meeting"):
            await handle_browser(websocket, path)
        elif path == "/health":
            await websocket.send(json.dumps({"status": "healthy"}))
        else:
            await websocket.close(code=4004, reason="Not found")
    
    async def start_server():
        logger.info(f"Meeting Server V2 starting on {args.host}:{args.port}")
        logger.info(f"WebSocket: ws://{args.host}:{args.port}/ws/meeting/{{session_id}}")
        
        cleanup_coro = asyncio.create_task(cleanup_task())
        
        try:
            async with websockets.serve(route_handler, args.host, args.port):
                await asyncio.Future()
        finally:
            cleanup_coro.cancel()
    
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        logger.info("Stopped by user")

if __name__ == "__main__":
    main()
