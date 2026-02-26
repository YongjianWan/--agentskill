#!/usr/bin/env python3
"""调试转写问题"""

import sys
sys.path.insert(0, '../src')

import subprocess
import tempfile
from pathlib import Path

print("=== 测试1: transcribe_bytes 读取 WebM ===")
with open('test_audio.webm', 'rb') as f:
    webm_data = f.read()
print(f"WebM size: {len(webm_data)} bytes")

from meeting_skill import transcribe_bytes
result = transcribe_bytes(webm_data[:500000])  # 只读前500KB
print(f"Transcribed length: {len(result['full_text'])}")
print(f"First 100 chars: {result['full_text'][:100]}")

print("\n=== 测试2: ffmpeg 转 WAV 后再转写 ===")
with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
    wav_path = f.name

cmd = ['ffmpeg', '-i', 'test_audio.webm', '-ar', '16000', '-ac', '1', '-c:a', 'pcm_s16le', '-y', wav_path]
result = subprocess.run(cmd, capture_output=True)

if result.returncode == 0:
    from faster_whisper import WhisperModel
    model = WhisperModel("small", device="cpu", compute_type="int8")
    segments, info = model.transcribe(wav_path, beam_size=5, language="zh")
    
    full_text = " ".join([seg.text.strip() for seg in segments])
    print(f"Direct Whisper length: {len(full_text)}")
    print(f"First 200 chars: {full_text[:200]}")
else:
    print(f"ffmpeg failed: {result.stderr.decode()[:200]}")

Path(wav_path).unlink(missing_ok=True)
