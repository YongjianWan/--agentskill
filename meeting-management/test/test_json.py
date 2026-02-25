#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from src.meeting_skill import generate_minutes, save_meeting
import json

# 读取测试文本
with open('test_transcription.txt', 'r', encoding='utf-8') as f:
    text = f.read()

print("[STEP 1] Generating meeting minutes...")
meeting = generate_minutes(
    transcription=text,
    title='Q4 Product Review',
    date='2024-11-01',
    time_range='09:00-09:30',
    location='Conference Room A',
    recorder='Assistant'
)

print(f"Meeting ID: {meeting.id}")
print(f"Title: {meeting.title}")
print(f"Date: {meeting.date}")
print(f"Participants: {meeting.participants}")
print(f"Topics: {len(meeting.topics)}")
print(f"Risks: {len(meeting.risks)}")
print(f"Pending: {len(meeting.pending_confirmations)}")
print()

print("[STEP 2] Topic details:")
for i, topic in enumerate(meeting.topics, 1):
    print(f"  Topic {i}: {topic.title[:40]}...")
    print(f"    Discussion: {len(topic.discussion_points)} points")
    print(f"    Conclusion: {topic.conclusion[:40] if topic.conclusion else 'None'}...")
    print(f"    Uncertain: {len(topic.uncertain)} items")
    print(f"    Actions: {len(topic.action_items)} items")
    for a in topic.action_items:
        print(f"      - [{a.owner}] {a.action[:30]}... (by {a.deadline})")

print()
print("[STEP 3] Saving files...")
files = save_meeting(meeting, output_dir='./output')
print(f"JSON: {files['json']}")
print(f"DOCX: {files['docx']}")

# Save readable output
with open('test_result.json', 'w', encoding='utf-8') as f:
    json.dump(meeting.to_dict(), f, ensure_ascii=False, indent=2)

print()
print("[OK] Test completed. Check test_result.json for full output.")
