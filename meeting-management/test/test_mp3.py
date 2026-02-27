#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试MP3文件转写"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.meeting_skill import transcribe
import time

mp3_path = r'C:\Users\sdses\Desktop\神思\ai孪生\agentp平台skill\meeting-management\test\周四 10点19分.mp3'

print('开始转写MP3文件...')
print(f'文件路径: {mp3_path}')
start_time = time.time()

try:
    result = transcribe(mp3_path, model='small')
    elapsed = time.time() - start_time
    
    print(f'\n✅ 转写完成！耗时: {elapsed:.1f}秒')
    print(f'转写文本长度: {len(result["full_text"])} 字符')
    print(f'参会人: {result["participants"]}')
    print(f'音频时长: {result["duration"]} 秒')
    print()
    print('=== 转写内容预览（前800字符）===')
    print(result['full_text'][:800])
    if len(result['full_text']) > 800:
        print('...')
    
except Exception as e:
    print(f'❌ 转写失败: {e}')
    import traceback
    traceback.print_exc()
