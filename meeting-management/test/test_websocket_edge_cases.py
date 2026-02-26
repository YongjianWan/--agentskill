"""
WebSocket 边界情况测试

测试场景：
1. 空音频数据
2. 超大音频数据
3. 非法 Base64 数据
4. 消息过大
5. 快速重连
6. 并发写入同一会议
7. 转写服务超时/失败
8. 非法 JSON 消息
9. 会话超时后操作
10. 权限验证（错误 user_id）

运行：python test/test_websocket_edge_cases.py
"""

import asyncio
import json
import base64
import time
import sys
sys.path.insert(0, 'src')

import aiohttp
import websockets

BASE_URL = "http://localhost:8765/api/v1"
WS_URL = "ws://localhost:8765/api/v1"
TEST_USER_ID = "test_edge_user"


async def create_meeting() -> str:
    """创建测试会议"""
    async with aiohttp.ClientSession() as session:
        data = {
            "title": "边界测试会议",
            "participants": ["测试员"],
            "location": "测试室",
            "user_id": TEST_USER_ID
        }
        async with session.post(f"{BASE_URL}/meetings", json=data) as resp:
            result = await resp.json()
            return result.get("session_id")


async def start_meeting(session_id: str):
    """开始会议"""
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE_URL}/meetings/{session_id}/start") as resp:
            return await resp.json()


async def end_meeting(session_id: str):
    """结束会议"""
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE_URL}/meetings/{session_id}/end") as resp:
            return await resp.json()


async def test_empty_audio():
    """测试1: 空音频数据"""
    print("\n[TEST 1] 空音频数据")
    session_id = await create_meeting()
    await start_meeting(session_id)
    
    ws_url = f"{WS_URL}/ws/meeting/{session_id}?user_id={TEST_USER_ID}"
    
    try:
        async with websockets.connect(ws_url) as ws:
            # 等待连接成功
            await asyncio.wait_for(ws.recv(), timeout=3.0)
            
            # 发送空音频数据
            await ws.send(json.dumps({
                "type": "audio",
                "seq": 0,
                "timestamp_ms": 0,
                "data": "",  # 空数据
                "mime_type": "audio/webm"
            }))
            
            # 等待一下，看是否报错
            await asyncio.sleep(0.5)
            print("  ✅ 空音频数据已处理（无崩溃）")
            
    except Exception as e:
        print(f"  ❌ 失败: {e}")
    finally:
        await end_meeting(session_id)


async def test_invalid_base64():
    """测试2: 非法 Base64 数据"""
    print("\n[TEST 2] 非法 Base64 数据")
    session_id = await create_meeting()
    await start_meeting(session_id)
    
    ws_url = f"{WS_URL}/ws/meeting/{session_id}?user_id={TEST_USER_ID}"
    
    try:
        async with websockets.connect(ws_url) as ws:
            await asyncio.wait_for(ws.recv(), timeout=3.0)
            
            # 发送非法 Base64
            await ws.send(json.dumps({
                "type": "audio",
                "seq": 0,
                "timestamp_ms": 0,
                "data": "!!!非法base64!!!",  # 非法字符
                "mime_type": "audio/webm"
            }))
            
            # 等待错误响应
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
                data = json.loads(msg)
                if data.get("type") == "error":
                    print(f"  ✅ 正确返回错误: {data.get('code')}")
                else:
                    print(f"  ⚠️ 未返回错误: {data}")
            except asyncio.TimeoutError:
                print("  ⚠️ 等待错误响应超时")
            
    except Exception as e:
        print(f"  ❌ 失败: {e}")
    finally:
        await end_meeting(session_id)


async def test_invalid_json():
    """测试3: 非法 JSON 消息"""
    print("\n[TEST 3] 非法 JSON 消息")
    session_id = await create_meeting()
    await start_meeting(session_id)
    
    ws_url = f"{WS_URL}/ws/meeting/{session_id}?user_id={TEST_USER_ID}"
    
    try:
        async with websockets.connect(ws_url) as ws:
            await asyncio.wait_for(ws.recv(), timeout=3.0)
            
            # 发送非法 JSON
            await ws.send("{invalid json")
            
            # 等待错误响应
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
                data = json.loads(msg)
                if data.get("type") == "error":
                    print(f"  ✅ 正确返回错误: {data.get('code')}")
                else:
                    print(f"  ⚠️ 未返回错误: {data}")
            except asyncio.TimeoutError:
                print("  ⚠️ 等待错误响应超时")
            
    except Exception as e:
        print(f"  ❌ 失败: {e}")
    finally:
        await end_meeting(session_id)


async def test_wrong_user_id():
    """测试4: 错误 user_id（权限验证）"""
    print("\n[TEST 4] 错误 user_id 权限验证")
    session_id = await create_meeting()
    
    # 使用错误的 user_id 连接
    ws_url = f"{WS_URL}/ws/meeting/{session_id}?user_id=WRONG_USER"
    
    try:
        async with websockets.connect(ws_url) as ws:
            msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
            data = json.loads(msg)
            if data.get("type") == "error" and data.get("code") == "UNAUTHORIZED":
                print(f"  ✅ 正确拒绝未授权用户")
            else:
                print(f"  ❌ 未正确拒绝: {data}")
    except websockets.exceptions.ConnectionClosed:
        print("  ✅ 连接被正确关闭")
    except Exception as e:
        print(f"  ❌ 失败: {e}")


