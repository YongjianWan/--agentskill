# Phase 4: AI纪要生成增强功能 - 设计文档

> **版本**: 1.0  
> **日期**: 2026-02-26  
> **状态**: 设计阶段  

---

## 1. 概述

### 1.1 目标

Phase 4 旨在增强 AI 纪要生成功能，实现以下目标：

| 功能 | 说明 | 优先级 |
|------|------|--------|
| **通义千问API接入** | 替代 DeepSeek，支持阿里云通义千问 | P0 |
| **多风格纪要模板** | 详细版、简洁版、行动项版等多种风格 | P0 |
| **实时纪要预览** | 通过 WebSocket 流式推送生成进度 | P1 |

### 1.2 架构变化

```
┌─────────────────────────────────────────────────────────────────┐
│                        Phase 4 架构                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     │
│  │   用户界面    │◄───►│  WebSocket   │◄───►│  纪要生成器   │     │
│  └──────────────┘     └──────────────┘     └──────┬───────┘     │
│         ▲                                         │              │
│         │         实时预览流                       │ AI调用        │
│         │                                         ▼              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     │
│  │  模板选择器   │────►│  提示词引擎   │◄───►│ 通义千问 API │     │
│  └──────────────┘     └──────────────┘     └──────────────┘     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. API 配置方案

### 2.1 环境变量配置

更新 `.env.example`：

```bash
# ========== AI配置（Phase 4增强版） ==========

# AI提供商选择: tongyi | deepseek | openai
AI_PROVIDER=tongyi

# --- 通义千问配置（推荐）---
# 阿里云API Key，从 https://dashscope.aliyun.com/ 获取
TONGYI_API_KEY=your_tongyi_api_key
TONGYI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
TONGYI_MODEL=qwen-max  # 可选: qwen-max, qwen-plus, qwen-turbo

# --- DeepSeek配置（兼容保留）---
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# --- OpenAI兼容配置（备用）---
OPENAI_API_KEY=your_openai_key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4

# --- 请求配置 ---
AI_REQUEST_TIMEOUT=120          # 请求超时（秒）
AI_MAX_RETRIES=3                # 最大重试次数
AI_RETRY_DELAY=1.0              # 重试间隔（秒）
AI_MAX_TEXT_LENGTH=20000        # 最大文本长度

# --- 功能开关 ---
ENABLE_AI_MINUTES=true          # 是否启用AI纪要
ENABLE_STREAMING_PREVIEW=true   # 是否启用实时预览
MINUTES_TEMPLATE_STYLE=auto     # 默认模板: auto | detailed | concise | action
```

### 2.2 配置类设计

```python
# src/config/ai_config.py

from dataclasses import dataclass
from typing import Optional
import os

