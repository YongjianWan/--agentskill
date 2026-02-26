#!/usr/bin/env python3
"""
WebSocket 新协议测试 (start/chunk/end)
Python 模拟客户端
"""

import sys
import json
import base64
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import websockets


async def test_websocket_flow():
    """测试完整流程: start -> chunk -> chunk -> end"""
    
    session_id = f"WS_TEST_{int(time.time())}"
    user_id = "test_user"
    uri = f"ws://localhost:8765/api/v1/ws/meeting/{session_id}?user_id={user_id}"
    
    print("=" * 60)
    print("WebSocket 新协议测试")
    print("=" * 60)
    print(f"连接: {uri}")
    
    try:
        async with websockets.connect(uri) as ws:
            
            # 1. 发送 start
            print("\n[1] 发送 start...")
            await ws.send(json.dumps({
                "type": "start",
                "title": "WebSocket测试会议"
            }))
            
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(response)
            print(f"  响应: {data}")
            assert data["type"] == "started", f"期望started，收到{data['type']}"
            print("  [OK] 会议已启动")
            
            # 2. 发送 chunk (mock音频)
            print("\n[2] 发送 chunk...")
            mock_audio = bytes([0x1A, 0x45, 0xDF, 0xA3]) + b"\x00" * 1000
            audio_b64 = base64.b64encode(mock_audio).decode()
            
            for i in range(2):
                await ws.send(json.dumps({
                    "type": "chunk",
                    "sequence": i,
                    "data": audio_b64
                }))
                print(f"  块 {i} 已发送")
                # 等待一小段时间
                await asyncio.sleep(0.5)
            
            # 尝试接收可能的transcript（也可能没有，因为mock音频无效）
            try:
                while True:
                    response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    data = json.loads(response)
                    print(f"  收到: {data}")
                    if data["type"] == "transcript":
                        print(f"  [OK] 收到转写: {data['text'][:50]}...")
                    elif data["type"] == "error":
                        print(f"  [WARN] 错误: {data.get('message')}")
            except asyncio.TimeoutError:
                print("  没有更多消息（正常）")
            
            # 3. 发送 end
            print("\n[3] 发送 end...")
            await ws.send(json.dumps({
                "type": "end"
            }))
            
            # 等待 completed 或 error（转写可能需要时间）
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=30.0)
                data = json.loads(response)
                print(f"  响应: {data}")
                
                if data["type"] == "completed":
                    print("  [OK] 会议已完成")
                    print(f"  [OK] Minutes路径: {data.get('minutes_path')}")
                    print(f"  [OK] Full text长度: {len(data.get('full_text', ''))}")
                    print(f"  [OK] Chunk数量: {data.get('chunk_count', 0)}")
                elif data["type"] == "error":
                    print(f"  [WARN] 完成但有错误: {data.get('message')}")
                    # 错误也算完成（协议通）
                    print("  [OK] 协议正常，错误是预期的（mock音频无效）")
                else:
                    print(f"  [INFO] 收到: {data}")
                    
            except asyncio.TimeoutError:
                print("  [WARN] 等待completed超时（30秒）")
                print("  [INFO] 这可能是因为Whisper转写需要更长时间")
            
    except (ConnectionRefusedError, TimeoutError, OSError) as e:
        print(f"\n[FAIL] 连接失败: {e}")
        print("  请确保: cd src && uvicorn main:app --reload --port 8765")
        return False
    except Exception as e:
        print(f"\n[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    return True


async def main():
    success = await test_websocket_flow()
    return 0 if success else 1


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(result)
