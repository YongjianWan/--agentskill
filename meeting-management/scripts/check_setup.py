#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查安装状态"""

import sys
import subprocess

# Windows 控制台 UTF-8 编码设置
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def check_ffmpeg():
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            return True, version
    except FileNotFoundError:
        pass
    return False, None

def check_python_deps():
    deps = {}
    
    try:
        import faster_whisper
        deps['faster-whisper'] = faster_whisper.__version__
    except ImportError:
        deps['faster-whisper'] = None
    
    try:
        import docx
        deps['python-docx'] = 'installed'
    except ImportError:
        deps['python-docx'] = None
    
    try:
        import av
        deps['av'] = 'installed'
    except ImportError:
        deps['av'] = None
    
    return deps

print("=" * 50)
print("Whisper 转写环境检查")
print("=" * 50)

# 检查 Python 依赖
print("\n[Python 依赖]")
deps = check_python_deps()
for name, status in deps.items():
    if status:
        print(f"  [OK] {name}: {status}")
    else:
        print(f"  [MISSING] {name}: 未安装")

# 检查 FFmpeg
print("\n[FFmpeg]")
ffmpeg_ok, ffmpeg_version = check_ffmpeg()
if ffmpeg_ok:
    print(f"  [OK] FFmpeg 已安装: {ffmpeg_version}")
else:
    print("  [MISSING] FFmpeg 未找到")
    print("    请开 VPN 后运行: winget install Gyan.FFmpeg")

# 总结
print("\n" + "=" * 50)
if ffmpeg_ok and deps['faster-whisper']:
    print("状态: 环境就绪，可以运行转写!")
    print("\n测试命令:")
    print("  python transcribe.py your_audio.mp3")
else:
    print("状态: 需要安装 FFmpeg")
    print("步骤:")
    print("  1. 开启 VPN")
    print("  2. 运行: winget install Gyan.FFmpeg")
    print("  3. 重启终端")
    print("  4. 再次运行此检查脚本")
print("=" * 50)