@dataclass
class AIProviderConfig:
    """AI提供商配置"""
    name: str
    api_key: str
    base_url: str
    model: str
    timeout: int = 120
    max_retries: int = 3
    
    @classmethod
    def from_env(cls, provider: str) -> "AIProviderConfig":
        """从环境变量加载配置"""
        configs = {
            "tongyi": {
                "api_key": os.getenv("TONGYI_API_KEY", ""),
                "base_url": os.getenv("TONGYI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
                "model": os.getenv("TONGYI_MODEL", "qwen-max"),
            },
            "deepseek": {
                "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
                "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
                "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            },
            "openai": {
                "api_key": os.getenv("OPENAI_API_KEY", ""),
                "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                "model": os.getenv("OPENAI_MODEL", "gpt-4"),
            }
        }
        
        if provider not in configs:
            raise ValueError(f"不支持的AI提供商: {provider}")
        
        config = configs[provider]
        return cls(
            name=provider,
            api_key=config["api_key"],
            base_url=config["base_url"],
            model=config["model"],
            timeout=int(os.getenv("AI_REQUEST_TIMEOUT", "120")),
            max_retries=int(os.getenv("AI_MAX_RETRIES", "3"))
        )


@dataclass
class MinutesTemplateConfig:
    """纪要模板配置"""
    style: str = "auto"  # auto | detailed | concise | action | executive
    language: str = "zh"  # zh | en
    include_timestamps: bool = False
    max_topics: Optional[int] = None
    max_action_items: Optional[int] = None
```

---

## 3. 提示词模板设计

### 3.1 模板体系

```
prompts/
├── __init__.py
├── base.py                    # 基础模板类
├── templates/
│   ├── detailed.py            # 详细版
│   ├── concise.py             # 简洁版
│   ├── action.py              # 行动项版
│   ├── executive.py           # 高管摘要版
│   └── custom.py              # 自定义模板
└── renderer.py                # 模板渲染器
```

### 3.2 基础模板类

```python
# src/prompts/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum


class MinutesStyle(Enum):
    """纪要风格枚举"""
    AUTO = "auto"              # 自动选择（根据内容长度）
    DETAILED = "detailed"      # 详细版
    CONCISE = "concise"        # 简洁版
    ACTION = "action"          # 行动项版
    EXECUTIVE = "executive"    # 高管摘要版


@dataclass
class MinutesTemplate:
    """纪要模板定义"""
    style: MinutesStyle
    name: str
    description: str
    system_prompt: str
    user_prompt_template: str
    output_schema: Dict[str, Any]
    
    def render(self, transcription: str, title_hint: str = "", **kwargs) -> str:
        """渲染提示词"""
        return self.user_prompt_template.format(
            transcription=transcription,
            title_hint=title_hint,
            **kwargs
        )


class BaseMinutesTemplate(ABC):
    """纪要模板基类"""
    
    @property
    @abstractmethod
    def style(self) -> MinutesStyle:
        pass
    
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """系统提示词"""
        pass
    
    @property
    @abstractmethod
    def user_prompt_template(self) -> str:
        """用户提示词模板"""
        pass
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        """输出JSON Schema"""
        return {
            "type": "object",
            "required": ["title", "participants", "topics"],
            "properties": {
                "title": {"type": "string"},
                "participants": {"type": "array", "items": {"type": "string"}},
                "topics": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "discussion_points": {"type": "array", "items": {"type": "string"}},
                            "conclusion": {"type": "string"},
                            "action_items": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "action": {"type": "string"},
                                        "owner": {"type": "string"},
                                        "deadline": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                },
                "risks": {"type": "array", "items": {"type": "string"}},
                "pending_confirmations": {"type": "array", "items": {"type": "string"}},
                "summary": {"type": "string"}
            }
        }
```

### 3.3 详细版模板

```python
# src/prompts/templates/detailed.py

from prompts.base import BaseMinutesTemplate, MinutesStyle


class DetailedTemplate(BaseMinutesTemplate):
    """
    详细版纪要模板
    
    适用场景：正式会议、需要完整记录讨论过程
    特点：
    - 议题划分详细
    - 保留讨论要点（最多8条/议题）
    - 完整的结论描述
    - 详细的行动项（负责人、截止日期、交付物）
    - 风险点和待确认事项
    """
    
    @property
    def style(self) -> MinutesStyle:
        return MinutesStyle.DETAILED
    
    @property
    def system_prompt(self) -> str:
        return """你是一位专业的会议纪要撰写专家。请根据会议转写文本生成**详细版**的会议纪要。

## 输出要求

输出必须是合法的JSON格式：

```json
{
    "title": "会议标题",
    "participants": ["参会人1", "参会人2"],
    "summary": "会议整体概述（200字以内）",
    "topics": [
        {
            "title": "议题标题",
            "discussion_points": ["讨论要点1", "讨论要点2", "...最多8条"],
            "conclusion": "结论描述（详细）",
            "uncertain": ["不确定内容1"],
            "action_items": [
                {
                    "action": "具体行动描述",
                    "owner": "负责人",
                    "deadline": "YYYY-MM-DD",
                    "deliverable": "交付物描述"
                }
            ]
        }
    ],
    "risks": ["风险点1", "风险点2"],
    "pending_confirmations": ["待确认事项1"]
}
```

## 详细规则

### 议题划分
- 按议程或主题自然划分
- 每个议题有明确的开始和结束
- 议题标题简洁明了（不超过20字）

### 讨论要点
- 提取关键观点、数据、对比
- 保留重要的问答环节
- 去除口语化表达和重复内容
- 每个议题最多8条要点

### 结论
- 明确记录达成的共识
- 记录决策结果（如方案选择）
- 没有结论时留空字符串
- 绝不编造结论

### 行动项
- **必须**包含：做什么、谁来做、何时完成
- 负责人使用真实姓名
- 截止日期格式：YYYY-MM-DD 或"本周五"等
- 明确交付物是什么
- 只提取真正的任务分配，不要提取自我介绍、进度汇报

### 风险点
- 识别影响项目进度或结果的因素
- 过滤误报（如"没问题"不是风险）
- 包含风险等级（高/中/低）

### 待确认事项
- 记录需要后续跟进的问题
- 记录信息不完整的内容"""
    
    @property
    def user_prompt_template(self) -> str:
        return """请为以下会议转写文本生成**详细版**纪要。

{title_section}

## 会议转写文本

```
{transcription}
```

## 要求

1. 这是详细版纪要，请尽可能完整地记录讨论内容
2. 每个议题的讨论要点不少于3条（如有足够内容）
3. 结论必须准确，不能编造
4. 行动项必须完整（任务、负责人、时间）
5. 输出合法的JSON格式"""
    
    def render(self, transcription: str, title_hint: str = "", **kwargs) -> str:
        title_section = f"会议标题：{title_hint}" if title_hint else ""
        return self.user_prompt_template.format(
            transcription=transcription,
            title_section=title_section
        )
```

### 3.4 简洁版模板

```python
# src/prompts/templates/concise.py

from prompts.base import BaseMinutesTemplate, MinutesStyle


class ConciseTemplate(BaseMinutesTemplate):
    """
    简洁版纪要模板
    
    适用场景：日常站会、简短沟通、快速同步
    特点：
    - 高度概括
    - 只保留关键决策和行动项
    - 阅读时间 < 2分钟
    """
    
    @property
    def style(self) -> MinutesStyle:
        return MinutesStyle.CONCISE
    
    @property
    def system_prompt(self) -> str:
        return """你是一位高效的会议纪要撰写专家。请根据会议转写文本生成**简洁版**的会议纪要。

## 输出要求

输出必须是合法的JSON格式：

```json
{
    "title": "会议标题",
    "participants": ["参会人1", "参会人2"],
    "summary": "一句话概述会议核心内容",
    "topics": [
        {
            "title": "议题标题",
            "discussion_points": ["核心要点1", "核心要点2"],
            "conclusion": "结论",
            "action_items": [
                {"action": "行动", "owner": "负责人", "deadline": "日期"}
            ]
        }
    ],
    "action_items_summary": [
        {"action": "行动", "owner": "负责人", "deadline": "日期", "topic": "所属议题"}
    ],
    "risks": [],
    "pending_confirmations": []
}
```

## 简洁规则

### 议题
- 最多5个议题
- 每个议题最多3条讨论要点
- 只保留核心结论

### 讨论要点
- 高度概括，去除细节
- 每个要点不超过50字
- 只记录有决策价值的内容

### 行动项汇总
- 单独列出所有行动项
- 方便快速查阅待办事项
- 包含所属议题便于追溯

### 整体要求
- 全文阅读时间控制在2分钟内
- 去除所有寒暄、客套话
- 去除重复和冗余内容"""
    
    @property
    def user_prompt_template(self) -> str:
        return """请为以下会议转写文本生成**简洁版**纪要。

{title_section}

## 会议转写文本

```
{transcription}
```

## 要求

1. 这是简洁版，请高度概括，去除冗余
2. 全文阅读时间控制在2分钟内
3. 重点突出决策和行动项
4. 输出合法的JSON格式"""
    
    def render(self, transcription: str, title_hint: str = "", **kwargs) -> str:
        title_section = f"会议标题：{title_hint}" if title_hint else ""
        return self.user_prompt_template.format(
            transcription=transcription,
            title_section=title_section
        )
```

### 3.5 行动项版模板

```python
# src/prompts/templates/action.py

from prompts.base import BaseMinutesTemplate, MinutesStyle


class ActionTemplate(BaseMinutesTemplate):
    """
    行动项版纪要模板
    
    适用场景：项目管理、任务分配、执行跟进
    特点：
    - 以行动项为核心
    - 详细的任务分解
    - 便于后续跟踪执行
    """
    
    @property
    def style(self) -> MinutesStyle:
        return MinutesStyle.ACTION
    
    @property
    def system_prompt(self) -> str:
        return """你是一位项目管理专家。请根据会议转写文本生成**行动项导向**的会议纪要。

## 输出要求

输出必须是合法的JSON格式：

```json
{
    "title": "会议标题",
    "participants": ["参会人1", "参会人2"],
    "summary": "会议核心目标",
    "topics": [
        {
            "title": "议题标题",
            "discussion_points": ["背景信息"],
            "conclusion": "决策结果",
            "action_items": [
                {
                    "action": "具体任务描述",
                    "owner": "负责人",
                    "deadline": "YYYY-MM-DD",
                    "deliverable": "可验证的交付物",
                    "priority": "高|中|低",
                    "dependencies": ["依赖的任务"]
                }
            ]
        }
    ],
    "action_items_table": [
        {
            "action": "任务",
            "owner": "负责人",
            "deadline": "截止日期",
            "priority": "优先级",
            "status": "待启动"
        }
    ],
    "owners_summary": {
        "负责人1": ["任务1", "任务2"],
        "负责人2": ["任务3"]
    },
    "risks": [],
    "pending_confirmations": []
}
```

## 行动项规则

### 任务描述
- 使用动宾结构，明确具体动作
- 避免模糊词汇（如"处理一下"）
- 包含可量化的标准

### 负责人
- 每个任务只有一个主负责人
- 使用参会人真实姓名
- 如果未明确指定，标记为"待分配"

### 截止日期
- 尽可能明确到具体日期
- 相对时间转换为绝对日期
- 未明确时标记为"待确认"

### 交付物
- 明确产出物是什么
- 描述可验证的标准
- 例如："文档"→"技术方案文档（含架构图）"

### 优先级
- 高：本周必须完成，阻塞其他任务
- 中：下周完成，有依赖关系
- 低：可延后，无强时间要求

### 依赖关系
- 识别任务间的先后顺序
- 标注前置任务
- 识别可并行执行的任务

### 汇总表格
- 按截止日期排序
- 按优先级分组
- 按负责人分组"""
    
    @property
    def user_prompt_template(self) -> str:
        return """请为以下会议转写文本生成**行动项导向**的纪要。

{title_section}

## 会议转写文本

```
{transcription}
```

## 要求

1. 这是行动项版，请以任务执行为核心
2. 每个行动项必须包含：任务、负责人、截止日期、交付物、优先级
3. 提供多种汇总视图（按时间、按优先级、按负责人）
4. 识别任务间的依赖关系
5. 输出合法的JSON格式"""
    
    def render(self, transcription: str, title_hint: str = "", **kwargs) -> str:
        title_section = f"会议标题：{title_hint}" if title_hint else ""
        return self.user_prompt_template.format(
            transcription=transcription,
            title_section=title_section
        )
```

### 3.6 高管摘要版模板

```python
# src/prompts/templates/executive.py

from prompts.base import BaseMinutesTemplate, MinutesStyle


class ExecutiveTemplate(BaseMinutesTemplate):
    """
    高管摘要版纪要模板
    
    适用场景：向管理层汇报、跨部门同步、决策会议
    特点：
    - 一页纸原则
    - 聚焦决策和战略
    - 突出风险和资源需求
    """
    
    @property
    def style(self) -> MinutesStyle:
        return MinutesStyle.EXECUTIVE
    
    @property
    def system_prompt(self) -> str:
        return """你是一位高级管理顾问。请根据会议转写文本生成**高管摘要版**的会议纪要。

## 输出要求

输出必须是合法的JSON格式：

```json
{
    "title": "会议标题",
    "participants": ["参会人1", "参会人2"],
    "executive_summary": "核心结论（50字以内）",
    "key_decisions": [
        {
            "decision": "决策内容",
            "rationale": "决策依据",
            "impact": "预期影响"
        }
    ],
    "resource_requests": [
        {
            "type": "人力|预算|时间|其他",
            "description": "资源需求描述",
            "amount": "数量",
            "justification": "理由"
        }
    ],
    "risks_and_mitigations": [
        {
            "risk": "风险描述",
            "level": "高|中|低",
            "mitigation": "缓解措施"
        }
    ],
    "next_milestones": [
        {
            "milestone": "里程碑",
            "target_date": "日期",
            "owner": "负责人"
        }
    ],
    "topics": [],
    "pending_confirmations": []
}
```

## 高管摘要规则

### 执行摘要
- 控制在50字以内
- 一句话说明会议核心结论
- 决策者最关心的问题

### 关键决策
- 记录所有正式决策
- 说明决策依据
- 分析预期影响

### 资源需求
- 人力需求（人数、角色、时间）
- 预算需求（金额、用途）
- 时间需求（关键节点）

### 风险与缓解
- 识别影响目标达成的风险
- 评估风险等级
- 提出缓解措施

### 下步里程碑
- 未来关键节点
- 负责人
- 交付物

### 一页纸原则
- 全文控制在A4纸一页内
- 优先展示决策和资源
- 详细讨论放在附录（可选）"""
    
    @property
    def user_prompt_template(self) -> str:
        return """请为以下会议转写文本生成**高管摘要版**纪要。

{title_section}

## 会议转写文本

```
{transcription}
```

## 要求

1. 这是高管摘要版，请聚焦决策、资源、风险
2. 遵循"一页纸原则"，高度精炼
3. 突出需要管理层关注和支持的事项
4. 输出合法的JSON格式"""
    
    def render(self, transcription: str, title_hint: str = "", **kwargs) -> str:
        title_section = f"会议标题：{title_hint}" if title_hint else ""
        return self.user_prompt_template.format(
            transcription=transcription,
            title_section=title_section
        )
```

### 3.7 模板选择器

```python
# src/prompts/selector.py

from typing import Optional
from prompts.base import MinutesStyle, BaseMinutesTemplate
from prompts.templates.detailed import DetailedTemplate
from prompts.templates.concise import ConciseTemplate
from prompts.templates.action import ActionTemplate
from prompts.templates.executive import ExecutiveTemplate


class TemplateSelector:
    """模板选择器"""
    
    _templates = {
        MinutesStyle.DETAILED: DetailedTemplate(),
        MinutesStyle.CONCISE: ConciseTemplate(),
        MinutesStyle.ACTION: ActionTemplate(),
        MinutesStyle.EXECUTIVE: ExecutiveTemplate(),
    }
    
    @classmethod
    def get_template(cls, style: MinutesStyle) -> BaseMinutesTemplate:
        """获取指定模板"""
        if style == MinutesStyle.AUTO:
            # 自动选择逻辑
            return cls._auto_select()
        return cls._templates.get(style, DetailedTemplate())
    
    @classmethod
    def _auto_select(cls, transcription_length: int = 0, meeting_duration: int = 0) -> BaseMinutesTemplate:
        """
        自动选择模板
        
        规则：
        - 会议时长 < 15分钟：简洁版
        - 15-60分钟：详细版
        - > 60分钟 或 文本 > 10000字：详细版
        - 包含"项目"、"里程碑"等关键词：行动项版
        """
        if meeting_duration < 15 * 60:  # 15分钟
            return ConciseTemplate()
        elif "项目" in "" or "里程碑" in "":  # 简化示例
            return ActionTemplate()
        else:
            return DetailedTemplate()
    
    @classmethod
    def list_available_styles(cls) -> list:
        """列出可用模板"""
        return [
            {"value": s.value, "name": s.name, "description": cls._get_description(s)}
            for s in MinutesStyle
        ]
    
    @classmethod
    def _get_description(cls, style: MinutesStyle) -> str:
        """获取模板描述"""
        descriptions = {
            MinutesStyle.AUTO: "根据内容自动选择最合适的模板",
            MinutesStyle.DETAILED: "详细版 - 完整记录讨论过程和决策依据",
            MinutesStyle.CONCISE: "简洁版 - 高度概括，适合快速阅读",
            MinutesStyle.ACTION: "行动项版 - 以任务分解和执行为核心",
            MinutesStyle.EXECUTIVE: "高管摘要版 - 聚焦决策、资源、风险",
        }
        return descriptions.get(style, "")
```

---

## 4. 纪要生成流程

### 4.1 整体流程图

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  会议结束    │────►│  转写文本   │────►│  模板选择   │────►│  构建提示词  │
└─────────────┘     └─────────────┘     └─────────────┘     └──────┬──────┘
                                                                   │
                    ┌───────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  保存结果   │◄────│  解析响应   │◄────│  调用API    │◄────│  发送请求   │
│  推送客户端  │     │  验证格式   │     │  流式接收   │     │  实时预览   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

### 4.2 核心类设计

```python
# src/services/minutes_generator.py

import json
import logging
from typing import AsyncIterator, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from prompts.base import MinutesStyle
from prompts.selector import TemplateSelector
from config.ai_config import AIProviderConfig

logger = logging.getLogger(__name__)


@dataclass
class GenerationProgress:
    """生成进度"""
    stage: str  # "preparing" | "calling_api" | "receiving" | "parsing" | "completed" | "error"
    progress: int  # 0-100
    message: str
    partial_content: Optional[Dict] = None
    error: Optional[str] = None


class StreamingMinutesGenerator:
    """
    流式纪要生成器
    
    支持：
    - 多AI提供商（通义千问、DeepSeek等）
    - 多模板风格
    - 流式输出（实时预览）
    """
    
    def __init__(self, provider_config: Optional[AIProviderConfig] = None):
        self.config = provider_config or AIProviderConfig.from_env("tongyi")
        self.template_selector = TemplateSelector()
    
    async def generate(
        self,
        transcription: str,
        title_hint: str = "",
        style: MinutesStyle = MinutesStyle.AUTO,
        meeting_duration: int = 0
    ) -> AsyncIterator[GenerationProgress]:
        """
        流式生成会议纪要
        
        Args:
            transcription: 会议转写文本
            title_hint: 会议标题提示
            style: 纪要风格
            meeting_duration: 会议时长（秒），用于自动选择模板
            
        Yields:
            GenerationProgress: 生成进度
        """
        try:
            # Stage 1: 准备
            yield GenerationProgress(
                stage="preparing",
                progress=10,
                message="正在选择模板并构建提示词..."
            )
            
            # 自动选择模板
            if style == MinutesStyle.AUTO:
                template = self.template_selector._auto_select(
                    len(transcription), 
                    meeting_duration
                )
            else:
                template = self.template_selector.get_template(style)
            
            # 构建提示词
            system_prompt = template.system_prompt
            user_prompt = template.render(transcription, title_hint)
            
            yield GenerationProgress(
                stage="preparing",
                progress=20,
                message=f"已选择模板: {template.style.value}"
            )
            
            # Stage 2: 调用API
            yield GenerationProgress(
                stage="calling_api",
                progress=30,
                message="正在连接AI服务..."
            )
            
            # 根据提供商调用不同API
            if self.config.name == "tongyi":
                async for progress in self._call_tongyi(
                    system_prompt, user_prompt, template.output_schema
                ):
                    yield progress
            elif self.config.name == "deepseek":
                async for progress in self._call_deepseek(
                    system_prompt, user_prompt, template.output_schema
                ):
                    yield progress
            else:
                raise ValueError(f"不支持的AI提供商: {self.config.name}")
                
        except Exception as e:
            logger.error(f"纪要生成失败: {e}", exc_info=True)
            yield GenerationProgress(
                stage="error",
                progress=0,
                message=f"生成失败: {str(e)}",
                error=str(e)
            )
    
    async def _call_tongyi(
        self, 
        system_prompt: str, 
        user_prompt: str,
        output_schema: Dict
    ) -> AsyncIterator[GenerationProgress]:
        """
        调用通义千问API（支持流式输出）
        
        使用阿里 dashscope SDK 或 OpenAI 兼容模式
        """
        import openai
        
        client = openai.AsyncOpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            timeout=self.config.timeout
        )
        
        try:
            # 使用流式输出
            stream = await client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=4000,
                response_format={"type": "json_object"},
                stream=True  # 启用流式输出
            )
            
            content_parts = []
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    content_parts.append(chunk.choices[0].delta.content)
                    
                    # 计算进度（简单估算）
                    progress = min(30 + len(content_parts) * 2, 80)
                    partial_content = "".join(content_parts)
                    
                    # 尝试解析部分JSON（用于实时预览）
                    preview_data = self._try_parse_partial_json(partial_content)
                    
                    yield GenerationProgress(
                        stage="receiving",
                        progress=progress,
                        message="正在接收AI响应...",
                        partial_content=preview_data
                    )
            
            # 完整内容接收完毕
            full_content = "".join(content_parts)
            
            yield GenerationProgress(
                stage="parsing",
                progress=90,
                message="正在解析结果..."
            )
            
            # 解析JSON
            try:
                result = json.loads(full_content)
                
                # 验证并补充字段
                result = self._normalize_result(result)
                
                yield GenerationProgress(
                    stage="completed",
                    progress=100,
                    message="生成完成",
                    partial_content=result
                )
                
            except json.JSONDecodeError as e:
                yield GenerationProgress(
                    stage="error",
                    progress=0,
                    message=f"JSON解析失败: {e}",
                    error=str(e)
                )
                
        except Exception as e:
            logger.error(f"通义千问API调用失败: {e}")
            raise
    
    def _try_parse_partial_json(self, content: str) -> Optional[Dict]:
        """
        尝试解析部分JSON（用于实时预览）
        
        策略：
        1. 尝试直接解析
        2. 尝试补全缺失的括号
        3. 返回已解析的部分字段
        """
        # 简化实现：尝试解析，失败返回None
        try:
            return json.loads(content)
        except:
            # 尝试提取已完整的字段
            result = {}
            try:
                # 提取title
                if '"title"' in content:
                    import re
                    match = re.search(r'"title"\s*:\s*"([^"]*)"', content)
                    if match:
                        result["title"] = match.group(1)
                
                # 提取summary（如果存在）
                if '"summary"' in content:
                    match = re.search(r'"summary"\s*:\s*"([^"]*)"', content)
                    if match:
                        result["summary"] = match.group(1)
                
                return result if result else None
            except:
                return None
    
    def _normalize_result(self, result: Dict) -> Dict:
        """标准化结果字段"""
        # 确保基础字段存在
        result.setdefault("title", "未命名会议")
        result.setdefault("participants", [])
        result.setdefault("topics", [])
        result.setdefault("risks", [])
        result.setdefault("pending_confirmations", [])
        
        # 标准化topics
        for topic in result.get("topics", []):
            topic.setdefault("title", "未命名议题")
            topic.setdefault("discussion_points", [])
            topic.setdefault("conclusion", "")
            topic.setdefault("action_items", [])
            
            # 标准化action_items
            for action in topic.get("action_items", []):
                action.setdefault("action", "")
                action.setdefault("owner", "待定")
                action.setdefault("deadline", "")
        
        # 添加元数据
        result["_generated_at"] = datetime.now().isoformat()
        result["_generator"] = f"{self.config.name}-{self.config.model}"
        result["_template_style"] = self.template_selector.get_template(
            MinutesStyle.DETAILED  # 需要保存实际使用的模板
        ).style.value
        
        return result
