---
name: meeting-management
description: AI Agent Skill for meeting management. Audio transcription and structured storage with entity linking.
---
# Meeting Management - AI Agent Skill

> **角色定位**：这是 **AI 智能体** 的 Skill，供 AI 调用以完成会议管理任务。
>
> **使用模式**：用户 → AI 智能体 → 本 Skill
>
> **设计原则**：
>
> - Skill 层（本模块）：转写、数据模型、存储、实体关联
> - AI 层（调用方）：语义理解、议题提取、行动项抽取、实体识别

## 架构定位

```
┌───────────────┐
│   AI 调用方    │ ← 语义理解、议题提取、行动项识别
│  (你在这里)   │
└───────┬───────┘
        │ 调用
        ▼
┌───────────────┐
│ Meeting Skill │ ← 转写、数据模型、存储、导出
│   (本模块)    │
└───────────────┘
```

## 核心接口

### 1. 音频转写（Skill 负责）

```python
from meeting_skill import transcribe

result = transcribe("meeting.mp3", model="small")
# Returns:
{
  "segments": [
    {"timestamp": "00:00:01", "speaker": "张三", "text": "我们开始开会吧"}
  ],
  "full_text": "[00:00:01] 张三: 我们开始开会吧...",
  "participants": ["张三", "李四"],
  "duration": 1800,
  "model_used": "small"
}
```

### 2. 数据结构（AI 负责填充）

```python
from meeting_skill import Meeting, Topic, ActionItem
from datetime import datetime

meeting = Meeting(
    # === AI 填写以下字段 ===
    title="产品评审会",           # AI 从文本识别
    date="2026-02-25",
    participants=["张三", "李四"], # 可从转写结果复用
    topics=[
        Topic(
            title="技术方案讨论",   # AI 提取议题
            discussion_points=[     # AI 提取讨论要点
                "对比了方案A和B",
                "方案B成本更低"
            ],
            conclusion="决定采用方案B",  # AI 提取结论
            uncertain=[             # AI 标记不确定内容
                "具体实施时间待定"
            ],
            action_items=[          # AI 抽取行动项
                ActionItem(
                    action="整理技术文档",
                    owner="张三",
                    deadline="2026-03-01",
                    deliverable="文档"
                )
            ]
        )
    ],
    risks=["工期可能紧张"],        # AI 识别风险点
    pending_confirmations=["预算待确认"],
  
    # === Skill 自动生成 ===
    id="M20260225_143012_a1b2c3",
    time_range="14:30-15:30",
    location="会议室A",
    recorder="",
    audio_path="meeting.mp3",
    version=1
)
```

### 3. 保存输出（Skill 负责）

```python
from meeting_skill import save_meeting

files = save_meeting(meeting, output_dir="./output")
# Returns:
{
  "json": "./output/meetings/2026/02/M20260225_143012_a1b2c3/minutes_v1.json",
  "docx": "./output/meetings/2026/02/M20260225_143012_a1b2c3/minutes_v1.docx",
  "meeting_dir": "./output/meetings/2026/02/M20260225_143012_a1b2c3"
}
```

### 4. 其他工具方法

```python
# 查询历史会议
from meeting_skill import query_meetings
results = query_meetings(
    date_range=("2026-02-01", "2026-02-28"),
    keywords=["技术方案"]
)

# 更新会议（创建新版本）
from meeting_skill import update_meeting
meeting_v2 = update_meeting(
    meeting_id="M20260225_143012_a1b2c3",
    title="产品评审会（更新版）"
)
```

## 完整使用示例

```python
from meeting_skill import transcribe, Meeting, Topic, ActionItem, save_meeting

# Step 1: 转写（Skill）
result = transcribe("meeting.mp3")

# Step 2: AI 理解并填充（AI 层）
meeting = Meeting(
    title="AI 识别的会议标题",
    date="2026-02-25",
    participants=result["participants"],
    topics=[
        # AI 分析 result["full_text"] 后填充
        Topic(
            title="议题1",
            discussion_points=["要点1", "要点2"],
            conclusion="结论",
            action_items=[
                ActionItem(action="任务", owner="负责人", deadline="2026-03-01")
            ]
        )
    ],
    risks=[],
    pending_confirmations=[]
)

# Step 3: 保存（Skill）
files = save_meeting(meeting)
print(f"已保存到: {files['docx']}")
```

## 数据模型

### 核心实体

