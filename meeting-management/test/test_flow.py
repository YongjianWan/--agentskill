#!/usr/bin/env python3
"""
完整业务流程测试
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.meeting_skill import generate_minutes, save_meeting, update_meeting, query_meetings
import json

# 读取测试文本（相对于脚本位置）
test_file = Path(__file__).parent / 'test_transcription.txt'
with open(test_file, 'r', encoding='utf-8') as f:
    text = f.read()

print('='*60)
print('步骤1: 生成会议纪要')
print('='*60)

meeting = generate_minutes(
    transcription=text,
    title='Q4产品规划评审会',
    date='2024-11-01',
    time_range='09:00-09:30',
    location='会议室A',
    recorder='助理'
)

print(f'会议ID: {meeting.id}')
print(f'标题: {meeting.title}')
print(f'日期: {meeting.date}')
print(f'参会人: {meeting.participants}')
print(f'版本: v{meeting.version}')
print()

print('='*60)
print('步骤2: 议题与结论')
print('='*60)
for i, topic in enumerate(meeting.topics, 1):
    print(f'议题{i}: {topic.title}')
    print(f'  讨论要点: {len(topic.discussion_points)}条')
    conclusion = topic.conclusion or "无"
    print(f'  结论: {conclusion}')
    print(f'  不确定: {topic.uncertain}')
    print(f'  行动项: {len(topic.action_items)}个')
    for a in topic.action_items:
        action_short = a.action[:30] + "..." if len(a.action) > 30 else a.action
        print(f'    - [{a.owner}] {action_short} (截止: {a.deadline})')
    print()

print('='*60)
print('步骤3: 风险点')
print('='*60)
for risk in meeting.risks:
    risk_short = risk[:50] + "..." if len(risk) > 50 else risk
    print(f'  ! {risk_short}')

print()
print('='*60)
print('步骤4: 待确认事项')
print('='*60)
for pending in meeting.pending_confirmations:
    pending_short = pending[:50] + "..." if len(pending) > 50 else pending
    print(f'  ? {pending_short}')

print()
print('='*60)
print('步骤5: 保存会议记录')
print('='*60)
files = save_meeting(meeting, output_dir='./output')
print(f'JSON: {files["json"]}')
print(f'DOCX: {files["docx"]}')
print(f'会议目录: {files["meeting_dir"]}')

print()
print('='*60)
print('步骤6: 更新会议（创建v2）')
print('='*60)
updated = update_meeting(meeting.id, title='Q4产品规划评审会（修订版）')
print(f'已更新到 v{updated.version}')

print()
print('='*60)
print('步骤7: 查询历史会议')
print('='*60)
results = query_meetings(date_range=('2024-11-01', '2024-11-30'))
print(f'找到 {len(results)} 个会议')
for r in results[:3]:
    print(f'  - {r["date"]} {r["title"]} (v{r["version"]})')

print()
print('='*60)
print('✅ 业务流程测试完成')
print('='*60)
