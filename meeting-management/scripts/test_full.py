#!/usr/bin/env python3
"""
Full integration test for meeting management skill.
Starts WebSocket server, sends test data, generates minutes.

Usage:
    python test_full.py [--port 8768]
"""

import asyncio
import json
import sys
import argparse
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

import websockets
from websocket_server import meeting_manager
from generate_minutes import MeetingMinutes, MeetingTopic, ActionItem, create_docx, create_actions_json


async def start_test_server(host: str, port: int):
    """Start WebSocket server for testing."""
    import websocket_server
    
    async def route_handler(websocket):
        path = websocket.request.path if hasattr(websocket, 'request') else '/'
        if path.startswith("/ws/"):
            await websocket_server.handle_websocket(websocket, path)
        else:
            await websocket.close(code=4004, reason="Not found")
    
    server = await websockets.serve(route_handler, host, port)
    print(f"[Server] Started on ws://{host}:{port}")
    return server


async def send_test_data(uri: str, session_id: str):
    """Send test meeting data."""
    print(f"[Client] Connecting to {uri}...")
    
    async with websockets.connect(uri) as websocket:
        print("[Client] Connected!")
        
        # Send metadata
        metadata = {
            "type": "metadata",
            "session_id": session_id,
            "title": "Q4季度产品规划会议",
            "participants": ["张三", "李四", "王五"],
            "location": "会议室A"
        }
        await websocket.send(json.dumps(metadata))
        print(f"[Client] Sent metadata: {metadata['title']}")
        await asyncio.sleep(0.5)
        
        # Send transcription segments
        test_messages = [
            "今天我们来讨论Q4季度的产品规划。",
            "首先，张三负责前端开发，需要在11月15日前完成用户界面设计。",
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
            print(f"[Client] Sent segment {i}: {text[:30]}...")
            
            # Wait for ack
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=1)
                ack = json.loads(response)
                if ack.get("type") == "ack":
                    print(f"[Client] Received ack for segment {i}")
            except asyncio.TimeoutError:
                pass
            
            await asyncio.sleep(0.3)
        
        print("[Client] All data sent!")


async def main():
    parser = argparse.ArgumentParser(description="Full integration test")
    parser.add_argument("--host", default="127.0.0.1", help="Host")
    parser.add_argument("--port", type=int, default=8768, help="Port")
    args = parser.parse_args()
    
    session_id = "test-meeting-full"
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    
    # Step 1: Start server
    print("=" * 50)
    print("Step 1: Starting WebSocket server...")
    print("=" * 50)
    server = await start_test_server(args.host, args.port)
    await asyncio.sleep(1)
    
    # Step 2: Send test data
    print("\n" + "=" * 50)
    print("Step 2: Sending test meeting data...")
    print("=" * 50)
    uri = f"ws://{args.host}:{args.port}/ws/meeting/{session_id}"
    await send_test_data(uri, session_id)
    
    # Step 3: Finalize session
    print("\n" + "=" * 50)
    print("Step 3: Finalizing session...")
    print("=" * 50)
    session = meeting_manager.finalize_session(session_id)
    if session:
        log_file = meeting_manager.save_transcription_log(session)
        print(f"[Server] Session finalized: {session_id}")
        print(f"[Server] Transcription log: {log_file}")
        print(f"[Server] Total segments: {len(session.segments)}")
        
        # Step 4: Generate minutes
        print("\n" + "=" * 50)
        print("Step 4: Generating meeting minutes...")
        print("=" * 50)
        
        # Build minutes from session data
        minutes = MeetingMinutes(
            title=session.title,
            participants=session.participants,
            location=session.location
        )
        
        # Create a topic from all transcription
        full_text = " ".join([s.text for s in session.segments])
        topic = MeetingTopic(
            title="会议讨论",
            discussion_points=[s.text for s in session.segments]
        )
        
        # Extract action items (simple regex)
        import re
        action_patterns = [
            r'([\u4e00-\u9fa5]{2,4}).*?(?:负责|需要|要)(.+?)(?:在|于)(.+?)(?:前|之前)',
        ]
        for pattern in action_patterns:
            matches = re.finditer(pattern, full_text)
            for m in matches:
                topic.action_items.append(ActionItem(
                    action=m.group(2).strip(),
                    owner=m.group(1).strip(),
                    deadline=m.group(3).strip() if len(m.groups()) > 2 else None,
                    source="会议讨论"
                ))
        
        # Add risk items
        if '风险' in full_text:
            risk_match = re.search(r'风险点[^。]*', full_text)
            if risk_match:
                minutes.risks.append(risk_match.group(0))
        
        minutes.topics.append(topic)
        
        # Save outputs
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        docx_path = output_dir / f"meeting_minutes_{timestamp}.docx"
        create_docx(minutes, str(docx_path))
        
        json_path = output_dir / f"actions_{timestamp}.json"
        create_actions_json(minutes, str(json_path))
        
        print(f"\n[Output] Generated files:")
        print(f"  - {docx_path}")
        print(f"  - {json_path}")
        print(f"  - {log_file}")
        
    else:
        print(f"[Error] Session not found: {session_id}")
    
    # Cleanup
    print("\n" + "=" * 50)
    print("Step 5: Cleanup...")
    print("=" * 50)
    server.close()
    await server.wait_closed()
    print("[Server] Stopped")
    
    print("\n" + "=" * 50)
    print("Test completed successfully!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
