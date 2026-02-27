#!/usr/bin/env python3
"""测试 regenerate 接口"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8765"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def get_meetings():
    """获取会议列表"""
    resp = requests.get(f"{BASE_URL}/api/v1/meetings", timeout=10)
    return resp.json()

def get_meeting(session_id):
    """获取会议详情"""
    resp = requests.get(f"{BASE_URL}/api/v1/meetings/{session_id}", timeout=10)
    return resp.json()

def regenerate_minutes(session_id, template_style="concise"):
    """调用 regenerate 接口"""
    url = f"{BASE_URL}/api/v1/meetings/{session_id}/regenerate"
    payload = {"template_style": template_style}
    resp = requests.post(url, json=payload, timeout=30)
    return resp.status_code, resp.json()

def main():
    log("=" * 60)
    log("开始测试 regenerate 接口")
    log("=" * 60)
    
    # 1. 获取会议列表，找 completed 状态的会议
    log("\n[步骤1] 获取会议列表...")
    meetings_data = get_meetings()
    meetings = meetings_data.get("list", [])
    
    completed_meetings = [m for m in meetings if m.get("status") == "completed"]
    log(f"找到 {len(completed_meetings)} 个 completed 状态的会议")
    
    # 2. 找有 full_text 的会议
    target_session = None
    for m in completed_meetings:
        sid = m.get("session_id")
        detail = get_meeting(sid)
        meeting = detail.get("meeting", {})
        full_text = meeting.get("full_text")
        if full_text and len(full_text) > 0:
            log(f"找到有 full_text 的会议: {sid}")
            log(f"  full_text 长度: {len(full_text)}")
            target_session = sid
            break
    
    if not target_session:
        log("错误：没有找到有 full_text 的 completed 会议")
        return
    
    # 3. 第一次调用 regenerate - concise 模板
    log("\n[步骤2] 第一次调用 regenerate (template_style=concise)...")
    status1, result1 = regenerate_minutes(target_session, "concise")
    log(f"响应状态码: {status1}")
    log(f"响应结果:\n{json.dumps(result1, indent=2, ensure_ascii=False)}")
    
    if status1 != 200:
        log(f"错误：期望 200，但得到 {status1}")
        return
    
    # 4. 验证返回的 minutes 结构
    log("\n[步骤3] 验证 minutes 结构...")
    minutes = result1.get("minutes")
    if minutes:
        log(f"minutes 字段存在")
        log(f"minutes 内容: {json.dumps(minutes, indent=2, ensure_ascii=False)}")
    else:
        log("警告：minutes 字段不存在")
    
    # 5. 再次查询会议，验证 minutes_history
    log("\n[步骤4] 查询会议，验证 minutes_history...")
    detail2 = get_meeting(target_session)
    meeting2 = detail2.get("meeting", {})
    minutes_history = meeting2.get("minutes_history")
    log(f"minutes_history: {json.dumps(minutes_history, indent=2, ensure_ascii=False)}")
    
    if minutes_history and len(minutes_history) > 0:
        log(f"✓ minutes_history 已保存 {len(minutes_history)} 个历史版本")
    else:
        log("警告：minutes_history 为空或不存在")
    
    # 6. 第二次调用 regenerate - detailed 模板
    log("\n[步骤5] 第二次调用 regenerate (template_style=detailed)...")
    status2, result2 = regenerate_minutes(target_session, "detailed")
    log(f"响应状态码: {status2}")
    log(f"响应结果:\n{json.dumps(result2, indent=2, ensure_ascii=False)}")
    
    if status2 != 200:
        log(f"错误：期望 200，但得到 {status2}")
        return
    
    # 7. 再次查询会议，验证历史版本累积
    log("\n[步骤6] 再次查询会议，验证历史版本累积...")
    detail3 = get_meeting(target_session)
    meeting3 = detail3.get("meeting", {})
    minutes_history3 = meeting3.get("minutes_history")
    log(f"minutes_history: {json.dumps(minutes_history3, indent=2, ensure_ascii=False)}")
    
    if minutes_history3 and len(minutes_history3) >= 2:
        log(f"✓ minutes_history 已累积 {len(minutes_history3)} 个历史版本")
    else:
        log(f"警告：minutes_history 只有 {len(minutes_history3) if minutes_history3 else 0} 个历史版本")
    
    # 8. 最终验证
    log("\n[步骤7] 最终验证...")
    current_minutes = meeting3.get("minutes")
    log(f"当前 minutes: {json.dumps(current_minutes, indent=2, ensure_ascii=False)}")
    
    log("\n" + "=" * 60)
    log("测试完成总结:")
    log("=" * 60)
    log(f"测试会议: {target_session}")
    log(f"第一次 regenerate (concise): 状态码={status1}")
    log(f"第二次 regenerate (detailed): 状态码={status2}")
    log(f"minutes_history 历史版本数: {len(minutes_history3) if minutes_history3 else 0}")
    if status1 == 200 and status2 == 200:
        log("结果: ✓ 测试通过")
    else:
        log("结果: ✗ 测试失败")

if __name__ == "__main__":
    main()
