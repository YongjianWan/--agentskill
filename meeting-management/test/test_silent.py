#!/usr/bin/env python3
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.meeting_skill import generate_minutes, save_meeting
import json

# 读取测试文本（相对于脚本位置）
test_dir = Path(__file__).parent
test_file = test_dir / 'test_transcription.txt'
with open(test_file, 'r', encoding='utf-8') as f:
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

# 保存结果（相对于脚本位置）
result_file = test_dir / 'test_result.json'
with open(result_file, 'w', encoding='utf-8') as f:
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

summary_file = test_dir / 'test_summary.json'
with open(summary_file, 'w', encoding='utf-8') as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print(f"Test completed. Check {result_file.name} and {summary_file.name}")