```

### 4.3 集成到会议流程

```python
# src/meeting_skill.py（修改部分）

async def generate_minutes_streaming(
    session_id: str,
    transcription: str,
    title_hint: str = "",
    style: str = "auto",
    websocket_manager = None
) -> Dict:
    """
    流式生成会议纪要并实时推送
    
    Args:
        session_id: 会议ID
        transcription: 转写文本
        title_hint: 标题提示
        style: 模板风格
        websocket_manager: WebSocket管理器，用于推送进度
        
    Returns:
        最终生成的会议纪要
    """
    from services.minutes_generator import StreamingMinutesGenerator
    from prompts.base import MinutesStyle
    
    # 创建生成器
    generator = StreamingMinutesGenerator()
    
    # 解析风格
    try:
        minutes_style = MinutesStyle(style)
    except ValueError:
        minutes_style = MinutesStyle.AUTO
    
    # 获取会议时长
    meeting_duration = 0
    # ... 从session获取时长
    
    final_result = None
    
    # 流式生成
    async for progress in generator.generate(
        transcription=transcription,
        title_hint=title_hint,
        style=minutes_style,
        meeting_duration=meeting_duration
    ):
        # 推送进度到客户端
        if websocket_manager:
            await websocket_manager.send_minutes_progress(session_id, {
                "stage": progress.stage,
                "progress": progress.progress,
                "message": progress.message,
                "preview": progress.partial_content,
                "error": progress.error
            })
        
        # 保存最终结果
        if progress.stage == "completed":
            final_result = progress.partial_content
        elif progress.stage == "error":
            raise Exception(progress.error)
    
    return final_result
