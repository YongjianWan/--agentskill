#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TODO-009: Phase 4 真实场景验收测试

任务清单:
1. 用真实会议录音跑完整链路（转写→纪要生成）
2. 对比4种模板输出质量
3. 评估政府会议场景适配度（格式/术语/结构）
4. 根据结果决定是否需要调优 prompts.py

使用文件: test/周四 10点19分.mp3 (7.67MB, 11分钟录音)
"""

import requests
import json
import time
import os
import sys
from pathlib import Path
from datetime import datetime

# Windows 编码修复
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 配置
BASE_URL = "http://localhost:8765/api/v1"
HEALTH_URL = "http://localhost:8765/api/v1/health"
REAL_AUDIO_FILE = Path(__file__).parent / "周四 10点19分.mp3"
OUTPUT_DIR = Path(__file__).parent / "todo009_output"

# 确保输出目录存在
OUTPUT_DIR.mkdir(exist_ok=True)


def log(msg: str):
    """打印带时间戳的日志"""
    try:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    except UnicodeEncodeError:
        # 编码失败时简化输出
        safe_msg = msg.encode('ascii', 'ignore').decode('ascii')
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {safe_msg}")


def test_health():
    """1. 检查服务健康状态"""
    log("=" * 60)
    log("步骤1: 检查服务健康状态")
    log("=" * 60)
    
    try:
        resp = requests.get(HEALTH_URL, timeout=10)
        data = resp.json()
        
        if data.get("code") == 0:
            status = data["data"]
            log(f"✅ 服务状态: {status['status']}")
            log(f"   版本: {status['version']}")
            log(f"   运行时间: {status.get('uptime_seconds', 'N/A')}秒")
            
            # 检查组件状态
            components = status.get("components", {})
            for name, comp in components.items():
                comp_status = comp.get("status", "unknown")
                icon = "✅" if comp_status == "ok" else "⚠️" if comp_status == "degraded" else "❌"
                log(f"   {icon} {name}: {comp_status}")
            
            return True
        else:
            log(f"❌ 健康检查失败: {data}")
            return False
    except Exception as e:
        log(f"❌ 健康检查异常: {e}")
        return False


def test_upload_and_transcribe():
    """2. 上传真实音频并转写"""
    log("\n" + "=" * 60)
    log("步骤2: 上传真实音频文件并转写")
    log("=" * 60)
    
    if not REAL_AUDIO_FILE.exists():
        log(f"❌ 音频文件不存在: {REAL_AUDIO_FILE}")
        return None
    
    log(f"📁 音频文件: {REAL_AUDIO_FILE}")
    log(f"📦 文件大小: {REAL_AUDIO_FILE.stat().st_size / 1024 / 1024:.2f} MB")
    
    # 上传文件
    try:
        with open(REAL_AUDIO_FILE, "rb") as f:
            files = {"file": (REAL_AUDIO_FILE.name, f, "audio/mpeg")}
            data = {
                "title": f"TODO-009验收测试-{datetime.now().strftime('%m%d-%H%M')}",
                "user_id": "test_user_001"
            }
            
            log("⏫ 正在上传文件...")
            start_time = time.time()
            resp = requests.post(f"{BASE_URL}/upload/audio", files=files, data=data, timeout=300)
            upload_time = time.time() - start_time
        
        result = resp.json()
        
        if result.get("code") == 0:
            session_id = result["data"]["session_id"]
            log(f"✅ 上传成功 (耗时: {upload_time:.1f}s)")
            log(f"   会话ID: {session_id}")
            log(f"   标题: {result['data'].get('file_name')}")
            
            # 等待转写完成
            log("⏳ 等待转写和纪要生成完成...")
            return wait_for_completion(session_id)
        else:
            log(f"❌ 上传失败: {result.get('message')}")
            log(f"   响应: {result}")
            return None
            
    except Exception as e:
        log(f"❌ 上传异常: {e}")
        return None


def wait_for_completion(session_id: str, timeout: int = 600) -> dict:
    """等待会议处理完成"""
    start = time.time()
    last_status = None
    
    while time.time() - start < timeout:
        try:
            resp = requests.get(f"{BASE_URL}/meetings/{session_id}", timeout=10)
            data = resp.json()
            
            if data.get("code") == 0:
                meeting = data["data"]
                status = meeting.get("status")
                
                if status != last_status:
                    log(f"   状态变化: {last_status} -> {status}")
                    last_status = status
                
                if status == "COMPLETED":
                    log(f"✅ 处理完成 (总耗时: {time.time() - start:.1f}s)")
                    return meeting
                elif status == "ERROR":
                    log(f"❌ 处理失败")
                    return None
            
            time.sleep(5)
        except Exception as e:
            log(f"⚠️ 查询状态异常: {e}")
            time.sleep(5)
    
    log(f"⏰ 等待超时")
    return None


def test_all_templates(session_id: str) -> dict:
    """3. 对比4种模板输出质量"""
    log("\n" + "=" * 60)
    log("步骤3: 对比4种模板输出质量")
    log("=" * 60)
    
    templates = ["detailed", "concise", "action", "executive"]
    results = {}
    
    for template in templates:
        log(f"\n📋 测试模板: {template}")
        
        try:
            resp = requests.post(
                f"{BASE_URL}/meetings/{session_id}/regenerate",
                json={"template_style": template},
                timeout=120
            )
            result = resp.json()
            
            if result.get("code") == 0:
                data = result["data"]
                minutes = data.get("minutes", {})
                
                # 保存结果
                output_file = OUTPUT_DIR / f"{template}_{meeting_id[:8]}.json"
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(minutes, f, ensure_ascii=False, indent=2)
                
                # 统计信息
                char_count = len(json.dumps(minutes, ensure_ascii=False))
                log(f"   ✅ 生成成功")
                log(f"   📝 字符数: {char_count}")
                log(f"   💾 保存至: {output_file}")
                
                results[template] = {
                    "success": True,
                    "char_count": char_count,
                    "file": str(output_file),
                    "content": minutes
                }
            else:
                log(f"   ❌ 生成失败: {result.get('message')}")
                results[template] = {"success": False, "error": result.get("message")}
                
        except Exception as e:
            log(f"   ❌ 异常: {e}")
            results[template] = {"success": False, "error": str(e)}
    
    return results


def analyze_government_fit(results: dict) -> dict:
    """4. 评估政府会议场景适配度"""
    log("\n" + "=" * 60)
    log("步骤4: 评估政府会议场景适配度")
    log("=" * 60)
    
    analysis = {
        "format_compliance": {},
        "terminology": {},
        "structure": {},
        "recommendations": []
    }
    
    # 检查详细版（政府场景最常用）
    if "detailed" in results and results["detailed"]["success"]:
        content = results["detailed"]["content"]
        
        # 格式检查
        required_fields = ["title", "participants", "topics", "summary"]
        missing = [f for f in required_fields if f not in content]
        analysis["format_compliance"]["detailed"] = {
            "required_fields_present": len(required_fields) - len(missing),
            "required_fields_total": len(required_fields),
            "missing_fields": missing
        }
        
        # 议题结构检查
        topics = content.get("topics", [])
        log(f"📊 详细版议题数量: {len(topics)}")
        
        for i, topic in enumerate(topics[:3], 1):  # 只检查前3个
            has_action_items = bool(topic.get("action_items"))
            has_conclusion = bool(topic.get("conclusion"))
            discussion_points = len(topic.get("discussion_points", []))
            
            log(f"   议题{i}: 讨论点{discussion_points}个 | 结论:{has_conclusion} | 行动项:{has_action_items}")
            
            analysis["structure"][f"topic_{i}"] = {
                "discussion_points": discussion_points,
                "has_conclusion": has_conclusion,
                "has_action_items": has_action_items
            }
        
        # 政府场景检查点
        checks = {
            "有会议标题": bool(content.get("title")),
            "有参会人员列表": bool(content.get("participants")),
            "有会议总结": bool(content.get("summary")),
            "有议题划分": len(topics) > 0,
            "有行动项": any(t.get("action_items") for t in topics),
        }
        
        passed = sum(checks.values())
        log(f"\n🏛️ 政府场景合规检查: {passed}/{len(checks)}")
        for check, status in checks.items():
            icon = "✅" if status else "❌"
            log(f"   {icon} {check}")
        
        analysis["government_compliance_score"] = f"{passed}/{len(checks)}"
        
        # 生成建议
        if not checks["有行动项"]:
            analysis["recommendations"].append("建议增加行动项提取的prompt引导")
        if not checks["有参会人员列表"]:
            analysis["recommendations"].append("转写文本可能缺少发言人标识，需检查")
    
    return analysis


def generate_report(meeting: dict, template_results: dict, analysis: dict):
    """生成验收报告"""
    log("\n" + "=" * 60)
    log("验收报告生成")
    log("=" * 60)
    
    report = {
        "test_id": "TODO-009",
        "test_name": "Phase 4 真实场景验收",
        "timestamp": datetime.now().isoformat(),
        "audio_file": str(REAL_AUDIO_FILE),
        "session_id": meeting.get("session_id"),
        "summary": {
            "transcription_success": meeting is not None,
            "templates_tested": list(template_results.keys()),
            "government_compliance": analysis.get("government_compliance_score", "N/A")
        },
        "template_comparison": {},
        "government_analysis": analysis,
        "recommendations": analysis.get("recommendations", [])
    }
    
    # 模板对比摘要
    for name, result in template_results.items():
        if result.get("success"):
            report["template_comparison"][name] = {
                "char_count": result.get("char_count", 0),
                "suitable_for": {
                    "detailed": "正式会议、政府会议",
                    "concise": "日常站会、快速回顾",
                    "action": "项目跟进、任务分配",
                    "executive": "高层汇报、一页纸摘要"
                }.get(name, "通用")
            }
    
    # 保存报告
    report_file = OUTPUT_DIR / f"acceptance_report_{datetime.now().strftime('%m%d_%H%M')}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    log(f"\n📄 验收报告已保存: {report_file}")
    
    # 打印摘要
    log("\n" + "=" * 60)
    log("验收结果摘要")
    log("=" * 60)
    log(f"转写链路: {'✅ 通过' if meeting else '❌ 失败'}")
    log(f"模板测试: {sum(1 for r in template_results.values() if r.get('success'))}/4 通过")
    log(f"政府适配: {analysis.get('government_compliance_score', 'N/A')}")
    
    if analysis.get("recommendations"):
        log(f"\n💡 优化建议:")
        for rec in analysis["recommendations"]:
            log(f"   - {rec}")
    
    return report


def main():
    """主流程"""
    print("\n" + "=" * 70)
    print("TODO-009: Phase 4 真实场景验收测试")
    print("=" * 70 + "\n")
    
    # 1. 健康检查
    if not test_health():
        log("服务不健康，终止测试")
        sys.exit(1)
    
    # 2. 上传并转写
    meeting = test_upload_and_transcribe()
    if not meeting:
        log("转写链路失败，终止测试")
        sys.exit(1)
    
    # 3. 对比4种模板
    template_results = test_all_templates(meeting["id"])
    
    # 4. 政府场景评估
    analysis = analyze_government_fit(template_results)
    
    # 5. 生成报告
    report = generate_report(meeting, template_results, analysis)
    
    log("\n" + "=" * 60)
    log("TODO-009 验收测试完成")
    log("=" * 60)
    
    # 返回是否需要调优
    need_optimization = len(analysis.get("recommendations", [])) > 0
    if need_optimization:
        log("⚠️ 根据评估结果，建议调优 prompts.py")
        return 1
    else:
        log("✅ 当前 prompts.py 满足政府场景需求，无需调优")
        return 0


if __name__ == "__main__":
    sys.exit(main())
