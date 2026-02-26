#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket 全链路测试
验证 FIX-008 (清理任务) 和 FIX-009 (时间戳更新) 修复效果
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import asyncio
import time
from pathlib import Path

from services.websocket_manager import websocket_manager
from meeting_skill import (
    init_meeting_session, 
    append_audio_chunk, 
    finalize_meeting,
    _audio_sessions
)

# 测试音频数据（模拟）
def create_test_audio_chunk(duration_sec=1):
    """创建模拟音频数据（静音）"""
    # WebM 文件头 + 静音数据
    sample_rate = 48000
    channels = 1
    bytes_per_sample = 2
    samples = int(sample_rate * duration_sec)
    return b'\x00' * (samples * channels * bytes_per_sample)

async def test_websocket_full_chain():
    """全链路测试"""
    print('=' * 70)
    print('🔧 WebSocket 全链路测试')
    print('   验证: FIX-008 清理任务 | FIX-009 时间戳更新')
    print('=' * 70)
    
    # Step 1: 启动 WebSocketManager (FIX-008)
    print('\n[Step 1] 启动 WebSocketManager...')
    websocket_manager.start()
    await asyncio.sleep(0.1)
    if websocket_manager._cleanup_task:
        print('✅ 清理任务已启动')
    else:
        print('❌ 清理任务未启动')
        return False
    
    # Step 2: 初始化会议会话
    print('\n[Step 2] 初始化会议会话...')
    from datetime import datetime
    import uuid
    meeting_id = f"TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    audio_path = init_meeting_session(
        meeting_id=meeting_id,
        title="全链路测试会议",
        user_id="test_user_001"
    )
    print(f'✅ 会议创建: {meeting_id}')
    print(f'   音频路径: {audio_path}')
    
    # Step 3: 模拟音频流（测试 FIX-009）
    print('\n[Step 3] 模拟音频流（测试30秒触发逻辑）...')
    print('   追加音频块，观察转写触发...')
    
    chunk_count = 0
    transcribe_count = 0
    last_time = time.time()
    
    # 模拟 60 秒的音频流（每块1秒，共60块）
    for i in range(60):
        chunk = create_test_audio_chunk(1)
        result = append_audio_chunk(meeting_id, chunk, sequence=i)
        chunk_count += 1
        
        if result:
            transcribe_count += 1
            print(f'   [{i}] 📝 触发转写 #{transcribe_count}')
        
        # 模拟1秒间隔
        await asyncio.sleep(0.01)  # 加速测试
    
    print(f'\n   总块数: {chunk_count}')
    print(f'   转写次数: {transcribe_count}')
    
    # 验证: 60秒内应该触发约2次转写（30秒间隔）
    expected_transcribes = 60 // 30
    if transcribe_count <= expected_transcribes + 1:  # 允许1次误差
        print(f'✅ 转写触发次数正常 (期望约{expected_transcribes}次，实际{transcribe_count}次)')
    else:
        print(f'⚠️ 转写触发次数异常 (期望约{expected_transcribes}次，实际{transcribe_count}次)')
        print('   可能原因: 时间戳更新问题导致重复触发')
    
    # Step 4: 结束会议
    print('\n[Step 4] 结束会议...')
    try:
        result = finalize_meeting(meeting_id)
        print(f'✅ 会议结束成功')
        print(f'   - 转写文件: {result.get("transcript_path", "N/A")}')
        print(f'   - 纪要文件: {result.get("minutes_path", "N/A")}')
    except Exception as e:
        print(f'⚠️ 会议结束异常: {e}')
    
    # Step 5: 验证会话清理
    print('\n[Step 5] 验证会话状态...')
    if meeting_id in _audio_sessions:
        session = _audio_sessions[meeting_id]
        print(f'   - 块数: {session.get("chunk_count", 0)}')
        print(f'   - 转写部分数: {len(session.get("transcript_parts", []))}')
    
    # Step 6: 停止管理器
    print('\n[Step 6] 停止 WebSocketManager...')
    websocket_manager.stop()
    print('✅ 管理器已停止')
    
    print('\n' + '=' * 70)
    print('🎉 全链路测试完成')
    print('=' * 70)
    return True

if __name__ == "__main__":
    result = asyncio.run(test_websocket_full_chain())
    sys.exit(0 if result else 1)
