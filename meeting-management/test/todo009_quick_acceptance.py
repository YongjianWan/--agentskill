#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TODO-009: Phase 4 快速验收测试
基于已有会议数据，测试4种模板质量
"""

import sys
import io
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import requests
import json
from pathlib import Path
from datetime import datetime

BASE_URL = "http://localhost:8765/api/v1"
OUTPUT_DIR = Path(__file__).parent / "todo009_output"
OUTPUT_DIR.mkdir(exist_ok=True)


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def get_existing_meetings():
    """获取已有会议列表"""
    try:
        resp = requests.get(f"{BASE_URL}/meetings?limit=10", timeout=10)
        data = resp.json()
        if data.get("code") == 0:
            return data["data"]["items"]
        return []
    except Exception as e:
        log(f"获取会议列表失败: {e}")
        return []


def get_meeting_detail(session_id: str):
    """获取会议详情"""
    try:
        resp = requests.get(f"{BASE_URL}/meetings/{session_id}", timeout=10)
        return resp.json()
    except Exception as e:
        log(f"获取会议详情失败: {e}")
        return None


def test_template(session_id: str, template: str):
    """测试单个模板"""
    try:
        resp = requests.post(
            f"{BASE_URL}/meetings/{session_id}/regenerate",
            json={"template_style": template},
            timeout=60
        )
        result = resp.json()
        
        if result.get("code") == 0:
            minutes = result["data"]["minutes"]
            char_count = len(json.dumps(minutes, ensure_ascii=False))
            
            # 保存
            output_file = OUTPUT_DIR / f"{template}_{session_id[:8]}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(minutes, f, ensure_ascii=False, indent=2)
            
            return {"success": True, "char_count": char_count, "file": str(output_file), "content": minutes}
        else:
            return {"success": False, "error": result.get("message")}
    except Exception as e:
        return {"success": False, "error": str(e)}


def analyze_gov_scenario(results: dict):
    """分析政府场景适配度"""
    log("\n" + "="*60)
    log("政府会议场景适配度分析")
    log("="*60)
    
    analysis = {
        "scores": {},
        "recommendations": []
    }
    
    # 检查详细版
    if "detailed" in results and results["detailed"]["success"]:
        content = results["detailed"]["content"]
        
        # 检查必要字段
        checks = {
            "会议标题": bool(content.get("title")),
            "参会人员": bool(content.get("participants")),
            "会议总结": bool(content.get("summary")),
            "议题划分": len(content.get("topics", [])) > 0,
            "行动项": any(t.get("action_items") for t in content.get("topics", [])),
            "风险点": "risks" in content,
        }
        
        passed = sum(checks.values())
        score = passed / len(checks) * 100
        analysis["scores"]["detailed"] = f"{passed}/{len(checks)} ({score:.0f}%)"
        
        log(f"详细版合规检查: {passed}/{len(checks)}")
        for item, ok in checks.items():
            log(f"  {'✓' if ok else '✗'} {item}")
        
        # 议题结构分析
        topics = content.get("topics", [])
        log(f"\n议题数量: {len(topics)}")
        for i, t in enumerate(topics[:3], 1):
            points = len(t.get("discussion_points", []))
            has_concl = bool(t.get("conclusion"))
            actions = len(t.get("action_items", []))
            log(f"  议题{i}: {points}讨论点 | {'有' if has_concl else '无'}结论 | {actions}行动项")
        
        # 建议
        if not checks["行动项"]:
            analysis["recommendations"].append("详细版应强化行动项提取的prompt引导")
        if not checks["参会人员"]:
            analysis["recommendations"].append("转写文本缺少发言人识别，需检查Whisper说话人分离")
    
    # 检查高管摘要版
    if "executive" in results and results["executive"]["success"]:
        content = results["executive"]["content"]
        exec_checks = {
            "核心结论": bool(content.get("executive_summary")),
            "关键决策": len(content.get("key_decisions", [])) > 0,
            "风险缓解": len(content.get("risks_and_mitigations", [])) > 0,
        }
        passed = sum(exec_checks.values())
        analysis["scores"]["executive"] = f"{passed}/{len(exec_checks)} ({passed/len(exec_checks)*100:.0f}%)"
        
        log(f"\n高管摘要版合规: {passed}/{len(exec_checks)}")
        for item, ok in exec_checks.items():
            log(f"  {'✓' if ok else '✗'} {item}")
    
    return analysis


def generate_report(meeting, results, analysis):
    """生成验收报告"""
    report = {
        "test_id": "TODO-009",
        "test_name": "Phase 4 真实场景验收（快速版）",
        "timestamp": datetime.now().isoformat(),
        "test_mode": "基于已有会议数据",
        "meeting": {
            "session_id": meeting.get("session_id"),
            "title": meeting.get("title"),
            "status": meeting.get("status"),
            "full_text_length": len(meeting.get("full_text", "")) if meeting.get("full_text") else 0
        },
        "template_results": {k: {"success": v.get("success"), "char_count": v.get("char_count")} 
                            for k, v in results.items()},
        "government_analysis": analysis,
        "recommendations": analysis.get("recommendations", [])
    }
    
    report_file = OUTPUT_DIR / f"acceptance_report_{datetime.now().strftime('%m%d_%H%M')}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    log(f"\n📄 报告已保存: {report_file}")
    return report


def main():
    print("\n" + "="*70)
    print("TODO-009: Phase 4 真实场景验收测试（快速版）")
    print("="*70)
    
    # 1. 获取已有会议
    log("获取已有会议列表...")
    meetings = get_existing_meetings()
    
    if not meetings:
        log("❌ 无可用会议数据，请先运行完整转写测试")
        return 1
    
    # 找第一个已完成的会议
    completed = [m for m in meetings if m.get("status") == "COMPLETED"]
    if not completed:
        log("❌ 无已完成会议，无法进行模板测试")
        return 1
    
    meeting = completed[0]
    session_id = meeting["session_id"]
    log(f"✅ 使用会议: {meeting.get('title', 'Unknown')} ({session_id[:8]}...)")
    
    # 获取完整详情
    detail = get_meeting_detail(session_id)
    if detail:
        meeting = detail.get("data", meeting)
    
    # 2. 测试4种模板
    log("\n测试4种纪要模板...")
    templates = ["detailed", "concise", "action", "executive"]
    results = {}
    
    for tmpl in templates:
        log(f"  生成 {tmpl} 版...", end=" ")
        result = test_template(session_id, tmpl)
        if result["success"]:
            log(f"✅ ({result['char_count']}字符)")
        else:
            log(f"❌ {result.get('error', 'Unknown')}")
        results[tmpl] = result
    
    # 3. 政府场景分析
    analysis = analyze_gov_scenario(results)
    
    # 4. 生成报告
    report = generate_report(meeting, results, analysis)
    
    # 5. 结论
    log("\n" + "="*60)
    log("验收结论")
    log("="*60)
    
    success_count = sum(1 for r in results.values() if r.get("success"))
    log(f"模板测试: {success_count}/4 通过")
    log(f"政府适配: {analysis['scores'].get('detailed', 'N/A')}")
    
    if analysis.get("recommendations"):
        log("\n💡 优化建议:")
        for rec in analysis["recommendations"]:
            log(f"  - {rec}")
        log("\n⚠️ 建议调优 prompts.py")
        return 1
    else:
        log("\n✅ prompts.py 满足需求，无需调优")
        return 0


if __name__ == "__main__":
    sys.exit(main())
