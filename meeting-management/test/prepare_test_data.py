# -*- coding: utf-8 -*-
"""准备测试数据 - 更新会议docx路径"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from database.connection import init_db, AsyncSessionLocal
from models.meeting import MeetingModel
from sqlalchemy import select

async def main():
    await init_db()
    
    async with AsyncSessionLocal() as session:
        # 查找TEST_NO_DOCX_001会议
        result = await session.execute(
            select(MeetingModel).where(MeetingModel.session_id == "TEST_NO_DOCX_001")
        )
        meeting = result.scalar_one_or_none()
        
        if meeting:
            # 更新docx路径为存在的文件
            meeting.minutes_docx_path = "output/meetings/2024/11/M20241101_102123_23924e/minutes_latest.docx"
            await session.commit()
            print(f"已更新 TEST_NO_DOCX_001 的docx路径")
            print(f"  新路径: {meeting.minutes_docx_path}")
            print(f"  文件存在: {os.path.exists(meeting.minutes_docx_path)}")
        else:
            print("会议 TEST_NO_DOCX_001 不存在")
            
        # 列出所有completed会议
        result = await session.execute(
            select(MeetingModel).where(MeetingModel.status == 'completed')
        )
        meetings = result.scalars().all()
        print(f"\n共有 {len(meetings)} 个completed会议:")
        for m in meetings:
            print(f"  - {m.session_id}: docx={m.minutes_docx_path}")

if __name__ == "__main__":
    asyncio.run(main())
