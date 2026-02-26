#!/usr/bin/env python3
"""测试 ffmpeg 转码功能"""

import sys
sys.path.insert(0, '..')
sys.path.insert(0, '../src')

from meeting_skill import transcribe_bytes
from pathlib import Path
import glob

# 查找音频文件
audio_files = glob.glob('*.mp3')
if not audio_files:
    print('No mp3 files found')
    sys.exit(1)

audio_path = Path(audio_files[0])
print(f'Found audio: {audio_path}')

with open(audio_path, 'rb') as f:
    audio = f.read()

print(f'Audio size: {len(audio)} bytes')
print('Transcribing first 500KB...')

# 只转写前500KB
result = transcribe_bytes(audio[:500000])
full_text = result['full_text']
print(f'Transcribed text length: {len(full_text)}')
print(f'First 300 chars: {full_text[:300]}')
