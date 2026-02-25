#!/usr/bin/env python3
"""
End-to-End Test for Meeting Management Skill
Tests: WebSocket Server + Transcription + Minutes Generation

Usage:
    python e2e_test.py [--port 8770]
"""

import asyncio
import json
import sys
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

import websockets
from websocket_server import meeting_manager, MeetingSession


class E2ETest:
    """End-to-end test runner."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8770):
        self.host = host
        self.port = port
        self.ws_url = f"ws://{host}:{port}"
        self.session_id = f"e2e-test-{datetime.now().strftime('%H%M%S')}"
        self.output_dir = Path(__file__).parent.parent / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    async def start_server(self):
        """Start WebSocket server."""
        import websocket_server
        
        async def route_handler(websocket):
            path = websocket.request.path if hasattr(websocket, 'request') else '/'
            if path.startswith("/ws/"):
                await websocket_server.handle_websocket(websocket, path)
            else:
                await websocket.close(code=4004, reason="Not found")
        
        self.server = await websockets.serve(route_handler, self.host, self.port)
        print(f"[OK] Server started on {self.ws_url}")
        
    async def simulate_handy_meeting(self):
        """Simulate a complete Handy meeting."""
        uri = f"{self.ws_url}/ws/meeting/{self.session_id}"
        
        print(f"\n[Handy] Connecting as Handy to {uri}...")
        async with websockets.connect(uri) as ws:
            print("[OK] Handy connected")
            
            # 1. Session Start
            await ws.send(json.dumps({
                "type": "session_start",
                "session_id": self.session_id,
                "title": "Q4产品规划评审会",
                "start_time": datetime.utcnow().isoformat() + "Z"
            }))
            print("[OK] Sent session_start")
            await asyncio.sleep(0.5)
            
            # 2. Real meeting transcription
            meeting_content = [
                ("主持人", "大家早上好，今天我们召开Q4产品规划评审会。"),
                ("主持人", "参会人员有张三、李四、王五，大家请确认一下。"),
                ("张三", "我在，前端开发负责人张三。"),
                ("李四", "李四在，后端开发。"),
                ("王五", "王五在，产品经理。"),
                ("主持人", "好，那我们开始。张三先汇报前端进度。"),
                ("张三", "目前前端完成了80%，主要页面都已开发完成。"),
                ("张三", "还需要一周时间进行细节优化，预计11月15日可以全部完成。"),
                ("主持人", "很好，那李四的后端API呢？"),
                ("李四", "后端API已经完成了90%，剩余一些边界情况处理。"),
                ("李四", "我这边11月30日肯定能完成，可以提前给前端联调。"),
                ("王五", "那联调时间定在12月1日到5日可以吗？"),
                ("张三", "可以的，我这边15号完成后可以先自测。"),
                ("李四", "没问题，我也可以提前准备接口文档。"),
                ("主持人", "好的，那确认一下行动项。"),
                ("主持人", "张三负责11月15日前完成前端开发，没问题吧？"),
                ("张三", "确认，保证按时完成。"),
                ("主持人", "李四负责11月30日前完成后端API，并准备接口文档。"),
                ("李四", "确认，12月1日可以开始联调。"),
                ("王五", "我这边负责验收标准制定，下周三前完成。"),
                ("主持人", "还有一个风险点，第三方登录接口最近不稳定，需要关注。"),
                ("李四", "是的，我这边会准备一个备用方案。"),
                ("主持人", "好的，会议就到这里，大家按计划执行。"),
            ]
            
            for i, (speaker, text) in enumerate(meeting_content):
                segment = {
                    "type": "transcription",
                    "session_id": self.session_id,
                    "segment": {
                        "id": f"seg-{i}",
                        "text": f"{speaker}：{text}",
                        "start_time_ms": i * 3000,
                        "end_time_ms": (i + 1) * 3000,
                        "is_final": True,
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    }
                }
                await ws.send(json.dumps(segment, ensure_ascii=False))
                
                # Show progress
                if i % 5 == 0:
                    print(f"   Sent {i}/{len(meeting_content)} segments...")
                
                await asyncio.sleep(0.1)
            
            print(f"[OK] Sent {len(meeting_content)} transcription segments")
            
            # 3. Session End
            await ws.send(json.dumps({
                "type": "session_end",
                "session_id": self.session_id,
                "end_time": datetime.utcnow().isoformat() + "Z",
                "full_text": " ".join([t for _, t in meeting_content])
            }))
            print("[OK] Sent session_end")
            
            # Wait for server to process
            await asyncio.sleep(1)
            
    async def generate_minutes(self):
        """Generate meeting minutes from transcription."""
        print("\n[Gen] Generating meeting minutes...")
        
        session = meeting_manager.get_session(self.session_id)
        if not session:
            print("[FAIL] Session not found")
            return False
        
        # Get log file
        log_file = self.output_dir / f"{self.session_id}_stream.log"
        
        # Generate minutes using generate_minutes.py
        result = subprocess.run([
            sys.executable,
            "generate_minutes.py",
            "--input", str(log_file),
            "--title", session.title,
            "--output-dir", str(self.output_dir)
        ], capture_output=True, text=True, cwd=Path(__file__).parent)
        
        if result.returncode == 0:
            print("[OK] Meeting minutes generated")
            # Find generated files
            timestamp = datetime.now().strftime('%Y%m%d')
            docx_files = list(self.output_dir.glob(f"meeting_minutes_{timestamp}*.docx"))
            json_files = list(self.output_dir.glob(f"actions_{timestamp}*.json"))
            
            if docx_files:
                print(f"   [DOCX] {docx_files[-1].name}")
            if json_files:
                print(f"   [JSON] {json_files[-1].name}")
            return True
        else:
            print(f"[FAIL] Failed to generate minutes: {result.stderr}")
            return False
            
    async def verify_output(self):
        """Verify generated output files."""
        print("\n[Verify] Verifying output files...")
        
        files = list(self.output_dir.glob(f"{self.session_id}*"))
        if files:
            print(f"[OK] Found {len(files)} output files:")
            for f in files:
                size_kb = f.stat().st_size / 1024
                print(f"   - {f.name} ({size_kb:.2f} KB)")
            return True
        else:
            print("[FAIL] No output files found")
            return False
            
    async def run(self):
        """Run complete E2E test."""
        print("=" * 60)
        print("End-to-End Test: Meeting Management Skill")
        print("=" * 60)
        
        try:
            # Step 1: Start server
            await self.start_server()
            await asyncio.sleep(1)
            
            # Step 2: Simulate Handy meeting
            await self.simulate_handy_meeting()
            
            # Step 3: Generate minutes
            minutes_ok = await self.generate_minutes()
            
            # Step 4: Verify output
            output_ok = await self.verify_output()
            
            # Cleanup
            self.server.close()
            await self.server.wait_closed()
            
            # Results
            print("\n" + "=" * 60)
            if minutes_ok and output_ok:
                print("[OK] E2E TEST PASSED")
            else:
                print("[FAIL] E2E TEST FAILED")
            print("=" * 60)
            
            print(f"\n[Dir] Output directory: {self.output_dir.absolute()}")
            print(f"[Key] Session ID: {self.session_id}")
            
        except Exception as e:
            print(f"\n[FAIL] Test error: {e}")
            import traceback
            traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(description="E2E Test")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8770)
    args = parser.parse_args()
    
    test = E2ETest(args.host, args.port)
    asyncio.run(test.run())


if __name__ == "__main__":
    main()
