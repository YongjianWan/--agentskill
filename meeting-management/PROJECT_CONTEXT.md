# PROJECT_CONTEXT
# AI首读文件 - 新会话必须先读此文件

```yaml
meta:
  project: "meeting-management"
  version: "0.9-beta"
  updated: "2026-02-25"
  status: active
  read_first: true
```

## 1. 这是什么项目

AI Agent 的会议管理 Skill，提供音频转写、会议纪要结构化存储、行动项追踪能力。

**定位**：供 AI 调用的能力模块（非直接用户产品）
```
用户 → AI 智能体 → 本 Skill
              ↓
        [转写/存储/导出]
```

## 2. 当前阶段

**Beta 测试阶段** — 核心功能完成，待集成验证

- 技术栈：Python 3.11 + faster-whisper + python-docx + websockets
- 主规格：见 `docs/SKILL.md`
- 协议规范：见 `docs/DOCUMENT_PROTOCOL.md`

## 3. 关键文件

| 文件 | 用途 |
|------|------|
| `docs/SKILL.md` | **主开发规格**：数据模型、接口定义、责任边界 |
| `src/meeting_skill.py` | Skill 核心实现（转写/存储/导出） |
| `scripts/websocket_server.py` | WebSocket 服务端（接收 Handy 转写流） |
| `SESSION_STATE.yaml` | 当前任务进度 |
| `CHANGELOG.md` | 版本历史 + TODO |

## 4. 技术栈速览

```
核心: Python 3.11+, dataclasses, pathlib
转写: faster-whisper (Whisper 模型)
文档: python-docx (Word 导出)
通信: websockets (实时转写流)
存储: JSON 文件 + 文件系统分级存储
```

## 5. 当前开发计划

| 里程碑 | 目标 | 状态 |
|--------|------|------|
| v0.8 | 核心 Skill 接口（转写/存储/导出） | ✅ 完成 |
| v0.9 | WebSocket 实时流 + 行动项台账 | ✅ 完成 |
| v1.0 | Handy 集成测试 + 文档完善 | ⏳ 进行中 |
| v1.1 | 数据库持久化（SQLite） | ⏳ 待开始 |

## 6. 目录结构

```
meeting-management/
├── src/
│   ├── meeting_skill.py      # Skill 核心实现
│   └── __init__.py
├── scripts/
│   ├── websocket_server.py   # WebSocket 服务端
│   ├── meeting_assistant.py  # AI 助手封装
│   └── *.py                  # 工具脚本
├── output/                   # 会议输出目录
│   ├── meetings/             # 按年月组织的会议记录
│   └── action_registry.json  # 全局行动项台账
├── docs/
│   ├── SKILL.md              # 主规格文档
│   ├── DOCUMENT_PROTOCOL.md  # AI 协作协议
│   └── *.md                  # 其他文档
├── templates/                # L1 文档模板
├── examples/                 # 示例项目
├── PROJECT_CONTEXT.md        # ← 本文件
├── SESSION_STATE.yaml        # 任务状态
├── CHANGELOG.md              # 变更日志
└── demo_full_flow.py         # 完整流程演示
```

## 7. 新会话必读顺序

按 `docs/DOCUMENT_PROTOCOL.md` 规定：

1. ✅ **本文件** (`PROJECT_CONTEXT.md`) — 项目定位、当前阶段
2. ⏩ **`SESSION_STATE.yaml`** — 找 `tasks.next`，确认本次工作内容
3. 📋 **`docs/SKILL.md`** — 按需读对应章节（接口/数据模型）

**会话结束时必须**：
- 更新 `SESSION_STATE.yaml`
- 新 TODO 追加到 `CHANGELOG.md`
- 提交 commit

---
# END_OF_CONTEXT - 请继续阅读 SESSION_STATE.yaml
