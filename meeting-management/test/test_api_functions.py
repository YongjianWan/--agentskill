#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 功能测试脚本
"""

import requests
import json
import time
import sys
import os
from pathlib import Path

# 加载 .env 文件
dotenv_path = Path(__file__).parent.parent / ".env"
if dotenv_path.exists():
    with open(dotenv_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key, value)

BASE_URL = "http://localhost:8765/api/v1"

def test_health():
    print("\n=== Test 1: Health Check ===")
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"Status: {resp.status_code}")
        data = resp.json()
        print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
        return resp.status_code == 200 and data.get("code") == 0
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

def test_create_meeting():
    print("\n=== Test 2: Create Meeting ===")
    try:
        data = {
            "title": "Test Meeting",
            "participants": ["Alice", "Bob"],
            "location": "Room A",
            "user_id": "test_user_001"
        }
        resp = requests.post(f"{BASE_URL}/meetings", json=data, timeout=5)
        print(f"Status: {resp.status_code}")
        result = resp.json()
        print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
        session_id = result.get("data", {}).get("session_id") if "code" in result else result.get("session_id")
        return session_id
    except Exception as e:
        print(f"[ERROR] {e}")
        return None

def test_list_meetings_with_search():
    print("\n=== Test 3: Meeting List Search ===")
    try:
        # Basic list
        resp = requests.get(f"{BASE_URL}/meetings?user_id=test_user_001", timeout=5)
        print(f"Basic list - Status: {resp.status_code}")
        
        # Date range filter
        resp = requests.get(
            f"{BASE_URL}/meetings?user_id=test_user_001&start_date=2026-02-01&end_date=2026-12-31", 
            timeout=5
        )
        print(f"Date filter - Status: {resp.status_code}")
        
        # Keyword search
        resp = requests.get(
            f"{BASE_URL}/meetings?user_id=test_user_001&keyword=Test", 
            timeout=5
        )
        print(f"Keyword search - Status: {resp.status_code}")
        result = resp.json()
        count = len(result.get('data', {}).get('list', []))
        print(f"Search results count: {count}")
        
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

def test_end_meeting_triggers_ai(session_id):
    print(f"\n=== Test 4: End Meeting Triggers AI (session_id: {session_id}) ===")
    try:
        # Start meeting first
        print("Step 1: Start meeting...")
        resp = requests.post(f"{BASE_URL}/meetings/{session_id}/start", timeout=5)
        print(f"Start - Status: {resp.status_code}")
        
        # End meeting
        print("Step 2: End meeting...")
        resp = requests.post(f"{BASE_URL}/meetings/{session_id}/end", timeout=5)
        print(f"End - Status: {resp.status_code}")
        result = resp.json()
        print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        # Check PROCESSING status (case-insensitive)
        status = result.get("data", {}).get("status") if "data" in result else None
        if status and status.lower() == "processing":
            print("[OK] Meeting status is PROCESSING, AI task started")
            return True
        else:
            print(f"[WARN] Meeting status: {status}")
            return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

def test_download_not_completed(session_id):
    print(f"\n=== Test 5: Download Not Completed (expect 409) ===")
    try:
        resp = requests.get(
            f"{BASE_URL}/meetings/{session_id}/download?format=docx", 
            timeout=5
        )
        print(f"Status: {resp.status_code}")
        if resp.status_code == 409:
            print("[OK] Correctly returned 409 - meeting not completed")
            return True
        return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

def test_download_invalid_format(session_id):
    print(f"\n=== Test 6: Download Invalid Format (expect 400) ===")
    try:
        resp = requests.get(
            f"{BASE_URL}/meetings/{session_id}/download?format=invalid", 
            timeout=5
        )
        print(f"Status: {resp.status_code}")
        if resp.status_code == 400:
            print("[OK] Correctly returned 400 - format not supported")
            return True
        return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

def test_noise_filtering():
    print("\n=== Test 7: Noise Words Filtering ===")
    try:
        noise_words = os.getenv("AI_NOISE_WORDS", "")
        print(f"AI_NOISE_WORDS: {noise_words}")
        
        # Check expected words
        expected = ["字幕by索兰娅", "字幕", "索兰娅"]
        for word in expected:
            if word in noise_words:
                print(f"[OK] Contains: {word}")
            else:
                print(f"[WARN] Missing: {word}")
        
        # Test filter function
        sys.path.insert(0, "src")
        from ai_minutes_generator import filter_noise_words
        
        test_text = "今天我们讨论项目字幕by索兰娅进度"
        filtered = filter_noise_words(test_text)
        print(f"\nInput: {test_text}")
        print(f"Output: {filtered}")
        
        if "字幕" not in filtered and "索兰娅" not in filtered:
            print("[OK] Noise filtering works")
            return True
        else:
            print("[WARN] Noise filtering may not work")
            return False
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("Meeting Management System API Test")
    print(f"Base URL: {BASE_URL}")
    print("=" * 60)
    
    results = []
    
    # Test 1: Health check
    results.append(("Health Check", test_health()))
    
    # Test 2: Create meeting
    session_id = test_create_meeting()
    results.append(("Create Meeting", session_id is not None))
    
    if session_id:
        # Test 3: Search
        results.append(("Meeting List Search", test_list_meetings_with_search()))
        
        # Test 4: End meeting triggers AI
        results.append(("End Meeting Triggers AI", test_end_meeting_triggers_ai(session_id)))
        
        # Test 5: Download not completed
        results.append(("Download Not Completed (409)", test_download_not_completed(session_id)))
        
        # Test 6: Download invalid format
        results.append(("Download Invalid Format (400)", test_download_invalid_format(session_id)))
    
    # Test 7: Noise filtering
    results.append(("Noise Filtering", test_noise_filtering()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(1 for _, r in results if r)
    total = len(results)
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{name}: {status}")
    print(f"\nTotal: {passed}/{total} passed")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
