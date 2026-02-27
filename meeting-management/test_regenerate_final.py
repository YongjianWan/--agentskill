#!/usr/bin/env python3
"""测试 regenerate 接口"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8765"
TEST_SESSION_ID = "TEST_REGENERATE_001"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def regenerate_minutes(session_id, template_style="concise"):
    """调用 regenerate 接口"""
    url = f"{BASE_URL}/api/v1/meetings/{session_id}/regenerate"
    payload = {"template_style": template_style}
    resp = requests.post(url, json=payload, timeout=60)
    return resp.status_code, resp.json()

def get_meeting_detail(session_id):
    """获取会议详情"""
    url = f"{BASE_URL}/api/v1/meetings/{session_id}/result"
    resp = requests.get(url, timeout=10)
    return resp.status_code, resp.json()

def main():
    log("=" * 70)
    log("测试 regenerate 接口")
    log("=" * 70)
    
    # 1. 第一次调用 regenerate - concise 模板
    log("\n[步骤1] 第一次调用 regenerate (template_style=concise)...")
    status1, result1 = regenerate_minutes(TEST_SESSION_ID, "concise")
    log(f"响应状态码: {status1}")
    log(f"响应结果:\n{json.dumps(result1, indent=2, ensure_ascii=False)}")
    
    if status1 != 200:
        log(f"错误：期望 200，但得到 {status1}")
        return
    
    # 2. 验证返回的 minutes 结构
    log("\n[步骤2] 验证 minutes 结构...")
    data1 = result1.get("data", {})
    minutes1 = data1.get("minutes")
    if minutes1:
        log(f"[OK] minutes 字段存在")
        log(f"  - topics: {len(minutes1.get('topics', []))} 个议题")
        log(f"  - risks: {len(minutes1.get('risks', []))} 个风险点")
        log(f"  - participants: {len(minutes1.get('participants', []))} 个参与者")
        log(f"  - _meta: {minutes1.get('_meta', {})}")
    else:
        log("[FAIL] minutes 字段不存在")
    
    # 3. 再次查询会议，验证 minutes_history
    log("\n[步骤3] 查询会议详情，验证 minutes_history...")
    status_detail1, detail1 = get_meeting_detail(TEST_SESSION_ID)
    log(f"查询状态码: {status_detail1}")
    if status_detail1 == 200:
        meeting1 = detail1.get("data", {})
        # minutes_history 只在内部存储，API 返回中可能没有
        log(f"会议数据已获取")
    
    # 4. 第二次调用 regenerate - detailed 模板
    log("\n[步骤4] 第二次调用 regenerate (template_style=detailed)...")
    status2, result2 = regenerate_minutes(TEST_SESSION_ID, "detailed")
    log(f"响应状态码: {status2}")
    log(f"响应结果:\n{json.dumps(result2, indent=2, ensure_ascii=False)}")
    
    if status2 != 200:
        log(f"错误：期望 200，但得到 {status2}")
        return
    
    # 5. 验证第二次返回
    log("\n[步骤5] 验证第二次返回的 minutes...")
    data2 = result2.get("data", {})
    minutes2 = data2.get("minutes")
    if minutes2:
        log(f"[OK] minutes 字段存在")
        log(f"  - topics: {len(minutes2.get('topics', []))} 个议题")
        log(f"  - _meta.template: {minutes2.get('_meta', {}).get('template', 'unknown')}")
    
    # 6. 检查历史版本（直接查数据库）
    log("\n[步骤6] 检查数据库中的 minutes_history...")
    import sys
    sys.path.insert(0, 'src')
    from database.connection import AsyncSessionLocal
    from models.meeting import MeetingModel
    from sqlalchemy import select
    import asyncio
    
    async def check_history():
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(MeetingModel).where(MeetingModel.session_id == TEST_SESSION_ID))
            meeting = result.scalar_one_or_none()
            if meeting:
                history = meeting.minutes_history
                if history:
                    log(f"[OK] minutes_history 存在，共 {len(history)} 个历史版本")
                    for i, h in enumerate(history):
                        log(f"  版本 {i+1}: template={h.get('template', 'unknown')}, generated_at={h.get('generated_at', 'unknown')}")
                else:
                    log("[FAIL] minutes_history 为空")
            else:
                log("[FAIL] 会议未找到")
    
    asyncio.run(check_history())
    
    # 7. 测试无效模板
    log("\n[步骤7] 测试无效模板风格...")
    status3, result3 = regenerate_minutes(TEST_SESSION_ID, "invalid_template")
    log(f"响应状态码: {status3}")
    log(f"响应: {result3}")
    if status3 == 400:
        log("[OK] 无效模板正确返回 400")
    else:
        log(f"[FAIL] 期望 400，但得到 {status3}")
    
    # 8. 测试无 full_text 的会议
    log("\n[步骤8] 测试无 full_text 的会议...")
    # 先创建一个没有 full_text 的会议
    status4, result4 = regenerate_minutes("TEST_NO_DOCX_001", "concise")
    log(f"响应状态码: {status4}")
    log(f"响应: {result4}")
    if status4 == 400:
        log("[OK] 无 full_text 正确返回 400")
    else:
        log(f"期望 400，但得到 {status4}")
    
    # 总结
    log("\n" + "=" * 70)
    log("测试总结:")
    log("=" * 70)
    log(f"测试会议: {TEST_SESSION_ID}")
    log(f"第一次 regenerate (concise): HTTP {status1}")
    log(f"第二次 regenerate (detailed): HTTP {status2}")
    log(f"无效模板测试: HTTP {status3} (期望 400)")
    log(f"无 full_text 测试: HTTP {status4} (期望 400)")
    
    if status1 == 200 and status2 == 200 and status3 == 400 and status4 == 400:
        log("\n[OK] 所有测试通过！")
    else:
        log("\n[FAIL] 部分测试失败")

if __name__ == "__main__":
    main()
