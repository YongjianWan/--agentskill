#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from src.meeting_skill import generate_minutes, save_meeting
import json

# 读取测试文本
with open('test_transcription.txt', 'r', encoding='utf-8') as f:
    text = f.read()

# 生成会议纪要
meeting = generate_minutes(
    transcription=text,
    title='Q4 Product Review',
    date='2024-11-01',
    time_range='09:00-09:30',
    location='Conference Room A',
    recorder='Assistant'
)

# 保存结果
with open('test_result.json', 'w', encoding='utf-8') as f:
    json.dump(meeting.to_dict(), f, ensure_ascii=False, indent=2)

# 保存会议文件
files = save_meeting(meeting, output_dir='./output')

# 输出摘要（英文避免编码问题）
summary = {
    "status": "OK",
    "meeting_id": meeting.id,
    "title": meeting.title,
    "date": meeting.date,
    "participants_count": len(meeting.participants),
    "topics_count": len(meeting.topics),
    "total_actions": sum(len(t.action_items) for t in meeting.topics),
    "risks_count": len(meeting.risks),
    "version": meeting.version,
    "files": files
}

with open('test_summary.json', 'w', encoding='utf-8') as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print("Test completed. Check test_result.json and test_summary.json")