```

---

## 5. WebSocket 消息格式设计

### 5.1 实时预览消息

```typescript
// ========== 客户端 → 服务端 ==========

// 选择纪要模板风格
interface SelectMinutesStyleMessage {
    type: "select_minutes_style";
    style: "auto" | "detailed" | "concise" | "action" | "executive";
}

// 请求重新生成纪要
interface RegenerateMinutesMessage {
    type: "regenerate_minutes";
    style?: string;  // 可选，使用新风格重新生成
}


// ========== 服务端 → 客户端 ==========

// 纪要生成进度（流式推送）
interface MinutesProgressMessage {
    type: "minutes_progress";
    stage: "preparing" | "calling_api" | "receiving" | "parsing" | "completed" | "error";
    progress: number;  // 0-100
    message: string;   // 进度描述
    preview?: {        // 部分结果（可选）
        title?: string;
        summary?: string;
        topics_count?: number;
        action_items_count?: number;
        partial_topics?: Array<{
            title: string;
            conclusion?: string;
        }>;
    };
    error?: string;    // 错误信息
}

// 纪要生成完成
interface MinutesCompletedMessage {
    type: "minutes_completed";
    meeting_id: string;
    minutes: {
        title: string;
        participants: string[];
        summary?: string;
        topics: Topic[];
        action_items: ActionItem[];
        risks: string[];
        pending_confirmations: string[];
    };
    style_used: string;  // 实际使用的模板风格
    generated_at: string;  // ISO8601
    download_urls: {
        docx: string;
        json: string;
    };
}

