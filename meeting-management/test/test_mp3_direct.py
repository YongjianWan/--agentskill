#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""直接转写MP3文件并生成纪要 - 用于测试"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from meeting_skill import transcribe, generate_minutes, save_meeting
from datetime import datetime
from pathlib import Path
import time

mp3_path = r'C:\Users\sdses\Desktop\神思\ai孪生\agentp平台skill\meeting-management\test\周四 10点19分.mp3'
output_dir = r'C:\Users\sdses\Desktop\神思\ai孪生\agentp平台skill\meeting-management\output\meetings\2026\02'

print('=' * 60)
print('🎵 MP3 文件转写测试')
print('=' * 60)
print(f'📁 文件: 周四 10点19分.mp3')
print(f'📊 大小: {os.path.getsize(mp3_path) / 1024 / 1024:.2f} MB')
print()

# Step 1: 转写
print('⏳ Step 1/3: 正在转写音频...')
print('   (这可能需要 2-5 分钟，取决于音频长度和硬件性能)')
start_time = time.time()

try:
    result = transcribe(mp3_path, model='small')
    elapsed = time.time() - start_time
    
    print(f'✅ 转写完成！耗时: {elapsed:.1f}秒')
    print(f'   - 文本长度: {len(result["full_text"])} 字符')
    print(f'   - 参会人: {result["participants"]}')
    print(f'   - 音频时长: {result["duration"]} 秒')
    print()
    
    # 显示转写内容预览
    print('📝 转写内容预览:')
    print('-' * 60)
    preview = result['full_text'][:1000]
    print(preview)
    if len(result['full_text']) > 1000:
        print(f'... (还有 {len(result["full_text"]) - 1000} 字符)')
    print('-' * 60)
    print()
    
    # Step 2: 生成会议纪要
    print('⏳ Step 2/3: 正在生成会议纪要...')
    meeting = generate_minutes(
        transcription=result['full_text'],
        title='周四会议录音',
        date=datetime.now().strftime('%Y-%m-%d'),
        participants=result['participants'],
        audio_path=mp3_path
    )
    
    print(f'✅ 纪要生成完成！')
    print(f'   - 议题数: {len(meeting.topics)}')
    print(f'   - 行动项数: {sum(len(t.action_items) for t in meeting.topics)}')
    print()
    
    # Step 3: 保存文件
    print('⏳ Step 3/3: 正在保存会议纪要...')
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    files = save_meeting(meeting, output_dir=output_dir)
    
    print(f'✅ 保存完成！')
    print(f'   - DOCX: {files.get("docx", "N/A")}')
    print(f'   - JSON: {files.get("json", "N/A")}')
    print()
    
    print('=' * 60)
    print('🎉 全部完成！')
    print('=' * 60)
    
except Exception as e:
    print(f'❌ 错误: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