```python
@dataclass
class Meeting:
    id: str                    # 自动生成: M{YYYYMMDD}_{HHMMSS}_{hash6}
    title: str                 # ← AI 填写
    date: str                  # YYYY-MM-DD
    time_range: str            # HH:MM-HH:MM
    location: str
    participants: List[str]    # ← AI 可从转写结果提取
    recorder: str
    topics: List[Topic]        # ← AI 填写（核心）
    risks: List[str]           # ← AI 填写
    pending_confirmations: List[str]  # ← AI 填写
    audio_path: Optional[str]
    version: int = 1
    status: str = "draft"      # draft/final/archived
  
    # === 关联实体（AI 识别，设计预留）===
    policy_refs: List[PolicyRef]      # 涉及政策
    enterprise_refs: List[EnterpriseRef]  # 涉及企业
    project_refs: List[ProjectRef]    # 关联项目

@dataclass
class Topic:
    title: str                 # ← AI 提取议题标题
    discussion_points: List[str]  # ← AI 提取讨论要点
    conclusion: str = ""       # ← AI 提取结论
    uncertain: List[str] = []  # ← AI 标记不确定
    action_items: List[ActionItem] = []  # ← AI 抽取行动项

@dataclass
class ActionItem:
    action: str                # ← AI 抽取动作描述
    owner: str                 # ← AI 识别负责人
    deadline: str              # ← AI 识别截止时间
    deliverable: str = ""      # ← AI 识别交付物
    status: str = "待处理"
  
    # === 关联实体（AI 识别，设计预留）===
    related_policy: Optional[PolicyRef]      # 关联政策
    related_enterprise: Optional[EnterpriseRef]  # 关联企业
    related_project: Optional[ProjectRef]    # 关联项目
```

### 关联实体（设计预留）

```python
@dataclass
class PolicyRef:
    """政策引用 - AI 从会议内容识别"""
    policy_id: str = ""           # 政策ID（如 "P2024-001"）
    clause_ref: str = ""          # 引用条款（如 "第3条第2款"）
    check_required: bool = False  # 是否待核查

@dataclass
class EnterpriseRef:
    """企业关联 - AI 从会议内容识别"""
    enterprise_id: str = ""       # 企业ID
    cooperation_item: str = ""    # 合作事项描述
    contact_person: str = ""      # 对接人
    contact_permission: str = ""  # 权限级别（如 "readonly/edit"）

@dataclass
class ProjectRef:
    """项目关联 - AI 从会议内容识别"""
    project_id: str = ""          # 项目ID
    milestone: str = ""           # 涉及里程碑
    change_point: str = ""        # 变更点说明
```

## 输出格式

### JSON 结构

```json
{
  "id": "M20260225_143012_a1b2c3",
  "title": "产品评审会",
  "date": "2026-02-25",
  "participants": ["张三", "李四"],
  "topics": [
    {
      "title": "技术方案讨论",
      "discussion_points": ["对比方案A和B", "成本分析"],
      "conclusion": "决定采用方案B",
      "action_items": [
        {"action": "整理文档", "owner": "张三", "deadline": "2026-03-01"}
      ]
    }
  ],
  "risks": ["工期紧张"],
  "pending_confirmations": ["预算待确认"],
  "version": 1
}
```

### Word 文档结构

```
会议纪要：{标题}

一、会议基本信息
- 主题/时间/地点/参会人/记录人

二、议题与讨论
议题1：{标题}
（一）讨论要点
- xxx
（二）结论
- xxx
（三）行动项
| 行动事项 | 负责人 | 完成期限 | 交付物 | 状态 |

三、待确认事项
四、风险点
五、附件（录音文件）
```

## Prerequisites

```bash
pip install faster-whisper python-docx websockets
```

首次运行自动下载 Whisper small 模型 (~244MB)。

## 责任边界总结

| 功能       | 负责方 | 说明              |
| ---------- | ------ | ----------------- |
| 音频转写   | Skill  | Whisper 本地转写  |
| 文本分段   | Skill  | 时间戳/发言人解析 |
| 议题提取   | AI     | 语义理解          |
| 结论识别   | AI     | 语义理解          |
| 行动项抽取 | AI     | 语义理解          |
| 数据存储   | Skill  | JSON/DOCX 导出    |
| 格式排版   | Skill  | Word 文档生成     |



我想看这次会议开了几次会？
还有就是什么记录？
还有就是？
说白了还得搞一个数据库。
