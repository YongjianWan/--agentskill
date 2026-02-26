#!/usr/bin/env python3
"""测试 Whisper 直接读 WAV"""

from faster_whisper import WhisperModel

print("Loading Whisper model...")
model = WhisperModel("small", device="cpu", compute_type="int8")

print("Transcribing test_sample.wav...")
segments, info = model.transcribe("test_sample.wav", beam_size=5, language="zh")

full_text = " ".join([seg.text.strip() for seg in segments])
print(f"\nTranscribed length: {len(full_text)}")
print(f"Text: {full_text[:500]}")
