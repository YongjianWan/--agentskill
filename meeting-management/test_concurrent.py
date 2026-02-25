#!/usr/bin/env python3
"""测试并发会议场景"""

import asyncio
import websockets
import json
from datetime import datetime

async def simulate_client(client_id, duration=3):
    """模拟一个会议客户端"""
    uri = f"ws://localhost:8765/ws/meeting/test-{client_id}"
    try:
        async with websockets.connect(uri, timeout=5) as ws:
            # 开始会话
            await ws.send(json.dumps({
                "type": "session_start",
                "title": f"并发测试会议-{client_id}"
            }))
            
            # 发送转写片段
            for i in range(duration):
                await ws.send(json.dumps({
                    "type": "transcription",
                    "segment": {
                        "id": f"seg-{client_id}-{i}",
                        "text": f"客户端{client_id}的第{i+1}段话",
                        "start_time_ms": i * 1000
                    }
                }))
                await asyncio.sleep(0.2)
            
            # 结束会话
            await ws.send(json.dumps({
                "type": "session_end",
                "full_text": f"客户端{client_id}的完整转写"
            }))
            
            return f"客户端{client_id}: 成功"
    except Exception as e:
        return f"客户端{client_id}: 失败 - {e}"

async def test_concurrent():
    """测试多客户端并发"""
    print('='*60)
    print('测试并发会议场景')
    print('='*60)
    
    # 先启动服务器
    import sys
    sys.path.insert(0, 'scripts')
    from websocket_server import meeting_manager, handle_websocket
    
    async def route(websocket):
        path = websocket.request.path if hasattr(websocket, 'request') else '/'
        await handle_websocket(websocket, path)
    
    server = await websockets.serve(route, "127.0.0.1", 8766)
    print('服务器启动在 ws://localhost:8766')
    await asyncio.sleep(0.5)
    
    # 并发多个客户端
    clients = [simulate_client(i) for i in range(5)]
    results = await asyncio.gather(*clients)
    
    print()
    print('结果:')
    for r in results:
        print(f'  {r}')
    
    # 检查会话状态
    print()
    print(f'活跃会话数: {len(meeting_manager.sessions)}')
    for sid, session in meeting_manager.sessions.items():
        print(f'  - {sid}: {len(session.segments)} 片段')
    
    server.close()
    await server.wait_closed()
    print()
    print('='*60)
    print('并发测试完成')
    print('='*60)

if __name__ == "__main__":
    asyncio.run(test_concurrent())
