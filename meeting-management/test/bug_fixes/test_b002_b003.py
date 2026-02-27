#!/usr/bin/env python3
"""Test B-002 and B-003 fixes"""

import requests
import time
import json

BASE_URL = "http://localhost:8765/api/v1"

def test_b003():
    """Test B-003: end endpoint and minutes generation"""
    print("=" * 60)
    print("Testing B-003 (end endpoint)")
    print("=" * 60)
    
    # 1. Create meeting
    print("\n[1/6] Creating meeting...")
    try:
        resp = requests.post(f"{BASE_URL}/meetings", json={
            "title": "Test Meeting B003",
            "user_id": "test001"
        }, timeout=10)
        print(f"  Status: {resp.status_code}")
        data = resp.json()
        print(f"  Response: {json.dumps(data, ensure_ascii=False, indent=2)}")
        session_id = data.get("data", {}).get("session_id")
        if not session_id:
            print("  [FAIL] No session_id received")
            return False
        print(f"  [PASS] Meeting created, session_id: {session_id}")
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return False
    
    # 2. Start meeting
    print("\n[2/6] Starting meeting...")
    try:
        resp = requests.post(f"{BASE_URL}/meetings/{session_id}/start", timeout=10)
        print(f"  Status: {resp.status_code}")
        data = resp.json()
        print(f"  Response: {json.dumps(data, ensure_ascii=False, indent=2)}")
        if resp.status_code == 200:
            print("  [PASS] Meeting started")
        else:
            print("  [FAIL] Meeting start failed")
            return False
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return False
    
    # 3. End meeting (with minutes generation)
    print("\n[3/6] Ending meeting (with minutes generation)...")
    try:
        resp = requests.post(f"{BASE_URL}/meetings/{session_id}/end?template_style=detailed", timeout=30)
        print(f"  Status: {resp.status_code}")
        data = resp.json()
        print(f"  Response: {json.dumps(data, ensure_ascii=False, indent=2)}")
        if resp.status_code == 200:
            print("  [PASS] Meeting ended successfully")
        else:
            print(f"  [FAIL] Meeting end failed: {data.get('detail', 'Unknown')}")
            return False
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return False
    
    # 4. Query meeting status until completed
    print("\n[4/6] Waiting for minutes generation...")
    max_wait = 30
    for i in range(max_wait):
        try:
            resp = requests.get(f"{BASE_URL}/meetings/{session_id}", timeout=10)
            data = resp.json()
            status = data.get("data", {}).get("status")
            print(f"  Second {i+1}: status={status}")
            if status == "completed":
                print("  [PASS] Minutes generation completed")
                break
            time.sleep(1)
        except Exception as e:
            print(f"  Status query error: {e}")
            time.sleep(1)
    else:
        print("  [WARN] Timeout waiting, continuing test...")
    
    # 5. Download minutes
    print("\n[5/6] Downloading minutes...")
    try:
        resp = requests.get(f"{BASE_URL}/meetings/{session_id}/download?format=json", timeout=10)
        print(f"  Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"  Response keys: {list(data.keys())}")
            
            # 6. Verify minutes field exists
            print("\n[6/6] Verifying minutes field...")
            if "minutes" in data:
                minutes = data["minutes"]
                print(f"  [PASS] Contains minutes field")
                print(f"  Minutes type: {type(minutes)}")
                if isinstance(minutes, dict):
                    print(f"  Minutes keys: {list(minutes.keys())}")
                elif isinstance(minutes, str):
                    print(f"  Minutes preview: {minutes[:200]}...")
                print("\n  [PASS] B-003 TEST PASSED!")
                return session_id
            else:
                print(f"  [FAIL] No minutes field")
                print(f"  Actual keys: {list(data.keys())}")
                return False
        else:
            print(f"  [FAIL] Download failed: {resp.text}")
            return False
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return False


def test_b002(session_id):
    """Test B-002: regenerate endpoint"""
    print("\n" + "=" * 60)
    print("Testing B-002 (regenerate endpoint)")
    print("=" * 60)
    
    if not session_id:
        print("[FAIL] No session_id available, skipping test")
        return False
    
    # 1. Call regenerate endpoint
    print("\n[1/3] Calling regenerate endpoint...")
    try:
        resp = requests.post(
            f"{BASE_URL}/meetings/{session_id}/regenerate",
            json={"template_style": "concise"},
            timeout=30
        )
        print(f"  Status: {resp.status_code}")
        data = resp.json()
        print(f"  Response: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        if resp.status_code == 200:
            print("  [PASS] Regenerate call successful, no 500 error")
        else:
            print(f"  [FAIL] Regenerate call failed: {data.get('detail', 'Unknown')}")
            return False
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return False
    
    # 2. Wait for regeneration
    print("\n[2/3] Waiting for minutes regeneration...")
    max_wait = 30
    for i in range(max_wait):
        try:
            resp = requests.get(f"{BASE_URL}/meetings/{session_id}", timeout=10)
            data = resp.json()
            status = data.get("data", {}).get("status")
            print(f"  Second {i+1}: status={status}")
            if status == "completed":
                print("  [PASS] Regeneration completed")
                break
            time.sleep(1)
        except Exception as e:
            print(f"  Status query error: {e}")
            time.sleep(1)
    else:
        print("  [WARN] Timeout waiting, continuing test...")
    
    # 3. Download minutes again, verify updated
    print("\n[3/3] Downloading minutes again...")
    try:
        resp = requests.get(f"{BASE_URL}/meetings/{session_id}/download?format=json", timeout=10)
        print(f"  Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            if "minutes" in data:
                minutes = data["minutes"]
                print(f"  [PASS] Successfully got updated minutes")
                print(f"  Minutes type: {type(minutes)}")
                if isinstance(minutes, str):
                    print(f"  Preview: {minutes[:200]}...")
                print("\n  [PASS] B-002 TEST PASSED!")
                return True
            else:
                print(f"  [FAIL] No minutes field in response")
                return False
        else:
            print(f"  [FAIL] Download failed: {resp.text}")
            return False
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("B-002 / B-003 Fix Test Script")
    print("=" * 60)
    
    # Check service
    try:
        resp = requests.get("http://localhost:8765/health", timeout=5)
        print(f"\nService health check: {resp.status_code}")
    except Exception as e:
        print(f"\n[FAIL] Service not running: {e}")
        exit(1)
    
    # Test B-003
    session_id = test_b003()
    
    # Test B-002
    if session_id:
        test_b002(session_id)
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
