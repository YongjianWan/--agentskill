#!/usr/bin/env python3
"""测试 DeepSeek API 生成会议纪要"""

import os
import json
import requests

# DeepSeek API 配置
BASE_URL = "https://api.deepseek.com"
API_KEY = "sk-2c130f48c7c6474e882a24633a65b328"
MODEL = "deepseek-chat"

def generate_minutes_with_ai(transcription: str, title: str = "") -> dict:
    """使用 DeepSeek 生成会议纪要"""
    
    system_prompt = """你是一个专业的会议纪要助手。请根据会议转写文本生成结构化的会议纪要。

输出格式必须是 JSON：
{
    "title": "会议标题（从内容中提取或总结）",
    "participants": ["参会人列表"],
    "topics": [
        {
            "title": "议题标题",
            "discussion_points": ["讨论要点1", "讨论要点2"],
            "conclusion": "结论（如果没有则留空）",
            "action_items": [
                {"action": "具体行动", "owner": "负责人", "deadline": "截止日期或空"}
            ]
        }
    ],
    "risks": ["风险点1", "风险点2"],
    "pending_confirmations": ["待确认事项"]
}

规则：
1. 议题划分要合理，每个议题有明确边界
2. 结论必须准确，不要编造
3. 行动项必须包含：做什么、谁来做、何时完成
4. 风险点要真实存在，过滤误报
5. 不确定的内容放入 pending_confirmations"""

    user_prompt = f"会议转写文本：\n\n{transcription}\n\n请生成会议纪要 JSON："
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 4000,
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        
        # 解析 JSON
        minutes = json.loads(content)
        return minutes
        
    except Exception as e:
        print(f"API 调用失败: {e}")
        return None


def main():
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
    
    print("="*60)
    print("测试 DeepSeek 生成会议纪要")
    print("="*60)
    
    result = generate_minutes_with_ai(test_transcription, "Q4产品规划评审会")
    
    if result:
        print("\n生成结果：")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # 评估质量
        print("\n" + "="*60)
        print("质量评估")
        print("="*60)
        
        topics_count = len(result.get("topics", []))
        action_items_count = sum(len(t.get("action_items", [])) for t in result.get("topics", []))
        risks_count = len(result.get("risks", []))
        
        print(f"议题数: {topics_count}")
        print(f"行动项数: {action_items_count}")
        print(f"风险点数: {risks_count}")
        
        # 检查结论
        has_conclusion = any(t.get("conclusion") for t in result.get("topics", []))
        print(f"有结论: {has_conclusion}")
        
    else:
        print("生成失败")


if __name__ == "__main__":
    main()
