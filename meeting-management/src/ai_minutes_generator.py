#!/usr/bin/env python3
"""
AI 会议纪要生成器
使用 DeepSeek API 替代规则引擎

更新记录:
- 2026-02-25: 添加重试机制、超时配置、详细日志
"""

import json
import os
import logging
import time
from typing import Dict, List, Optional
from datetime import datetime

import requests

# 配置日志
logger = logging.getLogger(__name__)

# DeepSeek API 配置
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# 请求配置
REQUEST_TIMEOUT = int(os.getenv("AI_REQUEST_TIMEOUT", "60"))  # 默认60秒
MAX_RETRIES = int(os.getenv("AI_MAX_RETRIES", "3"))  # 默认重试3次
RETRY_DELAY = float(os.getenv("AI_RETRY_DELAY", "1.0"))  # 重试间隔秒数
MAX_TEXT_LENGTH = int(os.getenv("AI_MAX_TEXT_LENGTH", "15000"))  # 最大文本长度


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


def validate_transcription(transcription: str) -> tuple[bool, str]:
    """
    验证转写文本的有效性
    
    Returns:
        (是否有效, 错误信息)
    """
    if not transcription:
        return False, "转写文本为空"
    
    if not isinstance(transcription, str):
        return False, f"转写文本类型错误: {type(transcription)}"
    
    text_len = len(transcription.strip())
    if text_len == 0:
        return False, "转写文本仅包含空白字符"
    
    if text_len < 10:
        logger.warning(f"转写文本过短 ({text_len} 字符)，可能影响生成质量")
    
    return True, ""


def truncate_transcription(transcription: str, max_length: int = MAX_TEXT_LENGTH) -> str:
    """
    截断过长的转写文本，保留开头和结尾
    
    Args:
        transcription: 原始转写文本
        max_length: 最大长度
        
    Returns:
        截断后的文本
    """
    if len(transcription) <= max_length:
        return transcription
    
    # 保留开头 60% 和结尾 40%
    head_len = int(max_length * 0.6)
    tail_len = max_length - head_len
    
    head = transcription[:head_len]
    tail = transcription[-tail_len:]
    
    logger.warning(f"转写文本过长 ({len(transcription)} 字符)，已截断至 {max_length} 字符")
    
    return f"{head}\n\n...[中间内容省略]...\n\n{tail}"


def generate_minutes_with_ai(
    transcription: str,
    title_hint: str = "",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    max_retries: int = MAX_RETRIES,
    timeout: int = REQUEST_TIMEOUT
) -> Optional[Dict]:
    """
    使用 DeepSeek AI 生成会议纪要（带重试机制）
    
    Args:
        transcription: 会议转写文本
        title_hint: 会议标题提示
        api_key: DeepSeek API Key（默认从环境变量读取）
        base_url: API 基础 URL
        model: 模型名称
        max_retries: 最大重试次数
        timeout: 请求超时时间（秒）
        
    Returns:
        会议纪要字典，失败返回 None
    """
    # 参数准备
    api_key = api_key or DEEPSEEK_API_KEY
    base_url = base_url or DEEPSEEK_BASE_URL
    model = model or DEEPSEEK_MODEL
    
    # 验证 API Key
    if not api_key:
        logger.error("DeepSeek API Key 未配置，请设置 DEEPSEEK_API_KEY 环境变量")
        raise ValueError("DeepSeek API Key 未配置，请设置 DEEPSEEK_API_KEY 环境变量")
    
    # 验证转写文本
    is_valid, error_msg = validate_transcription(transcription)
    if not is_valid:
        logger.error(f"转写文本验证失败: {error_msg}")
        return fallback_to_rule_engine(transcription, error_msg)
    
    # 截断过长文本
    processed_text = truncate_transcription(transcription)
    
    # 构建提示词
    user_prompt = f"会议转写文本：\n\n{processed_text}\n\n请生成会议纪要 JSON："
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
    
    # 带重试的请求
    last_error = None
    for attempt in range(max_retries):
        try:
            logger.info(f"AI 生成请求: 第 {attempt + 1}/{max_retries} 次尝试, 文本长度: {len(processed_text)} 字符")
            start_time = time.time()
            
            response = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=timeout
            )
            
            elapsed = time.time() - start_time
            logger.info(f"AI 响应时间: {elapsed:.2f} 秒")
            
            # 处理 HTTP 错误
            if response.status_code == 401:
                logger.error("API 认证失败 (401)，请检查 DEEPSEEK_API_KEY 是否正确")
                raise ValueError("API Key 无效或已过期")
            
            if response.status_code == 429:
                logger.warning("API 速率限制 (429)，等待后重试...")
                if attempt < max_retries - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))  # 指数退避
                    continue
                raise requests.exceptions.RequestException("API 速率限制，已耗尽重试次数")
            
            if response.status_code == 503:
                logger.warning("API 服务暂时不可用 (503)，等待后重试...")
                if attempt < max_retries - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                    continue
            
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # 解析 JSON
            try:
                minutes = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"AI 返回的 JSON 解析失败: {e}, 内容: {content[:200]}...")
                raise
            
            # 标准化字段
            minutes = normalize_minutes(minutes, title_hint)
            
            logger.info(f"AI 纪要生成成功: {len(minutes.get('topics', []))} 个议题, "
                       f"{sum(len(t.get('action_items', [])) for t in minutes.get('topics', []))} 个行动项")
            
            return minutes
            
        except requests.exceptions.Timeout:
            last_error = "请求超时"
            logger.warning(f"第 {attempt + 1} 次尝试超时 (>{timeout}秒)")
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY)
                
        except requests.exceptions.ConnectionError as e:
            last_error = f"连接错误: {e}"
            logger.warning(f"第 {attempt + 1} 次尝试连接失败: {e}")
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                
        except (requests.exceptions.RequestException, ValueError) as e:
            last_error = str(e)
            logger.error(f"请求异常: {e}")
            # 这些错误通常重试无用，直接抛出
            raise
            
        except Exception as e:
            last_error = str(e)
            logger.error(f"第 {attempt + 1} 次尝试异常: {e}")
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY)
    
    # 所有重试都失败了
    logger.error(f"AI 生成失败，已重试 {max_retries} 次，最后错误: {last_error}")
    return None


