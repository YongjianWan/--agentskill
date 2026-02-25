#!/usr/bin/env python3
"""
完整业务流程演示
模拟 Handy → WebSocket → 会议纪要生成 全流程
"""
import asyncio
import json
import websockets
import subprocess
import time
import sys
from pathlib import Path

# 配置
WS_PORT = 8777
WS_URL = f"ws://localhost:{WS_PORT}/ws/meeting/demo-meeting-001"

# 模拟会议转写数据（真实场景来自 Handy）
MOCK_TRANSCRIPTION = [
    {"text": "大家好，我们开始今天的项目评审会议。", "speaker": "主持人"},
    {"text": "我是张三，负责前端开发。", "speaker": "张三"},
    {"text": "目前进度完成了80%，主要页面都开发完了。", "speaker": "张三"},
    {"text": "李四，你那边后端接口怎么样了？", "speaker": "主持人"},
    {"text": "后端API完成了90%，还有几个接口需要调试。", "speaker": "李四"},
    {"text": "预计下周三可以全部完成。", "speaker": "李四"},
    {"text": "好的，那联调安排在周四可以吗？", "speaker": "主持人"},
    {"text": "没问题，我这边可以配合。", "speaker": "张三"},
    {"text": "李四你负责准备测试环境。", "speaker": "主持人"},
    {"text": "好的，我会在周三前准备好测试环境。", "speaker": "李四"},
]

async def send_mock_handy_data():
    """模拟 Handy 客户端发送数据"""
    print("[MOCK] 模拟 Handy 客户端")
    print(f"   连接到 {WS_URL}")
    
    async with websockets.connect(WS_URL) as ws:
        # 1. 发送 session_start
        await ws.send(json.dumps({
            "type": "session_start",
            "title": "项目评审会议",
            "start_time": "2026-02-25T14:00:00Z"
        }))
        print("\n[SEND] session_start")
        
        # 2. 发送转写片段
        for i, seg in enumerate(MOCK_TRANSCRIPTION):
            msg = {
                "type": "transcription",
                "segment": {
                    "id": f"seg-{i:03d}",
                    "text": seg["text"],
                    "start_time_ms": i * 5000,
                    "is_final": True
                }
            }
            await ws.send(json.dumps(msg))
            print(f"[SEND] [{i+1}/{len(MOCK_TRANSCRIPTION)}]: {seg['text'][:30]}...")
            
            # 接收 ack
            try:
                ack = await asyncio.wait_for(ws.recv(), timeout=1.0)
                ack_data = json.loads(ack)
                if ack_data.get("type") == "ack":
                    print(f"   [RECV] ack")
            except asyncio.TimeoutError:
                pass
            
            await asyncio.sleep(0.1)  # 模拟实时流
        
        # 3. 发送 session_end
        full_text = "\n".join([s["text"] for s in MOCK_TRANSCRIPTION])
        await ws.send(json.dumps({
            "type": "session_end",
            "full_text": full_text
        }))
        print("\n[SEND] session_end")
        
        # 接收确认
        try:
            resp = await asyncio.wait_for(ws.recv(), timeout=2.0)
            resp_data = json.loads(resp)
            if resp_data.get("type") == "session_finalized":
                print(f"[OK] Session finalized!")
                print(f"   Segments: {resp_data.get('segment_count')}")
        except asyncio.TimeoutError:
            print("⚠️ No response received")

def start_websocket_server():
    """启动 WebSocket 服务器"""
    print("[START] 启动 WebSocket 服务器...")
    
    server_script = Path(__file__).parent / "scripts" / "websocket_server.py"
    
    proc = subprocess.Popen(
        [sys.executable, str(server_script), "--port", str(WS_PORT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    
    # 等待服务器启动
    time.sleep(2)
    
    return proc

def generate_minutes_from_log():
    """从转写日志生成会议纪要"""
    print("\n[GEN] 生成会议纪要...")
    
    log_file = Path(__file__).parent / "output" / "demo-meeting-001_stream.log"
    
    if not log_file.exists():
        print(f"[ERR] Log file not found: {log_file}")
        return
    
    # 读取转写内容
    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    print(f"   Loaded {len(lines)} lines")
    
    # 调用 meeting_skill 生成纪要
    sys.path.insert(0, str(Path(__file__).parent / "src"))
    from src.meeting_skill import generate_minutes, save_meeting
    
    full_text = "\n".join([f"[{i}] {line.strip()}" for i, line in enumerate(lines)])
    
    meeting = generate_minutes(
        full_text,
        title="项目评审会议",
        date="2026-02-25",
        participants=["主持人", "张三", "李四"]
    )
    
    files = save_meeting(meeting, output_dir="./output")
    
    print(f"\n[OK] 会议纪要已生成:")
    print(f"   DOCX: {files['docx']}")
    print(f"   JSON: {files['json']}")
    
    # 统计信息
    total_actions = sum(len(t.action_items) for t in meeting.topics)
    print(f"\n[STAT] 统计:")
    print(f"   议题: {len(meeting.topics)}")
    print(f"   行动项: {total_actions}")
    print(f"   风险点: {len(meeting.risks)}")

def main():
    print("=" * 60)
    print("Meeting Management Skill - 完整流程演示")
    print("=" * 60)
    print()
    
    # 1. 启动服务器
    server_proc = start_websocket_server()
    
    try:
        # 2. 模拟 Handy 发送数据
        print("\n" + "-" * 40)
        asyncio.run(send_mock_handy_data())
        
        # 3. 等待日志写入
        time.sleep(1)
        
        # 4. 生成会议纪要
        print("\n" + "-" * 40)
        generate_minutes_from_log()
        
        print("\n" + "=" * 60)
        print("✅ 完整流程演示完成!")
        print("=" * 60)
        
    finally:
        # 清理
        print("\n[STOP] 关闭服务器...")
        server_proc.terminate()
        server_proc.wait()

if __name__ == "__main__":
    main()
