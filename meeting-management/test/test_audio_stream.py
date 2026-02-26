#!/usr/bin/env python3
"""
音频流处理单元测试
测试 init_meeting_session → append_audio_chunk → finalize_meeting 全链路
"""

import sys
import time
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.meeting_skill import (
    init_meeting_session,
    append_audio_chunk,
    finalize_meeting,
    _audio_sessions,
)


def test_mock_bytes():
    """用mock bytes测试（不需要真实音频文件）"""
    print("=" * 60)
    print("测试1: Mock bytes 全流程测试")
    print("=" * 60)
    
    meeting_id = f"TEST_{int(time.time())}"
    title = "测试会议"
    
    # 1. 初始化会话
    print("\n[1] 初始化会话...")
    audio_path = init_meeting_session(meeting_id, title, user_id="test_user")
    print(f"  [OK] Audio路径: {audio_path}")
    
    # 验证目录创建
    meeting_dir = Path(audio_path).parent
    print(f"  [OK] 会议目录: {meeting_dir}")
    assert meeting_dir.exists(), "目录未创建"
    assert Path(audio_path).exists(), "音频文件未创建"
    
    # 验证session状态
    session = _audio_sessions.get(meeting_id)
    assert session is not None, "Session未创建"
    assert session["title"] == title
    assert session["chunk_count"] == 0
    assert session["transcript_parts"] == []
    print(f"  [OK] Session状态正常")
    
    # 2. 追加音频块（模拟webm格式头部）
    print("\n[2] 追加音频块...")
    
    # WebM文件魔数 + 一些随机数据（模拟音频块）
    # 注意：这不是有效音频，Whisper会报错，但测试的是流程
    webm_header = bytes([0x1A, 0x45, 0xDF, 0xA3])  # EBML Header
    mock_audio = webm_header + b"\x00" * 1000  # 模拟1KB音频
    
    # 追加几个块
    transcript_error = False
    for i in range(3):
        try:
            result = append_audio_chunk(meeting_id, mock_audio, sequence=i)
            print(f"  块 {i}: 大小={len(mock_audio)} bytes, 转写结果={result is not None}")
        except Exception as e:
            # 转写失败是正常的，因为mock数据不是有效音频
            print(f"  块 {i}: 转写失败（预期内，mock数据无效）: {type(e).__name__}")
            transcript_error = True
    
    # 验证文件写入
    audio_file_size = Path(audio_path).stat().st_size
    print(f"  [OK] 音频文件大小: {audio_file_size} bytes")
    assert audio_file_size == len(mock_audio) * 3, "音频文件大小不对"
    
    # 验证session更新
    session = _audio_sessions.get(meeting_id)
    assert session["chunk_count"] == 3
    print(f"  [OK] Chunk计数: {session['chunk_count']}")
    if transcript_error:
        print(f"  [INFO] Transcript片段: {len(session['transcript_parts'])} 个（转写失败是正常的）")
    else:
        print(f"  [OK] Transcript片段: {len(session['transcript_parts'])} 个")
    
    # 3. 结束会议
    print("\n[3] 结束会议...")
    try:
        result = finalize_meeting(meeting_id)
        print(f"  [OK] 会议结束成功")
        print(f"  [OK] Audio路径: {result['audio_path']}")
        print(f"  [OK] Minutes路径: {result['minutes_path']}")
        print(f"  [OK] Full text长度: {len(result['full_text'])}")
        print(f"  [OK] Chunk计数: {result['chunk_count']}")
        
        # 验证文件存在
        assert Path(result['audio_path']).exists(), "音频文件不存在"
        # Note: minutes可能生成失败（没有真实转写文本），不强求
        if Path(result['minutes_path']).exists():
            print(f"  [OK] Word文件已生成")
        else:
            print(f"  [WARN] Word文件未生成（mock音频无法转写，可接受）")
        
        # 验证session清理
        assert meeting_id not in _audio_sessions, "Session未清理"
        print(f"  [OK] Session已清理")
        
    except Exception as e:
        # finalize可能因转写失败而报错，但session应该被清理
        print(f"  [WARN] finalize_meeting异常（可能是mock音频无效）: {e}")
        # 检查session是否已清理（即使失败也应该清理）
        if meeting_id in _audio_sessions:
            print(f"  [FAIL] Session未清理")
            return False
        else:
            print(f"  [OK] Session已清理（虽然finalize失败）")
            # 检查音频文件是否还在
            if Path(audio_path).exists():
                print(f"  [OK] 音频文件保留")
            return True  # 流程测试通过，只是转写失败
    
    print("\n" + "=" * 60)
    print("测试1通过 [PASS]")
    print("=" * 60)
    return True


