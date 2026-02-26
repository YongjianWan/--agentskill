#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Transcribe audio file using Whisper and output timestamped text.

Usage:
    python transcribe.py <audio_file_path> [output_path]
    python transcribe.py <audio_file_path> --model base

Prerequisites:
    1. FFmpeg installed and in PATH
    2. One of the following Whisper backends:
       - openai-whisper: pip install openai-whisper
       - faster-whisper: pip install faster-whisper (recommended for CPU)

Output:
    Text file with format: [HH:MM:SS] transcription text
"""

import sys
import os
import warnings
import subprocess

# Windows 控制台 UTF-8 编码设置
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


def check_ffmpeg():
    """Check if ffmpeg is installed (optional for faster-whisper with av)."""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        # faster-whisper with av library can work without external ffmpeg
        try:
            import av
            return "av"  # Return special value indicating av is available
        except ImportError:
            return False


def check_whisper_backend():
    """Check which whisper backend is available."""
    try:
        import faster_whisper
        return "faster-whisper"
    except ImportError:
        pass
    
    try:
        import whisper
        return "openai-whisper"
    except ImportError:
        return None


def transcribe_with_openai_whisper(audio_path: str, model_size: str = "base") -> list:
    """Transcribe using OpenAI Whisper."""
    import whisper
    
    print(f"Loading OpenAI Whisper model: {model_size}...")
    model = whisper.load_model(model_size)
    
    print(f"Transcribing: {audio_path}")
    result = model.transcribe(audio_path, verbose=False)
    
    segments = result.get("segments", [])
    formatted_lines = []
    
    for segment in segments:
        start_time = segment["start"]
        text = segment["text"].strip()
        
        hours = int(start_time // 3600)
        minutes = int((start_time % 3600) // 60)
        seconds = int(start_time % 60)
        timestamp = f"[{hours:02d}:{minutes:02d}:{seconds:02d}]"
        
        formatted_lines.append(f"{timestamp} {text}")
    
    return formatted_lines


def transcribe_with_faster_whisper(audio_path: str, model_size: str = "base") -> list:
    """Transcribe using Faster Whisper (CPU/GPU optimized)."""
    from faster_whisper import WhisperModel
    
    print(f"Loading Faster Whisper model: {model_size}...")
    # Use CPU with int8 quantization for best compatibility
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    
    print(f"Transcribing: {audio_path}")
    segments, info = model.transcribe(audio_path, beam_size=5, language="zh")
    
    print(f"Detected language: {info.language} (probability: {info.language_probability:.2f})")
    
    formatted_lines = []
    for segment in segments:
        start_time = segment.start
        text = segment.text.strip()
        
        hours = int(start_time // 3600)
        minutes = int((start_time % 3600) // 60)
        seconds = int(start_time % 60)
        timestamp = f"[{hours:02d}:{minutes:02d}:{seconds:02d}]"
        
        formatted_lines.append(f"{timestamp} {text}")
    
    return formatted_lines


def transcribe_audio(audio_path: str, output_path: str = None, model_size: str = "base") -> str:
    """
    Transcribe audio file using available Whisper backend.
    
    Args:
        audio_path: Path to audio file (mp3, wav, m4a, flac, etc.)
        output_path: Optional output text file path
        model_size: Model size (tiny/base/small/medium/large)
        
    Returns:
        Path to output transcription file
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    # Check ffmpeg (optional for faster-whisper)
    ffmpeg_status = check_ffmpeg()
    if not ffmpeg_status:
        print("Warning: FFmpeg not found in PATH!")
        print("Note: faster-whisper can work without FFmpeg using the av library.")
        print("If you encounter issues, install FFmpeg:")
        print("  Windows: winget install Gyan.FFmpeg")
        print("  Mac: brew install ffmpeg")
        print("  Linux: sudo apt install ffmpeg")
    elif ffmpeg_status == "av":
        print("Note: Using av library for audio processing (FFmpeg not in PATH).")
    
    # Check whisper backend
    backend = check_whisper_backend()
    if not backend:
        print("Error: No Whisper backend found!")
        print("Please install one of the following:")
        print("  Option 1 (recommended for CPU): pip install faster-whisper")
        print("  Option 2: pip install -U openai-whisper")
        sys.exit(1)
    
    # Default output path
    if output_path is None:
        base_name = os.path.splitext(audio_path)[0]
        output_path = f"{base_name}_transcription.txt"
    
    # Suppress warnings
    warnings.filterwarnings("ignore")
    
    # Transcribe with available backend
    print(f"Using backend: {backend}")
    
    if backend == "faster-whisper":
        formatted_lines = transcribe_with_faster_whisper(audio_path, model_size)
    else:
        formatted_lines = transcribe_with_openai_whisper(audio_path, model_size)
    
    # Write output
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(formatted_lines))
    
    print(f"\nTranscription saved to: {output_path}")
    print(f"Total segments: {len(formatted_lines)}")
    
    return output_path


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        print("\nExamples:")
        print("  python transcribe.py meeting.mp3")
        print("  python transcribe.py meeting.mp3 output.txt")
        print("  python transcribe.py meeting.mp3 --model small")
        sys.exit(1)
    
    audio_path = sys.argv[1]
    output_path = None
    model_size = "base"
    
    # Parse arguments
    for i, arg in enumerate(sys.argv[2:], 2):
        if arg == "--model" and i + 1 < len(sys.argv):
            model_size = sys.argv[i + 1]
        elif not arg.startswith("--") and output_path is None:
            output_path = arg
    
    try:
        transcribe_audio(audio_path, output_path, model_size)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
