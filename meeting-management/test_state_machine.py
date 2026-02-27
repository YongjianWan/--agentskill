# -*- coding: utf-8 -*-
"""
会议状态机流转测试 - 测试清单 1.2
"""

import requests
import json
import sys
import time
from datetime import datetime

BASE_URL = "http://localhost:8765/api/v1"


def create_meeting():
    """创建会议获取 session_id"""
    url = f"{BASE_URL}/meetings"
    data = {
        "title": "状态机测试会议",
        "user_id": "test_user",
        "participants": ["测试员"],
        "location": "测试室"
    }
    try:
        resp = requests.post(url, json=data, timeout=10)
        if resp.status_code == 200:
            result = resp.json()
            return result.get("data", {}).get("session_id")
        else:
            print(f"创建会议失败: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        print(f"创建会议异常: {e}")
        return None


def get_meeting_status(session_id):
    """获取会议状态"""
    url = f"{BASE_URL}/meetings/{session_id}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("data", {})
        return None
    except Exception as e:
        print(f"获取状态异常: {e}")
        return None


def start_meeting(session_id):
    """开始会议"""
    url = f"{BASE_URL}/meetings/{session_id}/start"
    try:
        resp = requests.post(url, timeout=10)
        return resp.status_code, resp.json() if resp.text else {}
    except Exception as e:
        return -1, {"error": str(e)}


def pause_meeting(session_id):
    """暂停会议"""
    url = f"{BASE_URL}/meetings/{session_id}/pause"
    try:
        resp = requests.post(url, timeout=10)
        return resp.status_code, resp.json() if resp.text else {}
    except Exception as e:
        return -1, {"error": str(e)}


def resume_meeting(session_id):
    """恢复会议"""
    url = f"{BASE_URL}/meetings/{session_id}/resume"
    try:
        resp = requests.post(url, timeout=10)
        return resp.status_code, resp.json() if resp.text else {}
    except Exception as e:
        return -1, {"error": str(e)}


def end_meeting(session_id):
    """结束会议"""
    url = f"{BASE_URL}/meetings/{session_id}/end"
    try:
        resp = requests.post(url, timeout=10)
        return resp.status_code, resp.json() if resp.text else {}
    except Exception as e:
        return -1, {"error": str(e)}


def run_tests():
    """执行状态机测试"""
    print("=" * 80)
    print("会议状态机流转测试 - 测试清单 1.2")
    print("=" * 80)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"服务地址: {BASE_URL}")
    print()
    
    # 步骤1: 创建会议获取 session_id
    print("[步骤1] 创建会议...")
    session_id = create_meeting()
    if not session_id:
        print("[FAIL] 创建会议失败，测试终止")
        return
    print(f"[PASS] 会议创建成功: {session_id}")
    
    # 获取初始状态
    status_data = get_meeting_status(session_id)
    if not status_data:
        print("[FAIL] 获取会议状态失败")
        return
    print(f"   当前状态: {status_data.get('status')}")
    print()
    
    # 测试结果记录
    results = []
    bugs = []
    
    # 测试用例1: created -> POST /start
    print("-" * 80)
    print("[测试1] 前置状态=created, 操作=POST /start")
    print("        期望=200, status=recording, start_time不为null")
    code, resp_data = start_meeting(session_id)
    status_data = get_meeting_status(session_id)
    actual_status = status_data.get('status') if status_data else None
    start_time = status_data.get('start_time') if status_data else None
    
    passed = (code == 200 and actual_status == "recording" and start_time is not None)
    results.append({
        "id": 1,
        "前置状态": "created",
        "操作": "POST /start",
        "期望": "200, status=recording, start_time不为null",
        "实际结果": f"{code}, status={actual_status}, start_time={start_time is not None}",
        "通过": "PASS" if passed else "FAIL"
    })
    print(f"实际: HTTP {code}, status={actual_status}, start_time={start_time is not None}")
    print(f"结果: {'PASS' if passed else 'FAIL'}")
    if not passed:
        bugs.append(f"测试1失败: created状态start操作返回{code}，期望200")
    print()
    
    # 测试用例2: created + POST /pause -> 400
    print("-" * 80)
    print("[测试2] 前置状态=created, 操作=POST /pause")
    print("        期望=400, detail含'未在录音状态'")
    print("   (创建新会议用于测试)")
    session_id_2 = create_meeting()
    if not session_id_2:
        print("[FAIL] 创建会议失败")
    else:
        code, resp_data = pause_meeting(session_id_2)
        detail = resp_data.get('detail', '') if isinstance(resp_data, dict) else str(resp_data)
        
        passed = (code == 400 and ('未在录音状态' in detail or '状态' in detail))
        results.append({
            "id": 2,
            "前置状态": "created",
            "操作": "POST /pause",
            "期望": "400, detail含'未在录音状态'",
            "实际结果": f"{code}, detail={detail}",
            "通过": "PASS" if passed else "FAIL"
        })
        print(f"实际: HTTP {code}, detail={detail}")
        print(f"结果: {'PASS' if passed else 'FAIL'}")
        if not passed:
            bugs.append(f"测试2失败: created状态pause操作返回{code}，期望400，detail={detail}")
    print()
    
    # 测试用例3: recording + POST /start -> 400
    print("-" * 80)
    print("[测试3] 前置状态=recording, 操作=POST /start")
    print("        期望=400, detail含'状态错误'")
    code, resp_data = start_meeting(session_id)
    detail = resp_data.get('detail', '') if isinstance(resp_data, dict) else str(resp_data)
    
    passed = (code == 400 and '状态' in detail)
    results.append({
        "id": 3,
        "前置状态": "recording",
        "操作": "POST /start",
        "期望": "400, detail含'状态错误'",
        "实际结果": f"{code}, detail={detail}",
        "通过": "PASS" if passed else "FAIL"
    })
    print(f"实际: HTTP {code}, detail={detail}")
    print(f"结果: {'PASS' if passed else 'FAIL'}")
    if not passed:
        bugs.append(f"测试3失败: recording状态start操作返回{code}，期望400，detail={detail}")
    print()
    
    # 测试用例4: recording + POST /pause -> 200, status=paused
    print("-" * 80)
    print("[测试4] 前置状态=recording, 操作=POST /pause")
    print("        期望=200, status=paused")
    code, resp_data = pause_meeting(session_id)
    status_data = get_meeting_status(session_id)
    actual_status = status_data.get('status') if status_data else None
    
    passed = (code == 200 and actual_status == "paused")
    results.append({
        "id": 4,
        "前置状态": "recording",
        "操作": "POST /pause",
        "期望": "200, status=paused",
        "实际结果": f"{code}, status={actual_status}",
        "通过": "PASS" if passed else "FAIL"
    })
    print(f"实际: HTTP {code}, status={actual_status}")
    print(f"结果: {'PASS' if passed else 'FAIL'}")
    if not passed:
        bugs.append(f"测试4失败: recording状态pause操作返回{code}，status={actual_status}")
    print()
    
    # 测试用例5: paused + POST /resume -> 200, status=recording
    print("-" * 80)
    print("[测试5] 前置状态=paused, 操作=POST /resume")
    print("        期望=200, status=recording")
    code, resp_data = resume_meeting(session_id)
    status_data = get_meeting_status(session_id)
    actual_status = status_data.get('status') if status_data else None
    
    passed = (code == 200 and actual_status == "recording")
    results.append({
        "id": 5,
        "前置状态": "paused",
        "操作": "POST /resume",
        "期望": "200, status=recording",
        "实际结果": f"{code}, status={actual_status}",
        "通过": "PASS" if passed else "FAIL"
    })
    print(f"实际: HTTP {code}, status={actual_status}")
    print(f"结果: {'PASS' if passed else 'FAIL'}")
    if not passed:
        bugs.append(f"测试5失败: paused状态resume操作返回{code}，status={actual_status}")
    print()
    
    # 重新暂停，用于测试用例6
    print("   (重新暂停会议用于测试)")
    pause_meeting(session_id)
    
    # 测试用例6: paused + POST /end -> 200, status=processing
    print("-" * 80)
    print("[测试6] 前置状态=paused, 操作=POST /end")
    print("        期望=200, status=processing")
    code, resp_data = end_meeting(session_id)
    status_data = get_meeting_status(session_id)
    actual_status = status_data.get('status') if status_data else None
    
    passed = (code == 200 and actual_status == "processing")
    results.append({
        "id": 6,
        "前置状态": "paused",
        "操作": "POST /end",
        "期望": "200, status=processing",
        "实际结果": f"{code}, status={actual_status}",
        "通过": "PASS" if passed else "FAIL"
    })
    print(f"实际: HTTP {code}, status={actual_status}")
    print(f"结果: {'PASS' if passed else 'FAIL'}")
    if not passed:
        bugs.append(f"测试6失败: paused状态end操作返回{code}，status={actual_status}")
    print()
    
    # 等待处理完成（简单轮询，最多30秒）
    print("[等待] 会议处理中，等待完成...")
    for i in range(30):
        time.sleep(1)
        status_data = get_meeting_status(session_id)
        if status_data and status_data.get('status') in ['completed', 'failed']:
            print(f"   处理完成: {status_data.get('status')}")
            break
    
    # 测试用例7: completed + POST /end -> 400
    print("-" * 80)
    print("[测试7] 前置状态=completed, 操作=POST /end")
    print("        期望=400, 不能重复结束")
    code, resp_data = end_meeting(session_id)
    detail = resp_data.get('detail', '') if isinstance(resp_data, dict) else str(resp_data)
    
    passed = (code == 400)
    results.append({
        "id": 7,
        "前置状态": "completed",
        "操作": "POST /end",
        "期望": "400, 不能重复结束",
        "实际结果": f"{code}, detail={detail}",
        "通过": "PASS" if passed else "FAIL"
    })
    print(f"实际: HTTP {code}, detail={detail}")
    print(f"结果: {'PASS' if passed else 'FAIL'}")
    if not passed:
        bugs.append(f"测试7失败: completed状态end操作返回{code}，期望400")
    print()
    
    # 测试用例8: 不存在的session_id + POST /start -> 404
    print("-" * 80)
    print("[测试8] 前置状态=不存在, 操作=POST /start")
    print("        期望=404")
    fake_session_id = "M99999999_999999_xxxxxx"
    code, resp_data = start_meeting(fake_session_id)
    detail = resp_data.get('detail', '') if isinstance(resp_data, dict) else str(resp_data)
    
    passed = (code == 404)
    results.append({
        "id": 8,
        "前置状态": "不存在",
        "操作": "POST /start",
        "期望": "404",
        "实际结果": f"{code}, detail={detail}",
        "通过": "PASS" if passed else "FAIL"
    })
    print(f"实际: HTTP {code}, detail={detail}")
    print(f"结果: {'PASS' if passed else 'FAIL'}")
    if not passed:
        bugs.append(f"测试8失败: 不存在session_id返回{code}，期望404")
    print()
    
    # 打印测试报告
    print()
    print("=" * 80)
    print("测试报告摘要")
    print("=" * 80)
    print(f"\n{'ID':<5}{'前置状态':<12}{'操作':<18}{'结果':<6}")
    print("-" * 80)
    for r in results:
        print(f"{r['id']:<5}{r['前置状态']:<12}{r['操作']:<18}{r['通过']:<6}")
    
    print()
    print("=" * 80)
    print("详细结果")
    print("=" * 80)
    for r in results:
        print(f"\n测试 {r['id']}: 前置状态={r['前置状态']}, 操作={r['操作']}")
        print(f"  期望: {r['期望']}")
        print(f"  实际: {r['实际结果']}")
        print(f"  判定: {r['通过']}")
    
    print()
    print("=" * 80)
    print("发现的Bug")
    print("=" * 80)
    if bugs:
        for i, bug in enumerate(bugs, 1):
            print(f"{i}. {bug}")
    else:
        print("[OK] 未发现Bug")
    
    print()
    print("=" * 80)
    passed_count = sum(1 for r in results if r['通过'] == "PASS")
    failed_count = len(results) - passed_count
    print(f"总计: {passed_count} 通过, {failed_count} 失败, 共 {len(results)} 个测试")
    print("=" * 80)


if __name__ == "__main__":
    run_tests()
