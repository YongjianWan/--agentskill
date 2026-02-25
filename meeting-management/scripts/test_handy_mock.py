#!/usr/bin/env python3
"""
Mock Handy client for integration testing.
Simulates the real Handy WebSocket client behavior.

Usage:
    python test_handy_mock.py --ws-url ws://localhost:8765/ws/meeting/test-001
"""

import asyncio
import json
import uuid
import argparse
from datetime import datetime
import websockets


class MockHandy:
    """Simulates Handy WebSocket client behavior."""
    
    def __init__(self, ws_url: str, session_id: str = None):
        self.ws_url = ws_url
        self.session_id = session_id or str(uuid.uuid4())
        self.start_time = None
        self.transcript_history = []
        
    async def connect(self):
        """Connect to meeting skill server."""
        print(f"[Handy] Connecting to {self.ws_url}...")
        self.ws = await websockets.connect(self.ws_url)
        print(f"[Handy] Connected! Session: {self.session_id}")
        
    async def start_session(self, title: str = None):
        """Send session_start message (Handy behavior)."""
        self.start_time = datetime.utcnow()
        
        msg = {
            "type": "session_start",
            "session_id": self.session_id,
            "title": title or f"Meeting {self.session_id[:8]}",
            "start_time": self.start_time.isoformat() + "Z"
        }
        
        await self.ws.send(json.dumps(msg))
        print(f"[Handy] Sent session_start: {msg['title']}")
        
    async def send_transcription(self, text: str, is_final: bool = True):
        """Send transcription segment (Handy behavior)."""
        if not text.strip():
            return
            
        elapsed_ms = 0
        if self.start_time:
            elapsed_ms = int((datetime.utcnow() - self.start_time).total_seconds() * 1000)
        
        segment = {
            "id": str(uuid.uuid4()),
            "text": text,
            "start_time_ms": elapsed_ms,
            "end_time_ms": elapsed_ms + 1000,
            "speaker_id": None,
            "is_final": is_final,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        msg = {
            "type": "transcription",
            "session_id": self.session_id,
            "segment": segment
        }
        
        await self.ws.send(json.dumps(msg, ensure_ascii=False))
        self.transcript_history.append(text)
        print(f"[Handy] Sent transcription [{len(self.transcript_history)}]: {text[:40]}...")
        
        # Wait for ack from server
        try:
            response = await asyncio.wait_for(self.ws.recv(), timeout=1.0)
            ack = json.loads(response)
            if ack.get("type") == "ack":
                print(f"[Handy] Received ack for segment {ack.get('segment_id', 'unknown')[:8]}")
        except asyncio.TimeoutError:
            pass
        
    async def end_session(self):
        """Send session_end message (Handy behavior)."""
        msg = {
            "type": "session_end",
            "session_id": self.session_id,
            "end_time": datetime.utcnow().isoformat() + "Z",
            "full_text": " ".join(self.transcript_history)
        }
        
        await self.ws.send(json.dumps(msg, ensure_ascii=False))
        print(f"[Handy] Sent session_end")
        print(f"[Handy] Full transcript ({len(self.transcript_history)} segments, {len(msg['full_text'])} chars)")
        
    async def close(self):
        """Close WebSocket connection."""
        await self.ws.close()
        print("[Handy] Disconnected")


async def run_mock_meeting(ws_url: str, duration: int = 10):
    """Run a complete mock meeting simulation."""
    handy = MockHandy(ws_url)
    
    try:
        # Connect
        await handy.connect()
        await handy.start_session(title="Q4产品规划会议")
        
        # Simulate meeting transcription
        meeting_script = [
            "大家早上好，今天我们讨论Q4的产品规划。",
            "首先张三汇报一下前端进度。",
            "好的，前端目前完成了80%，预计11月15日可以全部完成。",
            "很好，李四负责的后端API呢？",
            "后端API已经完成，11月30日可以联调。",
            "预算方面我们需要在下周三前确认。",
            "还有一个风险点是第三方接口的稳定性。",
            "会议就到这里，大家按计划推进。"
        ]
        
        for text in meeting_script:
            await handy.send_transcription(text)
            await asyncio.sleep(0.5)  # Simulate real-time delay
        
        await handy.end_session()
        
    except Exception as e:
        print(f"[Handy] Error: {e}")
    finally:
        await handy.close()


def main():
    parser = argparse.ArgumentParser(description="Mock Handy client")
    parser.add_argument("--ws-url", default="ws://localhost:8765/ws/meeting/mock-test-001",
                       help="WebSocket URL of meeting skill")
    parser.add_argument("--session-id", help="Custom session ID")
    args = parser.parse_args()
    
    print("=" * 60)
    print("Mock Handy Client - Meeting Skill Integration Test")
    print("=" * 60)
    print()
    
    asyncio.run(run_mock_meeting(args.ws_url))
    
    print()
    print("=" * 60)
    print("Test completed! Check meeting skill output directory.")
    print("=" * 60)


if __name__ == "__main__":
    main()
