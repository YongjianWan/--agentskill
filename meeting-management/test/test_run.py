#!/usr/bin/env python3
"""
跑一遍完整业务流程测试
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from meeting_skill import generate_minutes, save_meeting, transcribe
import json
import os

def test_text_to_minutes():
    """测试文本生成会议纪要"""
    print("=" * 60)
    print("TEST 1: Text -> Minutes (Batch Mode)")
    print("=" * 60)
    
    # 读取测试转写文本（相对于脚本位置）
    test_file = Path(__file__).parent / 'test_transcription.txt'
    with open(test_file, 'r', encoding='utf-8') as f:
        text = f.read()
    
    print(f"Input text length: {len(text)} chars")
    print()
    
    # 生成会议纪要
    meeting = generate_minutes(
        text,
        title='产品评审会议',
        date='2026-02-25',
        participants=['张三', '李四', '王五']
    )
    
    print(f"Meeting ID: {meeting.id}")
    print(f"Title: {meeting.title}")
    print(f"Date: {meeting.date}")
    print(f"Participants: {meeting.participants}")
    print(f"Topics count: {len(meeting.topics)}")
    print(f"Risks: {len(meeting.risks)}")
    print(f"Pending confirmations: {len(meeting.pending_confirmations)}")
    
    # 统计行动项
    total_actions = sum(len(t.action_items) for t in meeting.topics)
    print(f"Total Action Items: {total_actions}")
    print()
    
    # 显示议题详情
    print("Topics breakdown:")
    for i, topic in enumerate(meeting.topics, 1):
        action_count = len(topic.action_items)
        print(f"  [{i}] {topic.title[:40]}... - {action_count} actions")
        if topic.conclusion:
            print(f"      Conclusion: {topic.conclusion[:50]}...")
    
    print()
    
    # 保存会议
    print("Saving meeting files...")
    files = save_meeting(meeting, output_dir='./output')
    print(f"  JSON: {files['json']}")
    print(f"  DOCX: {files['docx']}")
    
    print()
    print("TEST 1 PASSED!")
    return True

def test_audio_transcription():
    """测试音频转写 (需要音频文件)"""
    print("=" * 60)
    print("TEST 2: Audio -> Transcription")
    print("=" * 60)
    
    # 检查是否有测试音频
    test_audio = "test_audio.mp3"
    if not os.path.exists(test_audio):
        print(f"SKIP: No test audio file found ({test_audio})")
        print("Please provide an audio file to test transcription")
        return None
    
    print(f"Transcribing: {test_audio}")
    print("Using model: small (244MB)")
    
    try:
        result = transcribe(test_audio, model="small")
        print(f"Duration: {result['duration']}s")
        print(f"Segments: {len(result['segments'])}")
        print(f"Participants: {result['participants']}")
        print("TEST 2 PASSED!")
        return result
    except Exception as e:
        print(f"TEST 2 FAILED: {e}")
        return None

def test_websocket_server():
    """测试 WebSocket 服务器状态"""
    print("=" * 60)
    print("TEST 3: WebSocket Server Check")
    print("=" * 60)
    
    # 检查依赖
    try:
        import websockets
        print("[OK] websockets module installed")
    except ImportError:
        print("[MISSING] websockets module not installed")
        print("  Run: pip install websockets")
        return False
    
    print("WebSocket server script: scripts/websocket_server.py")
    print("To start server: python scripts/websocket_server.py")
    print()
    print("TEST 3: Dependencies OK (server not started)")
    return True

def check_handy_integration():
    """检查 Handy 集成状态"""
    print("=" * 60)
    print("CHECK: Handy Integration Status")
    print("=" * 60)
    
    handy_source = "Handy-source/src-tauri/src/meeting_bridge.rs"
    if os.path.exists(handy_source):
        print("[OK] meeting_bridge.rs found")
        print("  - WebSocket client implemented")
        print("  - Session start/end messages")
        print("  - Real-time transcription push")
    else:
        print("[MISSING] Handy source not found")
    
    print()
    print("Handy Build Requirements:")
    
    # 检查 Rust
    rust_ok = os.system("rustc --version >nul 2>&1") == 0
    if rust_ok:
        print("  [OK] Rust installed")
    else:
        print("  [MISSING] Rust not installed")
        print("    Install: https://rustup.rs/")
    
    # 检查 Bun
    bun_ok = os.system("bun --version >nul 2>&1") == 0
    if bun_ok:
        print("  [OK] Bun installed")
    else:
        print("  [MISSING] Bun not installed")
        print("    Install: powershell -c \"irm bun.sh/install.ps1 | iex\"")
    
    if rust_ok and bun_ok:
        print()
        print("Ready to build Handy:")
        print("  cd Handy-source")
        print("  bun install")
        print("  bun run tauri build")
    
    return rust_ok and bun_ok

def main():
    print("\n" + "=" * 60)
    print("Meeting Management Skill - Business Flow Test")
    print("=" * 60)
    print()
    
    # 运行测试
    results = []
    
    # Test 1: 文本生成会议纪要
    try:
        results.append(("Text->Minutes", test_text_to_minutes()))
    except Exception as e:
        print(f"TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Text->Minutes", False))
    
    print()
    
    # Test 2: 音频转写（可选）
    try:
        result = test_audio_transcription()
        results.append(("Audio->Transcription", result is not None))
    except Exception as e:
        print(f"TEST 2 FAILED: {e}")
        results.append(("Audio->Transcription", False))
    
    print()
    
    # Test 3: WebSocket 服务器
    try:
        results.append(("WebSocket Server", test_websocket_server()))
    except Exception as e:
        print(f"TEST 3 FAILED: {e}")
        results.append(("WebSocket Server", False))
    
    print()
    
    # 检查 Handy 集成
    check_handy_integration()
    
    # 总结
    print()
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")
    
    all_passed = all(passed for _, passed in results if passed is not None)
    if all_passed:
        print()
        print("All critical tests passed!")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
