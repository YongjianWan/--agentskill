#!/usr/bin/env python3
"""将 MP3 转换为 WebM (Opus 编码) - 模拟浏览器 MediaRecorder 输出"""

import subprocess
import shutil
from pathlib import Path
import glob

# 查找 MP3 文件
mp3_files = glob.glob('*.mp3')
if not mp3_files:
    print('No MP3 files found')
    exit(1)

mp3_path = Path(mp3_files[0])
print(f'Found: {mp3_path}')

# 使用英文临时文件名避免编码问题
import tempfile
temp_dir = Path(tempfile.gettempdir())
temp_mp3 = temp_dir / 'input_audio.mp3'
output_webm = temp_dir / 'output_audio.webm'

# 复制到临时文件
import shutil
shutil.copy(mp3_path, temp_mp3)
print(f'Copied to: {temp_mp3}')

# 转换为 WebM/Opus (浏览器 MediaRecorder 默认格式)
ffmpeg_cmd = shutil.which('ffmpeg')
if not ffmpeg_cmd:
    print('ffmpeg not found')
    exit(1)

cmd = [
    ffmpeg_cmd,
    '-i', str(temp_mp3),
    '-c:a', 'libopus',    # Opus 编码 (浏览器标准)
    '-b:a', '128k',       # 比特率
    '-ar', '48000',       # 采样率 48kHz
    '-ac', '2',           # 立体声
    '-f', 'webm',         # WebM 容器
    '-y',
    str(output_webm)
]

print(f'Converting to WebM...')
result = subprocess.run(cmd, capture_output=True, text=True)

if result.returncode == 0:
    # 复制到测试目录
    final_output = Path('test_audio.webm')
    shutil.copy(output_webm, final_output)
    size_mb = final_output.stat().st_size / 1024 / 1024
    print(f'[OK] Converted: {final_output} ({size_mb:.2f} MB)')
else:
    print(f'[FAIL] Conversion failed:')
    print(result.stderr[:500])

# 清理临时文件
temp_mp3.unlink(missing_ok=True)
output_webm.unlink(missing_ok=True)
