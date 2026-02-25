#!/usr/bin/env python3
"""测试查询和更新接口"""

import sys
sys.path.insert(0, '.')

from src.meeting_skill import query_meetings, update_meeting

print('='*60)
print('测试 query_meetings')
print('='*60)

# 查询历史会议
results = query_meetings(date_range=('2024-11-01', '2024-11-30'))
print(f'查询到 {len(results)} 个会议')

for r in results[:5]:
    print(f"  - {r['date']} {r['title']} (v{r['version']})")

print()
print('='*60)
print('测试 update_meeting')
print('='*60)

if results:
    meeting_id = results[0]['id']
    print(f'更新会议: {meeting_id}')
    
    try:
        updated = update_meeting(meeting_id, title='测试更新后的标题')
        print(f'版本: v{updated.version}')
        print(f'新标题: {updated.title}')
        print('状态: 更新成功')
    except Exception as e:
        print(f'错误: {e}')
else:
    print('无会议可更新')

print()
print('='*60)
print('测试完成')
print('='*60)
