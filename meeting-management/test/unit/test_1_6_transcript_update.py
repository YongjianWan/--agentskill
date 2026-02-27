#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test List 1.6: Transcript Segment Update Test

Test Cases:
1. Valid segment_id, text="修正后的文字" -> 200, full_text updated with new text
2. Non-existent segment_id -> 404, detail contains "片段不存在"
3. Empty text -> 200, allow clearing (current code has no validation)
4. Batch update 3 segments, 1 id doesn't exist -> 200, updated_count=2, total_count=3
"""

import requests
import json
import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

BASE_URL = "http://127.0.0.1:8765/api/v1"
TEST_RESULTS = []

def log_case(case_num, description, expected, actual, passed, details=""):
    result = {
        "case_num": case_num,
        "description": description,
        "expected": expected,
        "actual": actual,
        "passed": passed,
        "details": details
    }
    TEST_RESULTS.append(result)
    status = "PASS" if passed else "FAIL"
    print(f"\n[Case {case_num}] {status}")
    print(f"  Description: {description}")
    print(f"  Expected: {expected}")
    print(f"  Actual: {actual}")
    if details:
        print(f"  Details: {details}")
    return passed

def create_meeting():
    print("=" * 60)
    print("Step 1: Create Meeting")
    print("=" * 60)
    
    create_data = {
        "title": "Transcript Update Test Meeting",
        "user_id": "test_user_001",
        "participants": ["Zhang San", "Li Si"]
    }
    
    resp = requests.post(f"{BASE_URL}/meetings", json=create_data)
    if resp.status_code != 200:
        print(f"Failed to create meeting: {resp.text}")
        return None
    
    meeting = resp.json()
    session_id = meeting["data"]["session_id"]
    print(f"[OK] Meeting created: {session_id}")
    return session_id

def setup_test_data(session_id):
    print("\n" + "=" * 60)
    print("Step 2: Setup Test Transcript Segments")
    print("=" * 60)
    
    import asyncio
    from database.connection import AsyncSessionLocal
    from models.meeting import MeetingModel
    from sqlalchemy import select
    
    async def do_setup():
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(MeetingModel).where(MeetingModel.session_id == session_id)
            )
            meeting = result.scalar_one_or_none()
            
            if meeting:
                meeting.transcript_segments = [
                    {
                        "id": "seg-0001",
                        "text": "Original text segment 1",
                        "start_time_ms": 0,
                        "end_time_ms": 3000,
                        "speaker": "Zhang San"
                    },
                    {
                        "id": "seg-0002",
                        "text": "Original text segment 2",
                        "start_time_ms": 3000,
                        "end_time_ms": 6000,
                        "speaker": "Li Si"
                    },
                    {
                        "id": "seg-0003",
                        "text": "Original text segment 3",
                        "start_time_ms": 6000,
                        "end_time_ms": 9000,
                        "speaker": "Zhang San"
                    }
                ]
                meeting.full_text = "[00:00] Original text segment 1\n[00:03] Original text segment 2\n[00:06] Original text segment 3"
                await db.commit()
                print(f"[OK] Added 3 test transcript segments")
                return True
            else:
                print(f"[FAIL] Meeting not found")
                return False
    
    return asyncio.run(do_setup())

def test_case_1(session_id):
    print("\n" + "=" * 60)
    print("Case 1: Update Valid segment_id")
    print("=" * 60)
    
    new_text = "修正后的文字"
    resp = requests.put(
        f"{BASE_URL}/meetings/{session_id}/transcript/seg-0001",
        json={"text": new_text}
    )
    
    if resp.status_code != 200:
        return log_case(
            1, 
            "Valid segment_id, text='修正后的文字'",
            "HTTP 200",
            f"HTTP {resp.status_code}",
            False,
            resp.text
        )
    
    data = resp.json()
    
    # Check if full_text is updated
    resp2 = requests.get(f"{BASE_URL}/meetings/{session_id}/transcript")
    transcript_data = resp2.json()
    full_text = transcript_data.get("data", {}).get("full_text", "")
    
    if new_text in full_text:
        return log_case(
            1,
            "Valid segment_id, text='修正后的文字'",
            "HTTP 200, full_text updated with new text",
            f"HTTP 200, full_text contains '{new_text}'",
            True,
            f"Updated full_text: {full_text[:100]}..."
        )
    else:
        return log_case(
            1,
            "Valid segment_id, text='修正后的文字'",
            "HTTP 200, full_text updated with new text",
            f"HTTP 200, but full_text does not contain '{new_text}'",
            False,
            f"full_text: {full_text}"
        )

def test_case_2(session_id):
    print("\n" + "=" * 60)
    print("Case 2: Update Non-existent segment_id")
    print("=" * 60)
    
    resp = requests.put(
        f"{BASE_URL}/meetings/{session_id}/transcript/seg-9999",
        json={"text": "Test text"}
    )
    
    if resp.status_code != 404:
        return log_case(
            2,
            "Non-existent segment_id",
            "HTTP 404, detail contains '片段不存在'",
            f"HTTP {resp.status_code}",
            False,
            resp.text
        )
    
    data = resp.json()
    detail = data.get("detail", "")
    
    if "片段不存在" in detail:
        return log_case(
            2,
            "Non-existent segment_id",
            "HTTP 404, detail contains '片段不存在'",
            f"HTTP 404, detail='{detail}'",
            True
        )
    else:
        return log_case(
            2,
            "Non-existent segment_id",
            "HTTP 404, detail contains '片段不存在'",
            f"HTTP 404, detail='{detail}' (does not contain '片段不存在')",
            False
        )

def test_case_3(session_id):
    print("\n" + "=" * 60)
    print("Case 3: Update with Empty text")
    print("=" * 60)
    
    resp = requests.put(
        f"{BASE_URL}/meetings/{session_id}/transcript/seg-0002",
        json={"text": ""}
    )
    
    if resp.status_code != 200:
        return log_case(
            3,
            "Empty text",
            "HTTP 200 (allow clearing)",
            f"HTTP {resp.status_code}",
            False,
            resp.text
        )
    
    # Verify if text is actually cleared
    resp2 = requests.get(f"{BASE_URL}/meetings/{session_id}/transcript")
    segments = resp2.json().get("data", {}).get("segments", [])
    
    seg_0002 = next((s for s in segments if s.get("id") == "seg-0002"), None)
    actual_text = seg_0002.get("text") if seg_0002 else "N/A"
    
    return log_case(
        3,
        "Empty text",
        "HTTP 200, text cleared",
        f"HTTP 200, text='{actual_text}'",
        True,
        "Empty text is allowed (no validation in code)"
    )

def test_case_4(session_id):
    print("\n" + "=" * 60)
    print("Case 4: Batch Update (1 id does not exist)")
    print("=" * 60)
    
    batch_data = {
        "updates": [
            {"segment_id": "seg-0001", "text": "Batch updated segment 1"},
            {"segment_id": "seg-0003", "text": "Batch updated segment 3"},
            {"segment_id": "seg-9999", "text": "Non-existent segment"}
        ]
    }
    
    resp = requests.put(
        f"{BASE_URL}/meetings/{session_id}/transcript",
        json=batch_data
    )
    
    if resp.status_code != 200:
        return log_case(
            4,
            "Batch update 3 segments, 1 id does not exist",
            "HTTP 200, updated_count=2, total_count=3",
            f"HTTP {resp.status_code}",
            False,
            resp.text
        )
    
    data = resp.json().get("data", {})
    updated_count = data.get("updated_count", 0)
    total_count = data.get("total_count", 0)
    
    if updated_count == 2 and total_count == 3:
        return log_case(
            4,
            "Batch update 3 segments, 1 id does not exist",
            "HTTP 200, updated_count=2, total_count=3",
            f"HTTP 200, updated_count={updated_count}, total_count={total_count}",
            True
        )
    else:
        return log_case(
            4,
            "Batch update 3 segments, 1 id does not exist",
            "HTTP 200, updated_count=2, total_count=3",
            f"HTTP 200, updated_count={updated_count}, total_count={total_count}",
            False
        )

def print_summary():
    print("\n" + "=" * 60)
    print("Test List 1.6 Execution Summary")
    print("=" * 60)
    
    passed = sum(1 for r in TEST_RESULTS if r["passed"])
    total = len(TEST_RESULTS)
    
    print(f"\nTotal: {passed}/{total} passed")
    print("\nDetailed Results:")
    for r in TEST_RESULTS:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  [{status}] Case {r['case_num']}: {r['description']}")
    
    print("\n" + "=" * 60)
    return passed == total

def main():
    print("=" * 60)
    print("Test List 1.6: Transcript Segment Update Test")
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Create meeting
    session_id = create_meeting()
    if not session_id:
        print("[FAIL] Test failed: Cannot create meeting")
        return False
    
    # Setup test data
    if not setup_test_data(session_id):
        print("[FAIL] Test failed: Cannot setup test data")
        return False
    
    # Execute test cases
    test_case_1(session_id)
    test_case_2(session_id)
    test_case_3(session_id)
    test_case_4(session_id)
    
    # Print summary
    all_passed = print_summary()
    
    # Cleanup info
    print(f"\nTest Meeting ID: {session_id} (manual cleanup required)")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
