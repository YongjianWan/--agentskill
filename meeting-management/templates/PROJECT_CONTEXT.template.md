# PROJECT_CONTEXT
# AI首读文件 - 新会话必须先读此文件
# 填写说明：替换所有 [...] 为你的项目信息

```yaml
meta:
  project: "[项目名称]"
  version: "[当前版本，如 1.0-dev]"
  updated: "[YYYY-MM-DD]"
  status: active
  read_first: true
```

## 1. 这是什么项目

[一句话描述项目是什么，做什么用的]

## 2. 当前阶段

**[阶段名称]**（如：MVP开发中 / v2.0 重构 / 稳定维护）

- 技术栈：[后端] + [前端] + [数据库]
- 开发规格：见 `[主规格文档文件名]`
- [其他关键信息]

## 3. 关键文件

| 文件 | 用途 |
|------|------|
| `[主规格文档].md` | **主开发规格**（AI 实现时的主要依据） |
| `SESSION_STATE.yaml` | 当前任务进度 |
| `docs/DOCUMENT_PROTOCOL.md` | AI 协作规范（必须遵守） |
| `CHANGELOG.md` | 版本历史 + TODO |

## 4. 技术栈速览

```
[填写你的技术栈架构，例如：]
后端: Python 3.11+, FastAPI, SQLAlchemy
前端: Vue 3, Vite
数据库: SQLite
测试: pytest
```

## 5. 当前开发计划

| 里程碑 | 目标 | 状态 |
|--------|------|------|
| [阶段1] | [目标] | ⏳ 待开始 |
| [阶段2] | [目标] | ⏳ |

## 6. 目录结构

```
[项目名]/
├── [核心目录]/
├── docs/
│   └── DOCUMENT_PROTOCOL.md
├── SESSION_STATE.yaml
├── PROJECT_CONTEXT.md     ← 本文件
└── CHANGELOG.md
```

## 7. 新会话必读顺序

> 以下顺序由 `docs/DOCUMENT_PROTOCOL.md` 规定，**所有 AI 会话必须遵守**。

1. ✅ 本文件 (`PROJECT_CONTEXT.md`) — 项目定位、当前阶段
2. ⏩ [`SESSION_STATE.yaml`](./SESSION_STATE.yaml) — 找 `tasks.next`，确认本次工作内容
3. 📋 `[主规格文档].md` — 按需读对应模块章节
4. [可选] 其他参考文档

**会话结束时必须**：更新 `SESSION_STATE.yaml` + 新 TODO 追加到 `CHANGELOG.md`。

---
# END_OF_CONTEXT - 请继续阅读 SESSION_STATE.yaml
