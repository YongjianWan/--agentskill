#!/usr/bin/env python3
"""
Meeting Management WebSocket Server
Receives real-time transcription from Handy and generates meeting minutes.

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
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass, field, asdict

import websockets
# WebSocket server - compatible with websockets >= 12.0

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
    
    def add_segment(self, segment: TranscriptionSegment):
        """Add a new transcription segment."""
        self.segments.append(segment)
        logger.info(f"[{self.session_id}] New segment: {segment.text[:50]}...")
    
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
            "participants": self.participants,
            "location": self.location,
            "segment_count": len(self.segments),
            "is_finalized": self.is_finalized
        }


class MeetingManager:
    """Manages active meeting sessions."""
    
    def __init__(self, output_dir: str = "../output"):
        self.sessions: Dict[str, MeetingSession] = {}
        script_dir = Path(__file__).parent
        self.output_dir = script_dir / output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def get_or_create_session(self, session_id: str) -> MeetingSession:
        """Get existing session or create new one."""
        if session_id not in self.sessions:
            self.sessions[session_id] = MeetingSession(session_id=session_id)
            logger.info(f"Created new session: {session_id}")
        return self.sessions[session_id]
    
    def get_session(self, session_id: str) -> Optional[MeetingSession]:
        """Get session by ID."""
        return self.sessions.get(session_id)
    
    def finalize_session(self, session_id: str) -> Optional[MeetingSession]:
        """Finalize a meeting session."""
        session = self.sessions.get(session_id)
        if session:
            session.end_time = datetime.now()
            session.is_finalized = True
            logger.info(f"Finalized session: {session_id}")
        return session
    
    def save_transcription_log(self, session: MeetingSession):
        """Save raw transcription log."""
        log_file = self.output_dir / f"{session.session_id}_stream.log"
        with open(log_file, "w", encoding="utf-8") as f:
            for seg in session.segments:
                timestamp = seg.received_at.strftime("%H:%M:%S.%f")[:-3]
                f.write(f"[{timestamp}] {seg.text}\n")
        logger.info(f"Saved transcription log: {log_file}")
        return log_file


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
    session = meeting_manager.get_or_create_session(session_id)
    
    logger.info(f"WebSocket connected: {session_id} from {websocket.remote_address}")
    
    try:
        async for message in websocket:
            try:
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
                    session.add_segment(segment)
                    
                    # Acknowledge
                    await websocket.send(json.dumps({
                        "type": "ack",
                        "segment_id": segment.id,
                        "received_at": datetime.now().isoformat()
                    }))
                    
                elif msg_type == "session_start":
                    # Handy session start
                    session.title = data.get("title", session.title)
                    if data.get("start_time"):
                        try:
                            session.start_time = datetime.fromisoformat(data["start_time"].replace("Z", "+00:00"))
                        except:
                            pass
                    logger.info(f"Handy session started: {session_id} - {session.title}")
                    
                elif msg_type == "session_end":
                    # Handy session end - auto finalize
                    session.end_time = datetime.now()
                    session.is_finalized = True
                    full_text = data.get("full_text", "")
                    logger.info(f"Handy session ended: {session_id}")
                    logger.info(f"Full transcript: {len(full_text)} chars, {len(session.segments)} segments")
                    
                    # Auto-save transcription log
                    log_file = meeting_manager.save_transcription_log(session)
                    logger.info(f"Auto-saved transcription log: {log_file}")
                    
                    # Send confirmation
                    await websocket.send(json.dumps({
                        "type": "session_finalized",
                        "session_id": session_id,
                        "transcription_log": str(log_file),
                        "segment_count": len(session.segments)
                    }))
                    
                elif msg_type == "metadata":
                    # Update meeting metadata
                    session.title = data.get("title", session.title)
                    session.participants = data.get("participants", [])
                    session.location = data.get("location", "")
                    logger.info(f"Updated metadata for {session_id}: {session.title}")
                    
                elif msg_type == "ping":
                    await websocket.send(json.dumps({"type": "pong"}))
                    
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received: {message[:100]}")
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


async def health_handler(websocket, path: str):
    """Simple health check endpoint."""
    if path == "/health":
        await websocket.send(json.dumps({
            "status": "healthy",
            "active_sessions": len(meeting_manager.sessions),
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
        body = json.dumps({
            "status": "healthy",
            "active_sessions": len(meeting_manager.sessions),
            "timestamp": datetime.now().isoformat()
        }).encode()
        headers.append([b"content-length", str(len(body)).encode()])
        await send({"type": "http.response.start", "status": 200, "headers": headers})
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
                log_file = meeting_manager.save_transcription_log(session)
                body = json.dumps({
                    "success": True,
                    "session": session.to_dict(),
                    "transcription_log": str(log_file)
                }, ensure_ascii=False).encode()
            else:
                body = json.dumps({"error": "Session not found"}).encode()
            headers.append([b"content-length", str(len(body)).encode()])
            await send({"type": "http.response.start", "status": 200 if session else 404, "headers": headers})
            await send({"type": "http.response.body", "body": body})
            return
    
    # 404 Not Found
    body = b'{"error": "Not found"}'
    headers.append([b"content-length", str(len(body)).encode()])
    await send({"type": "http.response.start", "status": 404, "headers": headers})
    await send({"type": "http.response.body", "body": body})


def main():
    parser = argparse.ArgumentParser(description="Meeting Management WebSocket Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind (default: 8765)")
    parser.add_argument("--output-dir", default="../output", help="Output directory (default: ../output)")
    args = parser.parse_args()
    
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
        logger.info(f"Starting WebSocket server on {args.host}:{args.port}")
        logger.info(f"WebSocket endpoint: ws://{args.host}:{args.port}/ws/meeting/{{session_id}}")
        logger.info(f"HTTP health check: http://{args.host}:{args.port}/health")
        
        async with websockets.serve(route_handler, args.host, args.port):
            await asyncio.Future()  # Run forever
    
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        logger.info("Server stopped")


if __name__ == "__main__":
    main()