def normalize_minutes(minutes: Dict, title_hint: str = "") -> Dict:
    """
    标准化会议纪要字段
    
    Args:
        minutes: 原始会议纪要字典
        title_hint: 标题提示
        
    Returns:
        标准化后的字典
    """
    # 确保基础字段存在
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
    
    # 添加元数据
    minutes["_generated_at"] = datetime.now().isoformat()
    minutes["_generator"] = "deepseek-ai"
    
    return minutes


def fallback_to_rule_engine(transcription: str, reason: str = "") -> Dict:
    """
    AI 失败时的降级方案：返回基础结构
    （不调用旧的规则引擎，避免噪音）
    
    Args:
        transcription: 转写文本
        reason: 失败原因
        
    Returns:
        基础会议纪要结构
    """
    logger.warning(f"使用降级方案生成纪要，原因: {reason}")
    
    # 尝试提取标题（第一行或前50字符）
    title = "AI 生成失败"
    if transcription and len(transcription) > 10:
        first_line = transcription.strip().split('\n')[0][:50]
        if len(first_line) > 10:
            title = f"未识别会议 - {first_line}..."
    
    return {
        "title": title,
        "participants": [],
        "topics": [{
            "title": "会议内容（AI生成失败）",
            "discussion_points": [f"[AI生成失败原因: {reason}]"],
            "conclusion": "",
            "action_items": []
        }],
        "risks": [],
        "pending_confirmations": [],
        "_ai_failed": True,
        "_fail_reason": reason,
        "_generated_at": datetime.now().isoformat(),
        "_raw_transcription_preview": transcription[:500] + "..." if len(transcription) > 500 else transcription
    }


def generate_minutes_with_fallback(
    transcription: str,
    title_hint: str = "",
    **kwargs
) -> Dict:
    """
    生成会议纪要，带自动降级
    
    优先使用 AI 生成，失败时自动降级到基础结构
    
    Args:
        transcription: 会议转写文本
        title_hint: 会议标题提示
        **kwargs: 传递给 generate_minutes_with_ai 的其他参数
        
    Returns:
        会议纪要字典（AI生成或降级结构）
    """
    try:
        result = generate_minutes_with_ai(transcription, title_hint, **kwargs)
        if result is not None:
            return result
    except Exception as e:
        logger.error(f"AI 生成异常: {e}")
    
    # AI 失败，使用降级方案
    return fallback_to_rule_engine(transcription, "AI 生成返回空结果或抛出异常")


if __name__ == "__main__":
    # 配置测试日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 测试用例
    test_cases = [
        ("正常文本", """
[00:00:01] 张三: 大家早上好，今天我们讨论项目进度。
[00:00:10] 李四: 我这边完成了80%，预计周五完成。
[00:00:15] 张三: 好的，那周五前把代码提交。
"""),
        ("空文本", ""),
        ("超短文本", "开会"),
    ]
    
    for name, text in test_cases:
        print(f"\n{'='*50}")
        print(f"测试: {name}")
        print(f"{'='*50}")
        
        try:
            result = generate_minutes_with_fallback(text, "项目进度会")
            print(f"结果: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}...")
        except Exception as e:
            print(f"错误: {e}")
