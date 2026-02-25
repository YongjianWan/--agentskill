#!/usr/bin/env python3
"""对比测试：AI 生成 vs 规则引擎"""

import sys
import json
import time
sys.path.insert(0, '.')

from src.meeting_skill import generate_minutes, create_meeting_skeleton

# 测试数据
test_transcription = """
[00:00:01] 主持人：大家早上好，今天我们召开Q4产品规划评审会。
[00:00:10] 主持人：参会人员有张三、李四、王五，大家请确认一下。
[00:00:15] 张三：我在，前端开发负责人张三。
[00:00:18] 李四：李四在，后端开发。
[00:00:20] 王五：王五在，产品经理。
[00:00:25] 主持人：好，那我们开始。张三先汇报前端进度。
[00:00:30] 张三：目前前端完成了80%，主要页面都已开发完成。
[00:00:35] 张三：还需要一周时间进行细节优化，预计11月15日可以全部完成。
[00:00:40] 主持人：很好，那李四的后端API呢？
[00:00:45] 李四：后端API已经完成了90%，剩余一些边界情况处理。
[00:00:50] 李四：我这边11月30日肯定能完成，可以提前给前端联调。
[00:00:55] 王五：那联调时间定在12月1日到5日可以吗？
[00:01:00] 张三：可以的，我这边15号完成后可以先自测。
[00:01:05] 李四：没问题，我也可以提前准备接口文档。
[00:01:10] 主持人：好的，那确认一下行动项。
[00:01:15] 主持人：张三负责11月15日前完成前端开发，没问题吧？
[00:01:20] 张三：确认，保证按时完成。
[00:01:25] 主持人：李四负责11月30日前完成后端API，并准备接口文档。
[00:01:30] 李四：确认，12月1日可以开始联调。
[00:01:35] 王五：我这边负责验收标准制定，下周三前完成。
[00:01:40] 主持人：还有一个风险点，第三方登录接口最近不稳定，需要关注。
[00:01:45] 李四：是的，我这边会准备一个备用方案。
[00:01:50] 主持人：好的，会议就到这里，大家按计划执行。
"""


def evaluate_quality(meeting, method_name):
    """评估生成质量"""
    print(f"\n{'='*60}")
    print(f"方法: {method_name}")
    print('='*60)
    
    topics = meeting.topics
    print(f"议题数: {len(topics)}")
    
    # 统计结论
    conclusions = [t.conclusion for t in topics if t.conclusion]
    print(f"有结论的议题: {len(conclusions)}/{len(topics)} ({len(conclusions)/max(len(topics),1)*100:.0f}%)")
    
    # 统计行动项
    action_items = []
    for t in topics:
        action_items.extend(t.action_items)
    print(f"行动项总数: {len(action_items)}")
    
    # 统计有负责人和截止日期的行动项
    valid_actions = [a for a in action_items if a.owner and a.owner != "待定"]
    print(f"有负责人的行动项: {len(valid_actions)}/{len(action_items)}")
    
    # 统计风险点
    print(f"风险点数: {len(meeting.risks)}")
    
    # 展示前2个议题
    print("\n前2个议题:")
    for i, t in enumerate(topics[:2], 1):
        print(f"  议题{i}: {t.title[:40]}...")
        if t.conclusion:
            print(f"    结论: {t.conclusion[:50]}...")
        if t.action_items:
            for a in t.action_items[:2]:
                print(f"    行动: [{a.owner}] {a.action[:30]}... (截止: {a.deadline})")
    
    return {
        "method": method_name,
        "topics_count": len(topics),
        "conclusion_rate": len(conclusions) / max(len(topics), 1),
        "action_items_count": len(action_items),
        "valid_actions": len(valid_actions),
        "risks_count": len(meeting.risks)
    }


def main():
    print("="*60)
    print("AI 生成 vs 规则引擎 对比测试")
    print("="*60)
    
    results = []
    
    # 测试1: AI 生成
    print("\n[1/2] 测试 AI 生成...")
    start = time.time()
    try:
        meeting_ai = generate_minutes(
            test_transcription,
            title="Q4产品规划评审会",
            use_ai=True
        )
        ai_time = time.time() - start
        print(f"耗时: {ai_time:.1f}秒")
        
        if meeting_ai.status == "ai_generated":
            result_ai = evaluate_quality(meeting_ai, "DeepSeek AI")
            result_ai["time"] = ai_time
            results.append(result_ai)
        else:
            print("⚠️ AI 生成失败，已降级到骨架模式")
            result_ai = evaluate_quality(meeting_ai, "AI 失败(骨架)")
            result_ai["time"] = ai_time
            results.append(result_ai)
    except Exception as e:
        print(f"❌ AI 生成异常: {e}")
    
    # 测试2: 骨架模式（原规则引擎已弃用）
    print("\n[2/2] 测试骨架模式（无AI）...")
    start = time.time()
    meeting_skeleton = create_meeting_skeleton(
        test_transcription,
        title="Q4产品规划评审会"
    )
    skeleton_time = time.time() - start
    print(f"耗时: {skeleton_time:.3f}秒")
    
    result_skeleton = evaluate_quality(meeting_skeleton, "骨架模式(无AI)")
    result_skeleton["time"] = skeleton_time
    results.append(result_skeleton)
    
    # 对比总结
    print("\n" + "="*60)
    print("对比总结")
    print("="*60)
    
    for r in results:
        print(f"\n{r['method']}:")
        print(f"  耗时: {r.get('time', 0):.1f}秒")
        print(f"  议题数: {r['topics_count']}")
        print(f"  结论率: {r['conclusion_rate']*100:.0f}%")
        print(f"  行动项: {r['action_items_count']} (有效: {r['valid_actions']})")
        print(f"  风险点: {r['risks_count']}")
    
    # 保存对比结果
    with open('output/ai_vs_rule_comparison.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print("\n" + "="*60)
    print("对比结果已保存到: output/ai_vs_rule_comparison.json")
    print("="*60)


if __name__ == "__main__":
    main()