// 模板列表（响应查询）
interface MinutesStylesMessage {
    type: "minutes_styles";
    styles: Array<{
        value: string;
        name: string;
        description: string;
        recommended_for?: string[];
    }>;
}
```

### 5.2 更新后的 WebSocket 协议

```typescript
// ========== 上行消息（浏览器→后端） ==========

// 1. 开始会议
interface StartMessage {
    type: "start";
    title: string;
    user_id: string;
}

// 2. 音频数据块
interface ChunkMessage {
    type: "chunk";
    sequence: number;
    data: string;  // base64编码的webm音频
}

// 3. 结束会议
interface EndMessage {
    type: "end";
}

// 4. 选择纪要风格（新增）
interface SelectStyleMessage {
    type: "select_minutes_style";
    style: "auto" | "detailed" | "concise" | "action" | "executive";
}

// 5. 心跳
interface PingMessage {
    type: "ping";
}

// 6. 获取模板列表（新增）
interface GetStylesMessage {
    type: "get_minutes_styles";
}


// ========== 下行消息（后端→浏览器） ==========

// 1. 会议已启动
interface StartedMessage {
    type: "started";
    meeting_id: string;
    audio_path: string;
}

// 2. 实时转写结果
interface TranscriptMessage {
    type: "transcript";
    text: string;
    sequence: number;
    is_final: boolean;
}

