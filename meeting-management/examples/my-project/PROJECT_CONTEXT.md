# PROJECT_CONTEXT
# AI首读文件 - 新会话必须先读此文件

```yaml
meta:
  project: "my-project"
  version: "1.0-dev"
  updated: "2026-02-22"
  status: active
  read_first: true
```

## 1. 这是什么项目

一个个人任务管理 CLI 工具，用命令行管理每日任务和项目进度。

## 2. 当前阶段

**MVP 开发中**（Target: 7天完成核心功能）

- 技术栈：Python 3.11 + SQLite + Click CLI
- 开发规格：见 `SPEC.md`（主规格文档）

## 3. 关键文件

| 文件 | 用途 |
|------|------|
| `SPEC.md` | **主开发规格**（AI 实现时的主要依据） |
| `SESSION_STATE.yaml` | 当前任务进度 |
| `docs/DOCUMENT_PROTOCOL.md` | AI 协作规范 |

## 4. 7天计划

| Day | 目标 | 状态 |
|-----|------|------|
| Day 1 | CLI 脚手架 + 数据库初始化 | ✅ 完成 |
| Day 2 | 任务 CRUD 命令 | ⏳ 进行中 |
| Day 3 | 项目管理命令 | ⏳ |
| Day 4-7 | 报告、搜索、polish | ⏳ |

## 7. 新会话必读顺序

1. ✅ 本文件
2. ⏩ `SESSION_STATE.yaml` — 找 `tasks.next`
3. 📋 `SPEC.md` — 按需读对应章节

**会话结束时必须**：更新 `SESSION_STATE.yaml` + 新 TODO 追加到 `CHANGELOG.md`。

---
# END_OF_CONTEXT
