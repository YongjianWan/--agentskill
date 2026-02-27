#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify Case 3: Empty text handling - detailed"""

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
            {'id': 'seg-0001', 'text': 'Original text', 'start_time_ms': 0, 'end_time_ms': 3000, 'speaker': 'Test'}
        ]
        meeting.full_text = '[00:00] Original text'
        await db.commit()
        print('Segment added with text: "Original text"')
asyncio.run(setup())

# Get initial state
r = requests.get(f'{BASE_URL}/meetings/{session_id}/transcript')
segments = r.json()['data']['segments']
print(f'Initial segment text: "{segments[0]["text"]}"')

# Test Case 3: Empty text
print('\n--- Sending PUT request with empty text ---')
r = requests.put(f'{BASE_URL}/meetings/{session_id}/transcript/seg-0001', json={'text': ''})
print(f'Response Status: {r.status_code}')
print(f'Response Body: {r.json()}')

# Verify segment content after update
r = requests.get(f'{BASE_URL}/meetings/{session_id}/transcript')
segments = r.json()['data']['segments']
print(f"\nSegment text after update: '{segments[0]['text']}'")

# Also check full_text
full_text = r.json()['data']['full_text']
print(f"Full text after update: '{full_text}'")

# Determine actual result
if segments[0]["text"] == "":
    print("\n[PASS] Text was successfully cleared")
else:
    print(f"\n[ISSUE] Text was NOT cleared, still: '{segments[0]['text']}'")
    print("Note: API returns 200 but doesn't actually update to empty string")
