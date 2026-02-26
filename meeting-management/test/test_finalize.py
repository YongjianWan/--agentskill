#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import os
sys.path.insert(0, 'src')

from meeting_skill import finalize_meeting

meeting_id = 'MT1772090634887'
audio_path = f'output/meetings/2026/02/{meeting_id}/audio.webm'

print(f'Testing finalize_meeting for {meeting_id}')
print(f'Audio exists: {os.path.exists(audio_path)}')
print(f'Audio size: {os.path.getsize(audio_path) / 1024:.1f} KB' if os.path.exists(audio_path) else 'N/A')

try:
    result = finalize_meeting(meeting_id)
    print('Success!')
    print(f'Text length: {len(result.get("full_text", ""))}')
    print(f'Minutes: {result.get("minutes_path", "N/A")}')
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
