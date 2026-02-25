#!/usr/bin/env python3
"""
Setup script for meeting-management skill.
Installs required dependencies for local Whisper transcription.
"""

import subprocess
import sys


def run_command(cmd, description):
    """Run a shell command and handle errors."""
    print(f"\n{description}...")
    print(f"> {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Success")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed: {e}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False


def main():
    print("=" * 60)
    print("Meeting Management Skill - Setup")
    print("=" * 60)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher required")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Install faster-whisper (recommended for local CPU usage)
    print("\nInstalling Whisper backend...")
    print("Option 1: faster-whisper (faster on CPU, recommended)")
    print("Option 2: openai-whisper (original implementation)")
    
    # Try faster-whisper first
    if run_command([sys.executable, "-m", "pip", "install", "-U", "faster-whisper"], 
                   "Installing faster-whisper"):
        pass
    else:
        print("\nFalling back to openai-whisper...")
        if not run_command([sys.executable, "-m", "pip", "install", "-U", "openai-whisper"],
                          "Installing openai-whisper"):
            print("\n❌ Failed to install Whisper backend")
            sys.exit(1)
    
    # Install other dependencies
    print("\nInstalling other dependencies...")
    run_command([sys.executable, "-m", "pip", "install", "python-docx"], 
                "Installing python-docx")
    
    print("\n" + "=" * 60)
    print("Setup complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Ensure FFmpeg is installed:")
    print("   Windows: winget install Gyan.FFmpeg")
    print("   Mac: brew install ffmpeg")
    print("   Linux: sudo apt install ffmpeg")
    print("\n2. Test transcription:")
    print("   python transcribe.py your_audio.mp3")
    print("\nNote: First run will download the Whisper model (~150MB-3GB)")
    print("      Model sizes: tiny < base < small < medium < large")


if __name__ == "__main__":
    main()
