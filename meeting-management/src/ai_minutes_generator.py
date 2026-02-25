#!/usr/bin/env python3
"""
AI 会议纪要生成器
使用 DeepSeek API 替代规则引擎
"""

import json
import os
import requests
from typing import Dict, List, Optional

# DeepSeek API 配置
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")


SYSTEM_PROMPT = """你是一个专业的会议纪要助手。请根据会议转写文本生成结构化的会议纪要。

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
                {"action": "具体行动描述", "owner": "负责人", "deadline": "截止日期或空字符串"}
            ]
        }
    ],
    "risks": ["风险点1", "风险点2"],
    "pending_confirmations": ["待确认事项"]
}

规则：
1. 议题划分要合理，每个议题有明确边界
2. 结论必须准确，不要编造，没有就留空
3. 行动项必须包含：做什么、谁来做、何时完成
   - 只提取真正的任务分配，不要提取自我介绍、进度汇报等
   - deadline 格式：YYYY-MM-DD 或"下周三"等相对时间
4. 风险点要真实存在，过滤误报（如"没问题"不是风险）
5. 不确定的内容放入 pending_confirmations
6. 参会人从发言人中提取，去重"""


def generate_minutes_with_ai(
    transcription: str,
    title_hint: str = "",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None
) -> Optional[Dict]:
    """
    使用 DeepSeek AI 生成会议纪要
    
    Args:
        transcription: 会议转写文本
        title_hint: 会议标题提示
        api_key: DeepSeek API Key（默认从环境变量读取）
        base_url: API 基础 URL
        model: 模型名称
        
    Returns:
        会议纪要字典，失败返回 None
    """
    api_key = api_key or DEEPSEEK_API_KEY
    base_url = base_url or DEEPSEEK_BASE_URL
    model = model or DEEPSEEK_MODEL
    
    if not api_key:
        raise ValueError("DeepSeek API Key 未配置，请设置 DEEPSEEK_API_KEY 环境变量")
    
    user_prompt = f"会议转写文本：\n\n{transcription[:15000]}\n\n请生成会议纪要 JSON："
    if title_hint:
        user_prompt = f"会议标题：{title_hint}\n\n{user_prompt}"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 4000,
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        
        # 解析 JSON
        minutes = json.loads(content)
        
        # 标准化字段
        minutes.setdefault("title", title_hint or "未命名会议")
        minutes.setdefault("participants", [])
        minutes.setdefault("topics", [])
        minutes.setdefault("risks", [])
        minutes.setdefault("pending_confirmations", [])
        
        # 标准化 topics
        for topic in minutes["topics"]:
            topic.setdefault("title", "未命名议题")
            topic.setdefault("discussion_points", [])
            topic.setdefault("conclusion", "")
            topic.setdefault("action_items", [])
            
            # 标准化 action_items
            for action in topic["action_items"]:
                action.setdefault("action", "")
                action.setdefault("owner", "待定")
                action.setdefault("deadline", "")
        
        return minutes
        
    except requests.exceptions.RequestException as e:
        print(f"[AI] API 请求失败: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"[AI] JSON 解析失败: {e}")
        return None
    except Exception as e:
        print(f"[AI] 生成失败: {e}")
        return None


def fallback_to_rule_engine(transcription: str) -> Dict:
    """
    AI 失败时的降级方案：返回基础结构
    （不调用旧的规则引擎，避免噪音）
    """
    return {
        "title": "AI 生成失败",
        "participants": [],
        "topics": [{
            "title": "会议内容",
            "discussion_points": ["[原始转写]"],
            "conclusion": "",
            "action_items": []
        }],
        "risks": [],
        "pending_confirmations": [],
        "_ai_failed": True,
        "_raw_transcription": transcription[:500] + "..." if len(transcription) > 500 else transcription
    }


if __name__ == "__main__":
    # 测试
    test_text = """
[00:00:01] 张三: 大家早上好，今天我们讨论项目进度。
[00:00:10] 李四: 我这边完成了80%，预计周五完成。
[00:00:15] 张三: 好的，那周五前把代码提交。
"""
    
    result = generate_minutes_with_ai(test_text, "项目进度会")
    if result:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("生成失败")