// 3. 纪要生成进度（新增）
interface MinutesProgressMessage {
    type: "minutes_progress";
    stage: string;
    progress: number;
    message: string;
    preview?: object;
    error?: string;
}

// 4. 纪要生成完成（新增字段）
interface CompletedMessage {
    type: "completed";
    meeting_id: string;
    full_text: string;
    minutes: object;  // 完整的纪要内容
    style_used: string;
    minutes_path: string;
    chunk_count: number;
}

// 5. 模板列表响应（新增）
interface StylesResponseMessage {
    type: "minutes_styles";
    styles: Array<{
        value: string;
        name: string;
        description: string;
    }>;
}

// 6. 错误
interface ErrorMessage {
    type: "error";
    code: string;
    message: string;
    recoverable: boolean;
}

// 7. 心跳响应
interface PongMessage {
    type: "pong";
    timestamp: string;
}
```

### 5.3 WebSocket 管理器扩展

```python
# src/services/websocket_manager.py（新增方法）

class WebSocketManager:
    # ... 现有代码 ...
    
    async def send_minutes_progress(self, session_id: str, progress: dict):
        """发送纪要生成进度"""
        session = self.sessions.get(session_id)
        if session and session.is_active:
            await session.send_json({
                "type": "minutes_progress",
                **progress
            })
    
    async def send_minutes_styles(self, session_id: str):
        """发送可用模板列表"""
        from prompts.selector import TemplateSelector
        
        session = self.sessions.get(session_id)
        if session and session.is_active:
            styles = TemplateSelector.list_available_styles()
            await session.send_json({
                "type": "minutes_styles",
                "styles": styles
            })
