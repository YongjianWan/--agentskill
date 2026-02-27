#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify Case 3: Empty text handling"""

import requests
import sys
sys.path.insert(0, 'src')

BASE_URL = 'http://127.0.0.1:8765/api/v1'

# Create meeting
r = requests.post(f'{BASE_URL}/meetings', json={'title': 'Test', 'user_id': 'u1'})
session_id = r.json()['data']['session_id']
print(f'Meeting: {session_id}')

# Setup data
import asyncio
from database.connection import AsyncSessionLocal
from models.meeting import MeetingModel
from sqlalchemy import select

async def setup():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(MeetingModel).where(MeetingModel.session_id == session_id))
        meeting = result.scalar_one_or_none()
        meeting.transcript_segments = [
            {'id': 'seg-0001', 'text': '原始文字', 'start_time_ms': 0, 'end_time_ms': 3000, 'speaker': '张三'}
        ]
        meeting.full_text = '[00:00] 原始文字'
        await db.commit()
        print('Segment added')
asyncio.run(setup())

# Test Case 3: Empty text
r = requests.put(f'{BASE_URL}/meetings/{session_id}/transcript/seg-0001', json={'text': ''})
print(f'\nCase 3 - Status: {r.status_code}')
print(f'Case 3 - Response: {r.json()}')

# Verify segment content
r = requests.get(f'{BASE_URL}/meetings/{session_id}/transcript')
segments = r.json()['data']['segments']
print(f'Case 3 - Segment text after update: "{segments[0]["text"]}"')

if segments[0]["text"] == "":
    print("\nResult: Text was cleared (empty string)")
else:
    print(f"\nResult: Text was NOT cleared, current value: '{segments[0]['text']}'")
