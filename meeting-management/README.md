# Meeting Management - AI Agent Skill

```yaml
role: AI Agent Skill
purpose: Meeting transcription + structured minutes storage
usage: User -> AI Agent -> This Skill
```

## Quick Start for AI

```python
# 1. Transcribe audio
from meeting_skill import transcribe, create_meeting_skeleton, save_meeting
from meeting_skill import Meeting, Topic, ActionItem, PolicyRef, EnterpriseRef, ProjectRef

result = transcribe("meeting.mp3")
# Returns: {segments, full_text, participants, duration, model_used}

# 2. Create skeleton (Skill) -> AI fills content
meeting = create_meeting_skeleton(
    transcription=result["full_text"],
    title="AI-recognized title",
    participants=result["participants"]
)

# 3. AI fills structured content
meeting.title = "Product Review Meeting"
meeting.topics = [
    Topic(
        title="Technical Solution",
        discussion_points=["Compared A and B", "B is cheaper"],
        conclusion="Adopt solution B",
        uncertain=["Implementation details pending"],
        action_items=[
            ActionItem(
                action="Prepare technical document",
                owner="Zhang San",
                deadline="2026-03-05",
                related_project=ProjectRef(project_id="PROJ-001", milestone="M1")
            )
        ]
    )
]
meeting.risks = ["Tight schedule may affect quality"]
meeting.pending_confirmations = ["Third-party API cost pending"]

# 4. Save
files = save_meeting(meeting, output_dir="./output")
# Returns: {json, docx, meeting_dir}
```

## Data Model

### Meeting

```python
@dataclass
class Meeting:
    # Core (AI fills)
    title: str
    date: str
    participants: List[str]
    topics: List[Topic]
    risks: List[str]
    pending_confirmations: List[str]
  
    # Entity linking (AI recognizes from content)
    policy_refs: List[PolicyRef]       # Policy references
    enterprise_refs: List[EnterpriseRef]  # Enterprise mentions
    project_refs: List[ProjectRef]     # Project associations
  
    # Auto-generated (Skill)
    id: str  # M{YYYYMMDD}_{HHMMSS}_{hash6}
    version: int = 1
    status: str = "draft"  # draft/final/archived
```

### Topic

```python
@dataclass
class Topic:
    title: str                          # AI extracts
    discussion_points: List[str]        # AI extracts
    conclusion: str = ""                # AI extracts
    uncertain: List[str] = []           # AI marks uncertainty
    action_items: List[ActionItem] = [] # AI extracts
```

### ActionItem

```python
@dataclass
class ActionItem:
    action: str                         # AI extracts
    owner: str                          # AI recognizes
    deadline: str                       # AI extracts date
    deliverable: str = ""               # AI infers
    status: str = "待处理"
  
    # Optional entity linking
    related_policy: Optional[PolicyRef]
    related_enterprise: Optional[EnterpriseRef]
    related_project: Optional[ProjectRef]
```

### Entity References (Future Integration)

```python
@dataclass
class PolicyRef:
    policy_id: str = ""           # e.g., "P2024-001"
    clause_ref: str = ""          # e.g., "Article 3, Section 2"
    check_required: bool = False

@dataclass
class EnterpriseRef:
    enterprise_id: str = ""       # Enterprise ID
    cooperation_item: str = ""    # Cooperation description
    contact_person: str = ""      # Contact person
    contact_permission: str = ""  # Permission level

@dataclass
class ProjectRef:
    project_id: str = ""          # Project ID
    milestone: str = ""           # Affected milestone
    change_point: str = ""        # Change description
```

## Core Functions

### transcribe(audio_path, model="small", language="zh")

```python
{
    "segments": [{"timestamp": "00:00:01", "speaker": "...", "text": "..."}],
    "full_text": "[00:00:01] Speaker: text...",
    "participants": ["Speaker1", "Speaker2"],
    "duration": 1800,
    "model_used": "small"
}
```

### create_meeting_skeleton(transcription, **kwargs)

- Parses transcription text
- Creates empty Meeting structure
- AI fills topics, risks, action_items

### save_meeting(meeting, output_dir="./output")

- Saves JSON + DOCX + latest symlink
- Creates action registry
- Returns file paths

### query_meetings(output_dir, date_range, keywords)

- Query historical meetings
- Returns list of Meeting dicts

## Workflow

```
User Request -> AI Agent -> Skill API
     |                           |
     |                           v
     |              transcribe() / create_meeting_skeleton()
     |                           |
     |                           v
     |              AI fills: topics, conclusions, action_items
     |                           |
     |                           v
     |              save_meeting()
     |                           |
     v                           v
  Response <--------------- File paths + summary
```

## Recording Options

### Option A: Meeting Assistant (Recommended)

```bash
python scripts/meeting_assistant.py
# > start "Meeting Title"  # Start recording
# > stop                   # Stop + auto-generate minutes
```

### Option B: Process Existing Audio

```bash
python scripts/meeting_assistant.py quick meeting.wav --title "Review"
```

### Option C: WebSocket (Requires Handy Client)

```bash
python scripts/websocket_server.py --port 8765
# Handy client streams transcription via WebSocket
```

## Output Format

### JSON Structure

```json
{
  "id": "M20260225_143012_a1b2c3",
  "title": "Product Review",
  "date": "2026-02-25",
  "participants": ["Zhang San", "Li Si"],
  "topics": [{
    "title": "Technical Solution",
    "discussion_points": ["Compared A and B"],
    "conclusion": "Adopt B",
    "action_items": [{
      "action": "Prepare document",
      "owner": "Zhang San",
      "deadline": "2026-03-05"
    }]
  }],
  "risks": ["Schedule risk"],
  "policy_refs": [],
  "enterprise_refs": [],
  "project_refs": [],
  "status": "final"
}
```

### DOCX Structure

```
会议纪要：{title}

一、会议基本信息
主题/时间/地点/参会人/记录人

二、议题与讨论
议题1：{title}
（一）讨论要点
- xxx
（二）结论
- xxx
（三）行动项
| 行动事项 | 负责人 | 完成期限 | 交付物 | 状态 |

三、待确认事项
四、风险点
五、附件
```

## Dependencies

```bash
pip install faster-whisper python-docx pyaudio websockets
```

## Architecture

| Layer        | Responsibility              | This Skill | AI Agent |
| ------------ | --------------------------- | ---------- | -------- |
| Data         | Transcription, storage, I/O | ✅         | ❌       |
| Intelligence | Understanding, extraction   | ❌         | ✅       |

**Rule**: Skill provides scaffolding, AI fills content.

## Status

| Component                 | Status | Note                        |
| ------------------------- | ------ | --------------------------- |
| transcribe()              | ✅     | Whisper small model         |
| create_meeting_skeleton() | ✅     | Creates empty structure     |
| save_meeting()            | ✅     | JSON + DOCX output          |
| Entity linking            | ✅     | Fields reserved for future  |
| Handy client              | ❌     | Blocked: CMake + Vulkan SDK |

## File Structure

```
src/meeting_skill.py          # Core API
scripts/meeting_assistant.py  # CLI entry point
scripts/recorder.py           # Audio recording
scripts/websocket_server.py   # WebSocket server
docs/online_meeting_guide.md  # Virtual audio setup
tast/                         # 测试文件
```
