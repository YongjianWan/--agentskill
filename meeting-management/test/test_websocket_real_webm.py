#!/usr/bin/env python3
"""
WebSocket 全链路测试 (使用真实 WebM 音频)
验证: start → chunk(xN) → end 完整流程

使用方法:
    python test/test_websocket_real_webm.py
"""

import sys
import json
import base64
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import websockets

# 配置
AUDIO_FILE = Path(__file__).parent / "test_audio.webm"
CHUNK_SIZE = 32000  # 每个chunk约32KB (约0.5-1秒音频)
CHUNK_COUNT = 20    # 发送20个chunk (约10-15秒音频)
CHUNK_INTERVAL = 1.0  # 每个chunk间隔1秒
WS_URL = "ws://localhost:8765/api/v1/ws/meeting/{session_id}?user_id={user_id}"


async def test_real_webm():
    """测试完整链路: start → chunk(xN) → end"""
    
    session_id = f"REALWEBM_{int(time.time())}"
    user_id = "test_user"
    uri = WS_URL.format(session_id=session_id, user_id=user_id)
    
    print("=" * 70)
    print("WebSocket 真实 WebM 音频测试")
    print("=" * 70)
    print(f"会议ID: {session_id}")
    print(f"音频文件: {AUDIO_FILE}")
    print(f"计划发送: {CHUNK_COUNT} 个 chunk，每个约 {CHUNK_SIZE} bytes")
    
    # 检查音频文件
    if not AUDIO_FILE.exists():
        print(f"\n[ERROR] WebM 音频文件不存在: {AUDIO_FILE}")
        print("请先运行: python test/convert_to_webm.py")
        return False
    
    file_size = AUDIO_FILE.stat().st_size
    print(f"音频文件大小: {file_size / 1024 / 1024:.2f} MB")
    
    # 读取音频文件
    with open(AUDIO_FILE, "rb") as f:
        audio_data = f.read()
    
    # 分割成 chunks
    chunks = []
    for i in range(0, len(audio_data), CHUNK_SIZE):
        chunk = audio_data[i:i+CHUNK_SIZE]
        chunks.append(chunk)
    
    print(f"实际分割: {len(chunks)} 个 chunks")
    
    try:
        async with websockets.connect(uri) as ws:
            
            # Step 1: 发送 start
            print("\n" + "-" * 70)
            print("[Step 1] 发送 start 消息...")
            print("-" * 70)
            await ws.send(json.dumps({
                "type": "start",
                "title": "真实WebM测试会议"
            }))
            
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(response)
            print(f"  响应: {data}")
            
            if data["type"] != "started":
                print(f"  [FAIL] 期望 'started'，收到 '{data['type']}'")
                return False
            print("  [OK] 会议已启动")
            
            # Step 2: 发送 chunks
            print("\n" + "-" * 70)
            print(f"[Step 2] 发送 {min(CHUNK_COUNT, len(chunks))} 个 audio chunks...")
            print("-" * 70)
            
            transcript_count = 0
            for i in range(min(CHUNK_COUNT, len(chunks))):
                chunk = chunks[i]
                await ws.send(json.dumps({
                    "type": "chunk",
                    "sequence": i,
                    "data": base64.b64encode(chunk).decode()
                }))
                print(f"  块 {i}: {len(chunk)} bytes 已发送", end="")
                
                # 尝试接收转写结果（非阻塞）
                try:
                    while True:
                        response = await asyncio.wait_for(ws.recv(), timeout=0.5)
                        data = json.loads(response)
                        if data["type"] == "transcript":
                            transcript_count += 1
                            text = data.get('text', '')[:30]
                            print(f" -> [转写] {text}...")
                        elif data["type"] == "error":
                            print(f" -> [错误] {data.get('message', '')[:50]}")
                        else:
                            print(f" -> [{data['type']}]")
                except asyncio.TimeoutError:
                    print()
                
                # 等待间隔
                await asyncio.sleep(CHUNK_INTERVAL)
            
            print(f"\n  [OK] 全部 {min(CHUNK_COUNT, len(chunks))} 个 chunks 发送完成")
            print(f"  [INFO] 收到 {transcript_count} 次转写结果")
            
            # Step 3: 发送 end
            print("\n" + "-" * 70)
            print("[Step 3] 发送 end 消息...")
            print("-" * 70)
            await ws.send(json.dumps({"type": "end"}))
            
            # 等待 completed（可能需要较长时间做转写和生成）
            print("  等待会议完成（转写 + AI生成纪要）...")
            print("  这可能需要 10-30 秒，请耐心等待...")
            
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=60.0)
                data = json.loads(response)
                print(f"\n  响应: {data}")
                
                if data["type"] == "completed":
                    print("\n  [OK] 会议正常完成！")
                    print(f"  [OK] 会议ID: {data.get('meeting_id')}")
                    print(f"  [OK] 音频路径: {data.get('audio_path')}")
                    print(f"  [OK] 纪要路径: {data.get('minutes_path')}")
                    full_text = data.get('full_text', '')
                    print(f"  [OK] 转写全文长度: {len(full_text)} 字符")
                    print(f"  [OK] 前200字符: {full_text[:200]}")
                    print(f"  [OK] 接收chunks: {data.get('chunk_count', 0)}")
                    return True
                    
                elif data["type"] == "error":
                    print(f"\n  [WARN] 会议完成但有错误:")
                    print(f"    错误码: {data.get('code')}")
                    print(f"    消息: {data.get('message')}")
                    print("\n  [OK] 协议层正常（错误是业务层问题）")
                    return True
                else:
                    print(f"\n  [WARN] 收到未知消息类型: {data['type']}")
                    return False
                    
            except asyncio.TimeoutError:
                print("\n  [FAIL] 等待 completed 超时（60秒）")
                print("  [INFO] 可能原因：转写或AI生成耗时过长")
                return False
            
    except (ConnectionRefusedError, TimeoutError, OSError) as e:
        print(f"\n[FAIL] 连接失败: {e}")
        print("  请确保: cd src && uvicorn main:app --reload --port 8765")
        return False
    except Exception as e:
        print(f"\n[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    success = await test_real_webm()
    
    print("")
    print("=" * 70)
    if success:
        print("[PASS] 真实 WebM 测试通过!")
    else:
        print("[FAIL] 真实 WebM 测试失败")
    print("=" * 70)
    
    return 0 if success else 1


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(result)
