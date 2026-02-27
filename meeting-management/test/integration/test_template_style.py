# -*- coding: utf-8 -*-
"""
测试清单 1.3: 结束会议 API 的 template_style 参数测试
"""

import requests
import json
import sys
from datetime import datetime

# 配置
BASE_URL = "http://localhost:8765"
API_PREFIX = "/api/v1"

def log(msg):
    """打印日志"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def create_meeting():
    """创建会议"""
    url = f"{BASE_URL}{API_PREFIX}/meetings"
    data = {
        "title": f"测试会议-{datetime.now().strftime('%H%M%S')}",
        "user_id": "test_user"
    }
    resp = requests.post(url, json=data)
    return resp

def start_meeting(session_id):
    """开始会议"""
    url = f"{BASE_URL}{API_PREFIX}/meetings/{session_id}/start"
    return requests.post(url)

def end_meeting(session_id, template_style=None):
    """结束会议
    
    Args:
        session_id: 会议ID
        template_style: 模板风格，None表示省略参数
    """
    url = f"{BASE_URL}{API_PREFIX}/meetings/{session_id}/end"
    params = {}
    if template_style is not None:
        params["template_style"] = template_style
    return requests.post(url, params=params)

def check_service():
    """检查服务是否运行"""
    try:
        resp = requests.get(f"{BASE_URL}{API_PREFIX}/health", timeout=5)
        return resp.status_code == 200
    except:
        return False

def run_test_case(case_num, description, template_style, expected_status, expected_detail_contains=None):
    """执行单个测试用例"""
    log(f"\n{'='*60}")
    log(f"测试用例 {case_num}: {description}")
    log(f"{'='*60}")
    
    result = {
        "case_num": case_num,
        "description": description,
        "input": f"template_style={template_style}" if template_style is not None else "省略 template_style",
        "expected": expected_status,
        "actual": None,
        "response": None,
        "status": "FAIL"
    }
    
    # 步骤1: 创建会议
    log("步骤1: 创建会议...")
    resp = create_meeting()
    if resp.status_code != 200:
        log(f"[FAIL] 创建会议失败: {resp.status_code} - {resp.text}")
        result["response"] = f"创建会议失败: {resp.status_code}"
        return result
    
    session_id = resp.json()["data"]["session_id"]
    log(f"[OK] 会议创建成功，session_id: {session_id}")
    
    # 步骤2: 开始会议
    log("步骤2: 开始会议...")
    resp = start_meeting(session_id)
    if resp.status_code != 200:
        log(f"[FAIL] 开始会议失败: {resp.status_code} - {resp.text}")
        result["response"] = f"开始会议失败: {resp.status_code}"
        return result
    log(f"[OK] 会议已开始，状态: {resp.json()['data']['status']}")
    
    # 步骤3: 结束会议（测试点）
    log(f"步骤3: 结束会议 (template_style={template_style})...")
    resp = end_meeting(session_id, template_style)
    
    result["actual"] = resp.status_code
    
    try:
        result["response"] = resp.json() if resp.headers.get('content-type', '').startswith('application/json') else resp.text
    except:
        result["response"] = resp.text
    
    log(f"响应状态码: {resp.status_code}")
    log(f"响应内容: {json.dumps(result['response'], ensure_ascii=False, indent=2) if isinstance(result['response'], dict) else result['response'][:500]}")
    
    # 判定结果
    if resp.status_code == expected_status:
        if expected_detail_contains:
            # 检查错误详情是否包含预期字符串
            try:
                detail = resp.json().get("detail", "")
                if expected_detail_contains in detail:
                    result["status"] = "PASS"
                    log(f"[PASS] 状态码正确 ({expected_status})，错误详情包含 '{expected_detail_contains}'")
                else:
                    result["status"] = "FAIL"
                    log(f"[FAIL] 状态码正确但错误详情不包含 '{expected_detail_contains}'，实际: {detail}")
            except:
                result["status"] = "FAIL"
                log(f"[FAIL] 无法解析响应内容检查错误详情")
        else:
            result["status"] = "PASS"
            log(f"[PASS] 状态码正确 ({expected_status})")
    else:
        result["status"] = "FAIL"
        log(f"[FAIL] 状态码错误，期望 {expected_status}，实际 {resp.status_code}")
    
    return result

def main():
    """主函数"""
    log("="*60)
    log("测试清单 1.3: template_style 参数测试")
    log("="*60)
    
    # 检查服务
    if not check_service():
        log("[ERROR] 服务未运行，请先启动服务: uvicorn main:app --host 0.0.0.0 --port 8765")
        sys.exit(1)
    log("[OK] 服务运行正常")
    
    results = []
    
    # 测试用例1: template_style=detailed
    result1 = run_test_case(
        case_num=1,
        description="结束会议带 detailed 模板",
        template_style="detailed",
        expected_status=200
    )
    results.append(result1)
    
    # 测试用例2: template_style=invalid_style
    result2 = run_test_case(
        case_num=2,
        description="结束会议带无效模板风格",
        template_style="invalid_style",
        expected_status=400,
        expected_detail_contains="无效的模板风格"
    )
    results.append(result2)
    
    # 测试用例3: 省略 template_style
    result3 = run_test_case(
        case_num=3,
        description="结束会议不带 template_style 参数（默认）",
        template_style=None,  # 省略参数
        expected_status=200
    )
    results.append(result3)
    
    # 汇总报告
    log("\n" + "="*60)
    log("测试报告汇总")
    log("="*60)
    
    for r in results:
        status_icon = "[PASS]" if r["status"] == "PASS" else "[FAIL]"
        log(f"{status_icon} 用例 {r['case_num']}: {r['description']}")
        log(f"   输入: {r['input']}")
        log(f"   期望: HTTP {r['expected']}")
        log(f"   实际: HTTP {r['actual']}")
        log(f"   结果: {r['status']}")
        log("")
    
    # 统计
    passed = sum(1 for r in results if r["status"] == "PASS")
    total = len(results)
    log(f"总计: {passed}/{total} 通过")
    
    # 保存详细报告
    report = {
        "test_suite": "测试清单 1.3 - template_style 参数测试",
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed
        },
        "results": results
    }
    
    with open("test_report_1.3.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    log(f"详细报告已保存到: test_report_1.3.json")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
