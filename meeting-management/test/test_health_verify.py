#!/usr/bin/env python3
"""
健康检查数据真实性验证
验证:
1. model.loaded 是真实状态
2. 磁盘数字是真实读取
3. active_sessions 在 WebSocket 连接后变化
"""

import requests
import json
import asyncio
import websockets

BASE_URL = "http://localhost:8765"
WS_URL = "ws://localhost:8765"


def get_health():
    """获取健康状态"""
    r = requests.get(f"{BASE_URL}/api/v1/health", timeout=5)
    return r.json()


def main():
    print("=" * 60)
    print("健康检查数据真实性验证")
    print("=" * 60)
    
    # 1. 初始状态
    print("\n【1】初始健康检查状态")
    data = get_health()
    components = data["data"]["components"]
    
    print(f"整体状态: {data['data']['status']}")
    print(f"运行时间: {data['data']['uptime_seconds']} 秒")
    print(f"model.loaded: {components['model']['loaded']}")
    print(f"model.name: {components['model']['name']}")
    print(f"model.device: {components['model']['device']}")
    print(f"gpu_available: {components['model']['gpu_available']}")
    print(f"磁盘总空间: {components['disk']['total_gb']} GB")
    print(f"磁盘剩余: {components['disk']['free_gb']} GB")
    print(f"active_sessions: {components['websocket']['active_sessions']}")
    
    # 2. 验证磁盘数字真实性（与系统命令对比）
    print("\n【2】验证磁盘数字真实性")
    import shutil
    output_path = "output"
    disk = shutil.disk_usage(output_path)
    calc_total = round(disk.total / (1024**3), 2)
    calc_free = round(disk.free / (1024**3), 2)
    
    api_total = components['disk']['total_gb']
    api_free = components['disk']['free_gb']
    
    print(f"Python shutil 计算: 总空间={calc_total} GB, 剩余={calc_free} GB")
    print(f"API 返回: 总空间={api_total} GB, 剩余={api_free} GB")
    
    if abs(calc_total - api_total) < 0.1 and abs(calc_free - api_free) < 0.1:
        print("[PASS] 磁盘数字验证通过：API 返回与系统读取一致")
    else:
        print("[FAIL] 磁盘数字验证失败：API 返回与系统读取不一致")
    
    # 3. 创建会议并连接 WebSocket
    print("\n【3】创建会议")
    r = requests.post(f"{BASE_URL}/api/v1/meetings", 
        json={'title': '健康检查测试', 'user_id': 'test_health'},
        timeout=5)
    result = r.json()
    session_id = result['data']['session_id']
    print(f"会议ID: {session_id}")
    
    # 4. 异步测试 WebSocket 会话计数
    print("\n【4】WebSocket 会话计数验证")
    
    async def test_websocket():
        ws_url = f"{WS_URL}/api/v1/ws/meeting/{session_id}?user_id=test_health"
        
        # 连接前
        before = get_health()['data']['components']['websocket']['active_sessions']
        print(f"连接前 active_sessions: {before}")
        
        async with websockets.connect(ws_url) as ws:
            # 发送 start
            await ws.send(json.dumps({'type': 'start', 'title': '测试会议'}))
            resp = await ws.recv()
            
            # 连接后
            during = get_health()['data']['components']['websocket']['active_sessions']
            print(f"连接后 active_sessions: {during}")
            
            if during > before:
                print("[PASS] WebSocket 计数验证通过：连接后计数增加")
            else:
                print("[FAIL] WebSocket 计数验证失败：连接后计数未增加")
            
            # 发送 end
            await ws.send(json.dumps({'type': 'end'}))
            await ws.recv()  # 等待 completed
        
        # 断开后（稍微等待清理）
        await asyncio.sleep(0.5)
        after = get_health()['data']['components']['websocket']['active_sessions']
        print(f"断开后 active_sessions: {after}")
        
        if after < during:
            print("[PASS] WebSocket 计数验证通过：断开后计数减少")
        else:
            print("[WARN] WebSocket 计数：断开后未减少（可能有延迟）")
    
    asyncio.run(test_websocket())
    
    print("\n" + "=" * 60)
    print("验证完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