```

---

## 6. API 端点扩展

### 6.1 REST API 新增

```yaml
# 获取可用的纪要模板风格
GET /api/v1/minutes/styles
Response:
  code: 0
  data:
    styles:
      - value: "auto"
        name: "自动选择"
        description: "根据会议内容自动选择最合适的模板"
      - value: "detailed"
        name: "详细版"
        description: "完整记录讨论过程和决策依据"
      - value: "concise"
        name: "简洁版"
        description: "高度概括，适合快速阅读"
      - value: "action"
        name: "行动项版"
        description: "以任务分解和执行为核心"
      - value: "executive"
        name: "高管摘要版"
        description: "聚焦决策、资源、风险"

# 重新生成纪要（使用不同模板）
POST /api/v1/meetings/{meeting_id}/regenerate
Request:
  style: "action"  # 可选，新模板风格
Response:
  code: 0
  data:
    message: "已开始重新生成"
    style_requested: "action"
```

---

## 7. 实现计划

### 7.1 文件结构

```
src/
├── config/
│   ├── __init__.py
│   └── ai_config.py           # AI配置管理
├── prompts/
│   ├── __init__.py
│   ├── base.py                # 基础模板类
│   ├── selector.py            # 模板选择器
│   ├── renderer.py            # 模板渲染器
│   └── templates/
│       ├── __init__.py
│       ├── detailed.py        # 详细版
│       ├── concise.py         # 简洁版
│       ├── action.py          # 行动项版
│       └── executive.py       # 高管摘要版
├── services/
│   ├── __init__.py
│   ├── minutes_generator.py   # 流式纪要生成器（新）
│   ├── websocket_manager.py   # 扩展WebSocket管理
│   └── transcription_service.py
└── api/
    ├── __init__.py
    ├── websocket.py           # 扩展WebSocket路由
    └── meetings.py            # 扩展REST API