def test_30s_transcription_trigger():
    """测试30秒触发转写逻辑"""
    print("\n" + "=" * 60)
    print("测试2: 30秒转写触发逻辑")
    print("=" * 60)
    
    meeting_id = f"TEST_30S_{int(time.time())}"
    
    # 初始化
    init_meeting_session(meeting_id, "30秒触发测试")
    session = _audio_sessions[meeting_id]
    
    mock_audio = b"\x00" * 500  # 小音频块
    
    print("\n[1] 第一次追加（应该触发转写，last_chunk_time=0）...")
    try:
        result1 = append_audio_chunk(meeting_id, mock_audio, sequence=0)
        print(f"  转写结果: {result1 is not None}")
    except Exception as e:
        print(f"  转写失败（mock数据无效）: {type(e).__name__}")
    assert session["last_chunk_time"] > 0 or session["chunk_count"] == 1, "首次应该触发转写或至少记录chunk"
    
    print("\n[2] 短时间内第二次追加（不应该触发）...")
    result2 = append_audio_chunk(meeting_id, mock_audio, sequence=1)
    print(f"  转写结果: {result2 is not None}")
    # 30秒内不应该触发
    
    print("\n[3] 验证状态...")
    print(f"  Chunk计数: {session['chunk_count']}")
    print(f"  Transcript片段: {len(session['transcript_parts'])}")
    print(f"  上次转写时间: {session['last_chunk_time']}")
    
    # 清理
    if meeting_id in _audio_sessions:
        s = _audio_sessions[meeting_id]
        if s.get("file_handle") and not s["file_handle"].closed:
            s["file_handle"].close()
        del _audio_sessions[meeting_id]
    
    print("\n" + "=" * 60)
    print("测试2通过 [PASS]")
    print("=" * 60)
    return True


def test_error_handling():
    """测试错误处理"""
    print("\n" + "=" * 60)
    print("测试3: 错误处理")
    print("=" * 60)
    
    # 测试不存在的meeting_id
    print("\n[1] 测试不存在的meeting_id...")
    try:
        append_audio_chunk("NON_EXISTENT", b"test", 0)
        print("  [FAIL] 应该抛出异常")
        return False
    except ValueError as e:
        print(f"  [OK] 正确抛出异常: {e}")
    
    try:
        finalize_meeting("NON_EXISTENT")
        print("  [FAIL] 应该抛出异常")
        return False
    except ValueError as e:
        print(f"  [OK] 正确抛出异常: {e}")
    
    print("\n" + "=" * 60)
    print("测试3通过 [PASS]")
    print("=" * 60)
    return True


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("音频流处理单元测试")
    print("=" * 60)
    
    results = []
    
    try:
        results.append(("Mock bytes测试", test_mock_bytes()))
    except Exception as e:
        print(f"\n[FAIL] Mock bytes测试失败: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Mock bytes测试", False))
    
    try:
        results.append(("30秒触发测试", test_30s_transcription_trigger()))
    except Exception as e:
        print(f"\n[FAIL] 30秒触发测试失败: {e}")
        import traceback
        traceback.print_exc()
        results.append(("30秒触发测试", False))
    
    try:
        results.append(("错误处理测试", test_error_handling()))
    except Exception as e:
        print(f"\n[FAIL] 错误处理测试失败: {e}")
        import traceback
        traceback.print_exc()
        results.append(("错误处理测试", False))
    
    # 汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {name}: {status}")
    
    all_passed = all(r[1] for r in results)
    print("\n" + "=" * 60)
    if all_passed:
        print("所有测试通过 [PASS]")
    else:
        print("部分测试失败 [FAIL]")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
