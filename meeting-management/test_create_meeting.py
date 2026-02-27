#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 POST /api/v1/meetings 创建会议API
测试清单 1.1
"""

import requests
import re
import json
import os
from datetime import datetime

# 设置环境变量避免编码问题
os.environ['PYTHONIOENCODING'] = 'utf-8'

BASE_URL = "http://localhost:8765"
API_ENDPOINT = "/api/v1/meetings"

def log_test(case_num, description, expected_http, expected_result, response, actual_result, passed):
    """记录测试结果"""
    status = "[PASS]" if passed else "[FAIL]"
    print(f"\n{'='*60}")
    print(f"Test Case {case_num}: {description}")
    print(f"{'='*60}")
    print(f"Expected HTTP: {expected_http}")
    print(f"Actual HTTP: {response.status_code if hasattr(response, 'status_code') else 'N/A'}")
    print(f"Expected Result: {expected_result}")
    print(f"Actual Result: {actual_result}")
    print(f"Result: {status}")
    if hasattr(response, 'text') and response.text:
        try:
            body = response.json()
            print(f"Response Body: {json.dumps(body, ensure_ascii=False, indent=2)}")
        except:
            print(f"Response Body: {response.text[:500]}")
    return passed

def test_case_1():
    """测试用例1: 正常创建会议"""
    print("\n" + "="*60)
    print("Executing Test Case 1...")
    
    payload = {
        "title": "周一例会",
        "user_id": "u001"
    }
    
    try:
        response = requests.post(f"{BASE_URL}{API_ENDPOINT}", json=payload, timeout=10)
        
        # 验证HTTP状态码
        http_ok = response.status_code == 200
        
        # 验证响应内容
        result_ok = False
        session_id = None
        if response.status_code == 200:
            try:
                data = response.json()
                session_id = data.get("session_id")
                # 验证session_id格式: M\d{8}_\d{6}_[a-f0-9]{6}
                pattern = r"^M\d{8}_\d{6}_[a-f0-9]{6}$"
                if session_id and re.match(pattern, session_id):
                    result_ok = True
            except:
                pass
        
        actual = f"HTTP {response.status_code}, session_id={session_id}"
        passed = http_ok and result_ok
        
        return log_test(
            1, 
            "Normal meeting creation: title='周一例会', user_id='u001'",
            "200",
            "session_id starts with M, format M\\d{8}_\\d{6}_[a-f0-9]{6}",
            response,
            actual,
            passed
        )
    except Exception as e:
        print(f"[ERROR] Test case 1 exception: {e}")
        return False

def test_case_2():
    """测试用例2: 空title"""
    print("\n" + "="*60)
    print("Executing Test Case 2...")
    
    payload = {
        "title": "",
        "user_id": "u001"
    }
    
    try:
        response = requests.post(f"{BASE_URL}{API_ENDPOINT}", json=payload, timeout=10)
        
        http_ok = response.status_code == 422
        
        # 验证是否有验证错误信息
        has_error = False
        if response.status_code == 422:
            has_error = True
        
        actual = f"HTTP {response.status_code}"
        passed = http_ok and has_error
        
        return log_test(
            2,
            "Empty title validation: title=''",
            "422",
            "Validation error",
            response,
            actual,
            passed
        )
    except Exception as e:
        print(f"[ERROR] Test case 2 exception: {e}")
        return False

def test_case_3():
    """测试用例3: title超过200字符"""
    print("\n" + "="*60)
    print("Executing Test Case 3...")
    
    payload = {
        "title": "a" * 201,
        "user_id": "u001"
    }
    
    try:
        response = requests.post(f"{BASE_URL}{API_ENDPOINT}", json=payload, timeout=10)
        
        http_ok = response.status_code == 422
        
        # 验证是否有长度错误信息
        has_error = False
        if response.status_code == 422:
            has_error = True
        
        actual = f"HTTP {response.status_code}"
        passed = http_ok and has_error
        
        return log_test(
            3,
            "Title length exceeds limit: title='a'*201",
            "422",
            "Exceeds 200 characters",
            response,
            actual,
            passed
        )
    except Exception as e:
        print(f"[ERROR] Test case 3 exception: {e}")
        return False

def test_case_4():
    """测试用例4: 省略user_id"""
    print("\n" + "="*60)
    print("Executing Test Case 4...")
    
    payload = {
        "title": "周一例会"
        # 省略 user_id
    }
    
    try:
        response = requests.post(f"{BASE_URL}{API_ENDPOINT}", json=payload, timeout=10)
        
        http_ok = response.status_code == 422
        
        # 验证是否有必填错误信息
        has_error = False
        if response.status_code == 422:
            has_error = True
        
        actual = f"HTTP {response.status_code}"
        passed = http_ok and has_error
        
        return log_test(
            4,
            "Missing user_id validation",
            "422",
            "user_id is required",
            response,
            actual,
            passed
        )
    except Exception as e:
        print(f"[ERROR] Test case 4 exception: {e}")
        return False

def test_case_5():
    """测试用例5: 只传title，不传user_id"""
    print("\n" + "="*60)
    print("Executing Test Case 5...")
    
    try:
        response = requests.post(
            f"{BASE_URL}{API_ENDPOINT}", 
            json={"title": "测试会议"},  # 不传user_id
            timeout=10
        )
        
        http_ok = response.status_code == 422
        
        # 验证是否有必填错误信息
        has_error = False
        if response.status_code == 422:
            has_error = True
        
        actual = f"HTTP {response.status_code}"
        passed = http_ok and has_error
        
        return log_test(
            5,
            "Only title, no user_id",
            "422",
            "Validation error (user_id required)",
            response,
            actual,
            passed
        )
    except Exception as e:
        print(f"[ERROR] Test case 5 exception: {e}")
        return False

def main():
    """主函数"""
    print("="*60)
    print("Meeting Creation API Test - Checklist 1.1")
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target: {BASE_URL}{API_ENDPOINT}")
    print("="*60)
    
    results = []
    
    # 执行所有测试用例
    results.append(("Case1", test_case_1()))
    results.append(("Case2", test_case_2()))
    results.append(("Case3", test_case_3()))
    results.append(("Case4", test_case_4()))
    results.append(("Case5", test_case_5()))
    
    # 汇总结果
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    passed_count = sum(1 for _, r in results if r)
    total_count = len(results)
    
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{name}: {status}")
    
    print(f"\nTotal: {passed_count}/{total_count} passed")
    
    # 发现的bug
    print("\n" + "="*60)
    print("Bug Summary")
    print("="*60)
    
    bugs = []
    for name, passed in results:
        if not passed:
            if name == "Case1":
                bugs.append("- Case1: Normal meeting creation failed, session_id format incorrect or missing")
            elif name == "Case2":
                bugs.append("- Case2: Empty title did not return 422 validation error")
            elif name == "Case3":
                bugs.append("- Case3: Title exceeding 200 chars did not return 422 validation error")
            elif name == "Case4":
                bugs.append("- Case4: Missing user_id did not return 422 validation error")
            elif name == "Case5":
                bugs.append("- Case5: Missing user_id did not return 422 validation error")
    
    if bugs:
        for bug in bugs:
            print(bug)
    else:
        print("No bugs found")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
