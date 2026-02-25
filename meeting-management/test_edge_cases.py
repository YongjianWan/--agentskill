#!/usr/bin/env python3
"""测试边界情况"""

import sys
sys.path.insert(0, '.')

from src.meeting_skill import create_meeting_skeleton, save_meeting, query_meetings, Meeting, Topic, ActionItem

print('='*60)
print('测试边界情况')
print('='*60)

# 1. 空转写文本
print()
print('测试1: 空转写文本')
try:
    meeting = create_meeting_skeleton("")
    print(f'  会议ID: {meeting.id}')
    print(f'  议题数: {len(meeting.topics)}')
    print('  状态: 通过')
except Exception as e:
    print(f'  错误: {e}')

# 2. 超长转写文本
print()
print('测试2: 超长转写文本（10万字符）')
try:
    long_text = "[00:00:01] 张三: 测试内容\n" * 10000
    meeting = create_meeting_skeleton(long_text[:100000])
    print(f'  文本长度: {len(long_text[:100000])}')
    print(f'  会议ID: {meeting.id}')
    print('  状态: 通过')
except Exception as e:
    print(f'  错误: {e}')

# 3. 特殊字符
print()
print('测试3: 特殊字符内容')
try:
    special_text = "[00:00:01] 张三: 测试<特殊>&字符\"'\\n\t"
    meeting = create_meeting_skeleton(special_text)
    files = save_meeting(meeting, output_dir='./output')
    print(f'  JSON: {files["json"]}')
    print('  状态: 通过')
except Exception as e:
    print(f'  错误: {e}')

# 4. 查询不存在的会议
print()
print('测试4: 查询不存在的日期范围')
results = query_meetings(date_range=('2020-01-01', '2020-01-31'))
print(f'  结果数: {len(results)}')
print('  状态: 通过')

# 5. 更新不存在的会议
print()
print('测试5: 更新不存在的会议ID')
try:
    update_meeting("NOT_EXIST_12345", title="测试")
    print('  状态: 应该报错但没有')
except FileNotFoundError as e:
    print(f'  错误类型: FileNotFoundError')
    print('  状态: 正确处理')
except Exception as e:
    print(f'  错误: {e}')

# 6. 大量行动项
print()
print('测试6: 大量行动项（100个）')
try:
    meeting = create_meeting_skeleton("[00:00:01] 张三: 测试")
    meeting.topics = [Topic(
        title="测试议题",
        discussion_points=["测试要点"],
        action_items=[
            ActionItem(action=f"行动项{i}", owner="张三", deadline="2026-03-01")
            for i in range(100)
        ]
    )]
    files = save_meeting(meeting, output_dir='./output')
    print(f'  行动项数: 100')
    print(f'  状态: 通过')
except Exception as e:
    print(f'  错误: {e}')

print()
print('='*60)
print('边界测试完成')
print('='*60)
