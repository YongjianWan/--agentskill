#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test client for WebSocket server.
Simulates Handy sending transcription data.

Usage:
    python test_client.py --session meeting-001
    python test_client.py --session meeting-001 --file test_transcription.txt
"""

import asyncio
import json
import argparse
import websockets
from datetime import datetime


async def send_test_messages(uri: str, session_id: str, test_text: str = None):
    """Send test messages to WebSocket server."""
    print(f"Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected! Session: {session_id}\n")
            
            # Send metadata
            metadata = {
                "type": "metadata",
                "session_id": session_id,
                "title": "Q4季度规划会议",
                "participants": ["张三", "李四", "王五"],
                "location": "会议室A"
            }
            await websocket.send(json.dumps(metadata))
            print(f"[Sent] Metadata: {metadata['title']}")
            
            # Note: Server may not send ack, continue anyway
            
            await asyncio.sleep(0.5)
            
            if test_text:
                # Send text as segments
                sentences = test_text.replace('。', '.').replace('，', ',').split('.')
                for i, sentence in enumerate(sentences):
                    if not sentence.strip():
                        continue
                    
                    segment = {
                        "type": "transcription",
                        "session_id": session_id,
                        "segment": {
                            "id": f"seg-{i}",
                            "text": sentence.strip(),
                            "start_time_ms": i * 5000,
                            "is_final": True
                        }
                    }
                    await websocket.send(json.dumps(segment))
                    print(f"[Sent] Segment {i}: {sentence.strip()[:50]}...")
                    
                    # Note: Server may not send ack, that's OK
                    await asyncio.sleep(0.1)
                    
                    await asyncio.sleep(0.3)
            else:
                # Send default test messages
                test_messages = [
                    "今天我们来讨论Q4季度的产品规划。",
                    "张三负责前端开发，需要在11月15日前完成用户界面设计。",
                    "李四负责后端API开发，截止日期是11月30日。",
                    "关于预算问题，我们需要在下周三前确认。",
                    "还有一个风险点是第三方接口的稳定性，需要进一步评估。"
                ]
                
                for i, text in enumerate(test_messages):
                    segment = {
                        "type": "transcription",
                        "session_id": session_id,
                        "segment": {
                            "id": f"seg-{i}",
                            "text": text,
                            "start_time_ms": i * 5000,
                            "is_final": True
                        }
                    }
                    await websocket.send(json.dumps(segment))
                    print(f"[Sent] Segment {i}: {text}")
                    
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        print(f"[Recv] {response}")
                    except asyncio.TimeoutError:
                        pass
                    
                    await asyncio.sleep(0.5)
            
            print("\n[Test] Completed successfully!")
            
    except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError, OSError):
        print("[Error] Connection refused. Is the server running?")
        print("   Start server: python websocket_server.py")
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Test WebSocket client")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=8765, help="Server port")
    parser.add_argument("--session", default="test-meeting-001", help="Session ID")
    parser.add_argument("--file", help="Text file to send as transcription")
    args = parser.parse_args()
    
    uri = f"ws://{args.host}:{args.port}/ws/meeting/{args.session}"
    
    # Read file if provided
    test_text = None
    if args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                test_text = f.read()
            print(f"Loaded text from {args.file}: {len(test_text)} chars")
        except FileNotFoundError:
            print(f"File not found: {args.file}")
            return
    
    asyncio.run(send_test_messages(uri, args.session, test_text))


if __name__ == "__main__":
    main()