```

### 7.2 实施步骤

| 步骤 | 任务 | 优先级 | 预计工时 |
|------|------|--------|----------|
| 1 | 配置管理（ai_config.py） | P0 | 2h |
| 2 | 模板基础类（prompts/base.py） | P0 | 2h |
| 3 | 详细版模板 | P0 | 3h |
| 4 | 简洁版模板 | P0 | 2h |
| 5 | 行动项版模板 | P1 | 3h |
| 6 | 高管摘要版模板 | P1 | 2h |
| 7 | 模板选择器 | P0 | 2h |
| 8 | 流式生成器（支持通义千问） | P0 | 6h |
| 9 | WebSocket消息扩展 | P0 | 3h |
| 10 | REST API扩展 | P1 | 2h |
| 11 | 集成测试 | P0 | 4h |
| 12 | 文档更新 | P1 | 2h |

---

## 8. 风险与注意事项

### 8.1 技术风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 通义千问API不稳定 | 纪要生成失败 | 保留DeepSeek作为fallback |
| 流式JSON解析出错 | 预览显示异常 | 使用try-catch，降级到非流式 |
| 大文本超出token限制 | 生成不完整 | 截断策略，保留开头和结尾 |

### 8.2 兼容性

- 保持与现有 DeepSeek 配置的兼容
- 新增功能默认关闭，通过环境变量启用
- WebSocket 协议向后兼容

---

## 9. 测试用例

### 9.1 单元测试

```python
# test/test_minutes_templates.py

import pytest
from prompts.selector import TemplateSelector
from prompts.base import MinutesStyle

class TestTemplateSelector:
    def test_get_detailed_template(self):
        template = TemplateSelector.get_template(MinutesStyle.DETAILED)
        assert template.style == MinutesStyle.DETAILED
        assert "详细" in template.system_prompt
    
    def test_auto_selection_short_meeting(self):
        template = TemplateSelector._auto_select(
            transcription_length=1000,
            meeting_duration=10 * 60  # 10分钟
        )
        assert template.style == MinutesStyle.CONCISE
    
    def test_render_template(self):
        template = TemplateSelector.get_template(MinutesStyle.CONCISE)
        prompt = template.render("测试转写文本", "测试会议")
        assert "测试转写文本" in prompt
        assert "测试会议" in prompt
        assert "简洁版" in prompt
```

### 9.2 集成测试

```python
# test/test_streaming_generator.py

import pytest
import asyncio
from services.minutes_generator import StreamingMinutesGenerator

@pytest.mark.asyncio
async def test_streaming_generation():
    generator = StreamingMinutesGenerator()
    
    transcription = """
    [00:00:01] 张三: 大家好，今天讨论项目进度。
    [00:00:10] 李四: 我完成了80%，预计周五完成。
    [00:00:20] 张三: 好的，那周五前提交代码。
    """
    
    stages = []
    async for progress in generator.generate(transcription, "项目进度会"):
        stages.append(progress.stage)
    
    assert "preparing" in stages
    assert "completed" in stages
    assert stages[-1] == "completed"
```

---

## 10. 附录

### 10.1 通义千问 API 参考

```python
# 阿里云 dashscope Python SDK 示例
import dashscope

# 方式1：使用 dashscope SDK
dashscope.api_key = "your-api-key"

response = dashscope.Generation.call(
    model="qwen-max",
    messages=[
        {"role": "system", "content": "你是会议纪要助手"},
        {"role": "user", "content": "生成纪要..."}
    ],
    result_format="message",
    stream=True  # 流式输出
)

# 方式2：使用 OpenAI 兼容模式（推荐）
import openai

client = openai.OpenAI(
    api_key="your-api-key",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

response = client.chat.completions.create(
    model="qwen-max",
    messages=[...],
    stream=True
)
```

### 10.2 模型选择建议

| 模型 | 适用场景 | Token上限 | 特点 |
|------|----------|-----------|------|
| qwen-max | 正式会议纪要 | 8K | 能力强，质量高 |
| qwen-plus | 日常会议 | 8K | 性价比高 |
| qwen-turbo | 快速预览 | 8K | 速度快，成本低 |

---

**文档结束**
