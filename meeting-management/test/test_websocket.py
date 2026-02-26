"""
WebSocket 实时转写测试脚本

测试功能：
1. 创建会议
2. 连接 WebSocket
3. 发送模拟音频数据
4. 接收实时转写结果
5. 结束会议
6. 查询转写结果
7. 测试转写文本编辑

运行：python test/test_websocket.py
"""

import asyncio
import json
import base64
import random
import websockets
import aiohttp
from datetime import datetime

# API 基础配置
BASE_URL = "http://localhost:8765/api/v1"
WS_URL = "ws://localhost:8765/api/v1"

# 测试用户
TEST_USER_ID = "test_user_001"


async def create_meeting() -> str:
    """创建测试会议"""
    async with aiohttp.ClientSession() as session:
        data = {
            "title": f"WebSocket 测试会议 - {datetime.now().strftime('%H:%M:%S')}",
            "participants": ["测试员"],
            "location": "测试室",
            "user_id": TEST_USER_ID
        }
        async with session.post(f"{BASE_URL}/meetings", json=data) as resp:
            result = await resp.json()
            session_id = result.get("session_id")
            print(f"✅ 会议创建成功: {session_id}")
            return session_id


async def start_meeting(session_id: str):
    """开始会议"""
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE_URL}/meetings/{session_id}/start") as resp:
            result = await resp.json()
            print(f"✅ 会议已开始: {result['data']['status']}")


async def end_meeting(session_id: str):
    """结束会议"""
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE_URL}/meetings/{session_id}/end") as resp:
            result = await resp.json()
            print(f"✅ 会议已结束: {result['data']['status']}")


async def get_transcript(session_id: str):
    """获取转写文本"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/meetings/{session_id}/transcript") as resp:
            result = await resp.json()
            segments = result.get("data", {}).get("segments", [])
            full_text = result.get("data", {}).get("full_text", "")
            print(f"📄 转写片段数: {len(segments)}")
            if full_text:
                print(f"📝 转写预览: {full_text[:100]}...")
            return segments


async def update_transcript(session_id: str, segment_id: str, new_text: str):
    """更新转写文本"""
    async with aiohttp.ClientSession() as session:
        data = {"segment_id": segment_id, "text": new_text}
        async with session.put(
            f"{BASE_URL}/meetings/{session_id}/transcript/{segment_id}",
            json=data
        ) as resp:
            result = await resp.json()
            if result.get("code") == 0:
                print(f"✅ 转写更新成功: {segment_id}")
            else:
                print(f"❌ 转写更新失败: {result}")


def generate_mock_audio_data() -> str:
    """生成模拟音频数据（Base64）"""
    # 生成随机音频数据（实际测试中应该是真实的音频数据）
    mock_audio = bytes(random.randint(0, 255) for _ in range(1024))
    return base64.b64encode(mock_audio).decode('utf-8')


async def test_websocket_realtime_transcription():
    """测试 WebSocket 实时转写全流程"""
    print("\n" + "="*60)
    print("WebSocket 实时转写测试")
    print("="*60)
    
    # 1. 创建会议
    session_id = await create_meeting()
    
    # 2. 开始会议
    await start_meeting(session_id)
    
    # 3. 连接 WebSocket
    ws_url = f"{WS_URL}/ws/meeting/{session_id}?user_id={TEST_USER_ID}"
    print(f"🔌 连接 WebSocket: {ws_url}")
    
    transcript_results = []
    
    try:
        async with websockets.connect(ws_url) as ws:
            # 等待连接成功消息
            msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(msg)
            print(f"📨 收到: {data['type']}")
            
            # 4. 发送音频数据（模拟）
            print("\n🎤 发送音频数据...")
            for i in range(5):
                audio_msg = {
                    "type": "audio",
                    "seq": i,
                    "timestamp_ms": i * 5000,
                    "data": generate_mock_audio_data(),
                    "mime_type": "audio/webm;codecs=opus"
                }
                await ws.send(json.dumps(audio_msg))
                print(f"  发送音频片段 #{i}")
                await asyncio.sleep(0.5)  # 模拟发送间隔
            
            print("\n⏳ 等待转写结果...")
            
            # 5. 接收转写结果（最多等待10秒）
            try:
                while len(transcript_results) < 3:
                    msg = await asyncio.wait_for(ws.recv(), timeout=10.0)
                    data = json.loads(msg)
                    
                    if data.get("type") == "transcript":
                        print(f"  📝 转写: {data['text']}")
                        transcript_results.append(data)
                    elif data.get("type") == "status":
                        print(f"  📊 状态: {data}")
                    elif data.get("type") == "error":
                        print(f"  ⚠️ 错误: {data}")
                        break
                        
            except asyncio.TimeoutError:
                print("  ⏱️ 等待转写结果超时")
    
    except Exception as e:
        print(f"❌ WebSocket 错误: {e}")
    
    # 6. 结束会议
    print("\n🛑 结束会议...")
    await end_meeting(session_id)
    
    # 7. 查询转写结果
    print("\n📋 查询转写结果...")
    await asyncio.sleep(1)  # 等待数据处理完成
    segments = await get_transcript(session_id)
    
    # 8. 测试转写编辑
    if segments:
        print("\n✏️ 测试转写编辑...")
        segment_id = segments[0]["id"]
        await update_transcript(session_id, segment_id, "这是编辑后的测试文本")
        
        # 验证编辑结果
        segments_after = await get_transcript(session_id)
        for seg in segments_after:
            if seg["id"] == segment_id:
                print(f"  编辑后: {seg['text']}")
    
    print("\n" + "="*60)
    print(f"测试完成! 收到 {len(transcript_results)} 条转写结果")
    print("="*60)
    
    return session_id, transcript_results


async def test_websocket_concurrent():
    """测试多个会议并发连接"""
    print("\n" + "="*60)
    print("并发连接测试")
    print("="*60)
    
    async def single_test(index: int):
        session_id = await create_meeting()
        await start_meeting(session_id)
        
        ws_url = f"{WS_URL}/ws/meeting/{session_id}?user_id={TEST_USER_ID}_{index}"
        
        try:
            async with websockets.connect(ws_url) as ws:
                # 等待连接成功
                await asyncio.wait_for(ws.recv(), timeout=5.0)
                
                # 发送少量数据
                for i in range(2):
                    await ws.send(json.dumps({
                        "type": "audio",
                        "seq": i,
                        "timestamp_ms": i * 1000,
                        "data": generate_mock_audio_data(),
                        "mime_type": "audio/webm"
                    }))
                    await asyncio.sleep(0.1)
                
                # 等待结果
                await asyncio.sleep(2)
                
                await end_meeting(session_id)
                print(f"  会议 {index+1} 完成")
                return True
        except Exception as e:
            print(f"  会议 {index+1} 失败: {e}")
            return False
    
    # 并发运行3个测试
    tasks = [single_test(i) for i in range(3)]
    results = await asyncio.gather(*tasks)
    
    success_count = sum(results)
    print(f"\n✅ 成功: {success_count}/{len(results)}")


async def main():
    """主测试入口"""
    print("\n🚀 开始 WebSocket 测试")
    print(f"API: {BASE_URL}")
    
    try:
        # 测试1: 基本实时转写
        await test_websocket_realtime_transcription()
        
        # 测试2: 并发连接（可选）
        # await test_websocket_concurrent()
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
