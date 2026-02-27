# -*- coding: utf-8 -*-
"""
WebSocket 连接测试脚本
"""

import asyncio
import json
import uuid
import websockets
import requests

# 配置
BASE_URL = "http://localhost:8765"
WS_URL = "ws://localhost:8765"
API_PREFIX = "/api/v1"
HEALTH_ENDPOINT = "/health"  # 健康检查端点


async def test_websocket():
    """测试 WebSocket 连接"""
    
    result = {
        "websocket_ok": False,
        "start_message_ok": False,
        "response_received": False,
        "notes": ""
    }
    
    # 生成测试用的 session_id 和 user_id
    session_id = f"test_{uuid.uuid4().hex[:8]}"
    user_id = f"user_{uuid.uuid4().hex[:8]}"
    
    print("=== WebSocket 测试开始 ===")
    print(f"Session ID: {session_id}")
    print(f"User ID: {user_id}")
    
    websocket = None
    
    try:
        # 1. 测试 WebSocket 连接建立
        ws_url = f"{WS_URL}{API_PREFIX}/ws/meeting/{session_id}?user_id={user_id}"
        print(f"\n[1/4] 连接 WebSocket: {ws_url}")
        
        websocket = await asyncio.wait_for(
            websockets.connect(ws_url),
            timeout=10
        )
        result["websocket_ok"] = True
        print("[OK] WebSocket 连接成功建立")
        
        # 2. 发送 start 消息
        start_msg = {
            "type": "start",
            "title": "测试会议"
        }
        print(f"\n[2/4] 发送 start 消息: {json.dumps(start_msg)}")
        
        await websocket.send(json.dumps(start_msg))
        result["start_message_ok"] = True
        print("[OK] start 消息发送成功")
        
        # 3. 等待响应
        print("\n[3/4] 等待服务器响应...")
        
        try:
            response = await asyncio.wait_for(
                websocket.recv(),
                timeout=10
            )
            result["response_received"] = True
            print(f"[OK] 收到响应: {response}")
            
            # 解析响应
            try:
                resp_data = json.loads(response)
                if resp_data.get("type") == "started":
                    print(f"   - 会议已启动，meeting_id: {resp_data.get('meeting_id')}")
                elif resp_data.get("type") == "error":
                    result["notes"] += f"服务器返回错误: {resp_data.get('message')}"
                    print(f"   [WARN] 服务器返回错误: {resp_data.get('message')}")
            except json.JSONDecodeError:
                result["notes"] += f"响应不是有效的 JSON: {response}"
                print(f"   [WARN] 响应不是有效的 JSON: {response}")
                
        except asyncio.TimeoutError:
            result["notes"] += "等待响应超时（10秒）"
            print("[FAIL] 等待响应超时（10秒）")
        
        # 4. 发送 end 消息
        end_msg = {"type": "end"}
        print(f"\n[4/4] 发送 end 消息: {json.dumps(end_msg)}")
        
        try:
            await websocket.send(json.dumps(end_msg))
            print("[OK] end 消息发送成功")
            
            # 等待 completed 响应
            print("   等待 completed 响应...")
            response = await asyncio.wait_for(
                websocket.recv(),
                timeout=30
            )
            print(f"   收到响应: {response}")
            
            try:
                resp_data = json.loads(response)
                if resp_data.get("type") == "completed":
                    print("   [OK] 会议正常结束")
                elif resp_data.get("type") == "error":
                    result["notes"] += f"; 结束会议时出错: {resp_data.get('message')}"
                    print(f"   [WARN] 结束会议时出错: {resp_data.get('message')}")
            except json.JSONDecodeError:
                pass
                
        except asyncio.TimeoutError:
            result["notes"] += "; 等待 completed 响应超时"
            print("   [WARN] 等待 completed 响应超时（30秒）")
        except Exception as e:
            result["notes"] += f"; 发送 end 消息失败: {e}"
            print(f"   [FAIL] 发送 end 消息失败: {e}")
        
    except asyncio.TimeoutError:
        result["notes"] = "WebSocket 连接超时"
        print("[FAIL] WebSocket 连接超时")
    except ConnectionRefusedError:
        result["notes"] = "连接被拒绝，请检查服务是否运行在 localhost:8765"
        print("[FAIL] 连接被拒绝，请检查服务是否运行在 localhost:8765")
    except Exception as e:
        result["notes"] = f"异常: {type(e).__name__}: {e}"
        print(f"[FAIL] 异常: {type(e).__name__}: {e}")
    finally:
        if websocket:
            try:
                await websocket.close()
                print("\n[OK] WebSocket 连接已关闭")
            except Exception as e:
                print(f"\n[WARN] 关闭 WebSocket 时出错: {e}")
    
    print("\n=== 测试结果 ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    return result


def test_rest_api():
    """测试 REST API 是否正常"""
    print("\n=== 检查 REST API 服务 ===")
    
    try:
        # 健康检查
        resp = requests.get(f"{BASE_URL}{API_PREFIX}{HEALTH_ENDPOINT}", timeout=5)
        if resp.status_code == 200:
            print(f"[OK] 健康检查通过: {resp.json()}")
            return True
        else:
            print(f"[WARN] 健康检查返回非200: {resp.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("[FAIL] 无法连接到服务，请检查服务是否运行在 localhost:8765")
        return False
    except Exception as e:
        print(f"[FAIL] 健康检查异常: {e}")
        return False


async def main():
    """主函数"""
    print("=" * 50)
    print("Meeting Management WebSocket 测试")
    print("=" * 50)
    
    # 先检查 REST API
    if not test_rest_api():
        print("\n[FAIL] 服务未运行，请先启动服务:")
        print("   cd src && uvicorn main:app --host 0.0.0.0 --port 8765")
        return {
            "websocket_ok": False,
            "start_message_ok": False,
            "response_received": False,
            "notes": "服务未运行，请先启动服务"
        }
    
    # 运行 WebSocket 测试
    result = await test_websocket()
    
    return result


if __name__ == "__main__":
    result = asyncio.run(main())
    
    # 最终输出 JSON 格式结果
    print("\n" + "=" * 50)
    print("最终测试结果 (JSON):")
    print("=" * 50)
    print(json.dumps(result, indent=2, ensure_ascii=False))