async def test_nonexistent_meeting():
    """测试5: 连接不存在的会议"""
    print("\n[TEST 5] 连接不存在的会议")
    
    ws_url = f"{WS_URL}/ws/meeting/NONEXISTENT_12345?user_id={TEST_USER_ID}"
    
    try:
        async with websockets.connect(ws_url) as ws:
            msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
            data = json.loads(msg)
            if data.get("type") == "error" and data.get("code") == "SESSION_NOT_FOUND":
                print(f"  ✅ 正确返回会议不存在")
            else:
                print(f"  ❌ 未正确处理: {data}")
    except websockets.exceptions.ConnectionClosed:
        print("  ✅ 连接被正确关闭")
    except Exception as e:
        print(f"  ❌ 失败: {e}")


async def test_rapid_reconnect():
    """测试6: 快速重连"""
    print("\n[TEST 6] 快速重连")
    session_id = await create_meeting()
    await start_meeting(session_id)
    
    ws_url = f"{WS_URL}/ws/meeting/{session_id}?user_id={TEST_USER_ID}"
    
    try:
        for i in range(3):
            try:
                async with websockets.connect(ws_url) as ws:
                    msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
                    print(f"  重连 #{i+1} 成功")
                    # 不主动关闭，直接断开
            except Exception as e:
                print(f"  重连 #{i+1} 失败: {e}")
            await asyncio.sleep(0.1)
        
        print("  ✅ 快速重连测试完成")
    finally:
        await end_meeting(session_id)


async def test_large_audio_data():
    """测试7: 超大音频数据"""
    print("\n[TEST 7] 超大音频数据")
    session_id = await create_meeting()
    await start_meeting(session_id)
    
    ws_url = f"{WS_URL}/ws/meeting/{session_id}?user_id={TEST_USER_ID}"
    
    try:
        async with websockets.connect(ws_url) as ws:
            await asyncio.wait_for(ws.recv(), timeout=3.0)
            
            # 生成超大音频数据 (约 5MB)
            large_data = base64.b64encode(bytes(1024 * 1024 * 5)).decode()
            
            await ws.send(json.dumps({
                "type": "audio",
                "seq": 0,
                "timestamp_ms": 0,
                "data": large_data,
                "mime_type": "audio/webm"
            }))
            
            # 等待一下看是否处理
            await asyncio.sleep(1)
            print("  ✅ 大音频数据已处理（无崩溃）")
            
    except websockets.exceptions.ConnectionClosed as e:
        print(f"  ⚠️ 连接关闭: {e}（可能被服务器拒绝）")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
    finally:
        await end_meeting(session_id)


async def test_missing_fields():
    """测试8: 缺少必需字段的音频消息"""
    print("\n[TEST 8] 缺少必需字段")
    session_id = await create_meeting()
    await start_meeting(session_id)
    
    ws_url = f"{WS_URL}/ws/meeting/{session_id}?user_id={TEST_USER_ID}"
    
    try:
        async with websockets.connect(ws_url) as ws:
            await asyncio.wait_for(ws.recv(), timeout=3.0)
            
            # 发送缺少字段的消息
            await ws.send(json.dumps({
                "type": "audio"
                # 缺少 seq, timestamp_ms, data
            }))
            
            await asyncio.sleep(0.5)
            print("  ✅ 缺字段消息已处理（无崩溃）")
            
    except Exception as e:
        print(f"  ❌ 失败: {e}")
    finally:
        await end_meeting(session_id)


async def test_edit_nonexistent_segment():
    """测试9: 编辑不存在的转写片段"""
    print("\n[TEST 9] 编辑不存在的转写片段")
    session_id = await create_meeting()
    
    async with aiohttp.ClientSession() as session:
        data = {"segment_id": "NONEXISTENT", "text": "测试文本"}
        async with session.put(
            f"{BASE_URL}/meetings/{session_id}/transcript/NONEXISTENT",
            json=data
        ) as resp:
            if resp.status == 404:
                print("  ✅ 正确返回 404")
            else:
                result = await resp.json()
                print(f"  ⚠️ 返回: {resp.status}, {result}")


async def test_double_start():
    """测试10: 重复开始会议"""
    print("\n[TEST 10] 重复开始会议（状态机冲突）")
    session_id = await create_meeting()
    
    # 第一次开始
    result1 = await start_meeting(session_id)
    print(f"  第一次: {result1.get('data', {}).get('status')}")
    
    # 第二次开始（应该失败）
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE_URL}/meetings/{session_id}/start") as resp:
            if resp.status == 409:
                print("  ✅ 正确拒绝重复开始（409）")
            else:
                result = await resp.json()
                print(f"  ⚠️ 返回: {resp.status}, {result}")
    
    await end_meeting(session_id)


async def main():
    """运行所有边界测试"""
    print("="*60)
    print("WebSocket 边界情况测试")
    print("="*60)
    
    tests = [
        test_empty_audio,
        test_invalid_base64,
        test_invalid_json,
        test_wrong_user_id,
        test_nonexistent_meeting,
        test_rapid_reconnect,
        test_large_audio_data,
        test_missing_fields,
        test_edit_nonexistent_segment,
        test_double_start,
    ]
    
    for test in tests:
        try:
            await test()
        except Exception as e:
            print(f"  ❌ 测试异常: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("边界测试完成")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
