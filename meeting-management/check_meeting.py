import asyncio
import sys
sys.path.insert(0, 'src')

from database.connection import AsyncSessionLocal
from models.meeting import MeetingModel
from sqlalchemy import select

async def check_meeting():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(MeetingModel).where(MeetingModel.session_id == 'TEST_REGENERATE_001'))
        meeting = result.scalar_one_or_none()
        if meeting:
            print(f'session_id: {meeting.session_id}')
            print(f'status: {meeting.status}')
            print(f'full_text exists: {meeting.full_text is not None}')
            print(f'full_text length: {len(meeting.full_text) if meeting.full_text else 0}')
            if meeting.full_text:
                print(f'full_text preview: {meeting.full_text[:100]}')
            print(f'topics: {meeting.topics}')
            print(f'minutes_history: {meeting.minutes_history}')
        else:
            print('Meeting not found')

asyncio.run(check_meeting())
