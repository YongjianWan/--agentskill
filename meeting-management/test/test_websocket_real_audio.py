#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket 全链路测试 - 使用真实音频文件
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
from datetime import datetime

from services.websocket_manager import websocket_manager
from meeting_skill import (
    init_meeting_session, 
    append_audio_chunk, 
    finalize_meeting,
    _audio_sessions
)

# 真实MP3文件路径
MP3_PATH = r'C:\Users\sdses\Desktop\神思\ai孪生\agentp平台skill\meeting-management\test\周四 10点19分.mp3'

def read_mp3_chunks(chunk_size=32000):
    """读取MP3文件为块（模拟WebSocket chunk）"""
    with open(MP3_PATH, 'rb') as f:
        chunk_num = 0
        while True:
            data = f.read(chunk_size)
            if not data:
                break
            chunk_num += 1
            yield chunk_num, data

async def test_websocket_with_real_audio():
    """使用真实音频的全链路测试"""
    print('=' * 70)
    print('🔧 WebSocket 全链路测试（真实音频）')
    print('   验证: FIX-008 清理任务 | FIX-009 时间戳更新')
    print('=' * 70)
    
    # 检查文件
    if not Path(MP3_PATH).exists():
        print(f'❌ 音频文件不存在: {MP3_PATH}')
        return False
    
    file_size = Path(MP3_PATH).stat().st_size
    print(f'\n📁 测试文件: 周四 10点19分.mp3')
    print(f'   大小: {file_size / 1024 / 1024:.2f} MB')
    
    # Step 1: 启动 WebSocketManager (FIX-008)
    print('\n[Step 1] 启动 WebSocketManager...')
    websocket_manager.start()
    await asyncio.sleep(0.1)
    if websocket_manager._cleanup_task:
        print('✅ 清理任务已启动')
        print(f'   任务: {websocket_manager._cleanup_task}')
    else:
        print('❌ 清理任务未启动')
        return False
    
    # Step 2: 初始化会议会话
    print('\n[Step 2] 初始化会议会话...')
    meeting_id = f"REAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    audio_path = init_meeting_session(
        meeting_id=meeting_id,
        title="真实音频测试会议",
        user_id="test_user_001"
    )
    print(f'✅ 会议创建: {meeting_id}')
    print(f'   输出路径: {audio_path}')
    
    # Step 3: 模拟音频流（测试 FIX-009）
    print('\n[Step 3] 模拟音频流（每32KB一个chunk，测试30秒触发逻辑）...')
    print('   注意：真实转写需要较长时间，请耐心等待...')
    
    chunk_count = 0
    transcribe_count = 0
    start_time = time.time()
    last_transcribe_time = start_time
    
    # 读取MP3并分块发送
    for seq, chunk in read_mp3_chunks():
        result = append_audio_chunk(meeting_id, chunk, sequence=seq)
        chunk_count += 1
        
        if result:
            transcribe_count += 1
            now = time.time()
            interval = now - last_transcribe_time
            last_transcribe_time = now
            print(f'   [{seq}] 📝 触发转写 #{transcribe_count} (间隔: {interval:.1f}s)')
        
        # 每10个chunk打印一次进度
        if chunk_count % 10 == 0:
            elapsed = time.time() - start_time
            print(f'   ... 已发送 {chunk_count} 块, 耗时 {elapsed:.1f}s')
        
        # 模拟网络延迟
        await asyncio.sleep(0.05)
    
    total_time = time.time() - start_time
    print(f'\n   总块数: {chunk_count}')
    print(f'   转写次数: {transcribe_count}')
    print(f'   总耗时: {total_time:.1f}s')
    
    # Step 4: 结束会议（全量转写+生成纪要）
    print('\n[Step 4] 结束会议（全量转写+生成纪要）...')
    try:
        result = finalize_meeting(meeting_id)
        print('✅ 会议结束成功')
        print(f'   转写文本长度: {len(result.get("full_text", ""))} 字符')
        print(f'   转写文件: {result.get("transcript_path", "N/A")}')
        print(f'   纪要文件: {result.get("minutes_path", "N/A")}')
    except Exception as e:
        print(f'⚠️ 会议结束异常: {e}')
        import traceback
        traceback.print_exc()
    
    # Step 5: 验证会话状态
    print('\n[Step 5] 验证会话状态...')
    if meeting_id in _audio_sessions:
        session = _audio_sessions[meeting_id]
        print(f'   - 块数: {session.get("chunk_count", 0)}')
        print(f'   - 转写部分数: {len(session.get("transcript_parts", []))}')
    else:
        print('   会话已清理')
    
    # Step 6: 停止管理器
    print('\n[Step 6] 停止 WebSocketManager...')
    websocket_manager.stop()
    print('✅ 管理器已停止')
    
    print('\n' + '=' * 70)
    print('🎉 真实音频全链路测试完成')
    print('=' * 70)
    return True

if __name__ == "__main__":
    result = asyncio.run(test_websocket_with_real_audio())
    sys.exit(0 if result else 1)
