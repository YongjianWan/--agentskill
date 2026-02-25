# ai-session-relay

**AI 驱动开发的会话接力框架**

> 解决核心问题：AI 没有跨会话记忆，但项目是连续的。

---

## 这是什么

`ai-session-relay` 是一套轻量级文档框架，让多个 AI 会话能够无缝接力开发同一个项目，而不丢失上下文。

**核心机制**：把"任务状态"和"项目上下文"结构化为文件，AI 每次进来读文件，而不是读聊天记录。

```
会话 1: AI 读文件 → 做任务 → 更新状态文件
会话 2: AI 读文件 → 继续上次的任务 → 更新状态文件
会话 N: ...
```

## 核心文件

| 文件 | 用途 |
|------|------|
| `PROJECT_CONTEXT.md` | AI 首读，30秒了解项目 |
| `SESSION_STATE.yaml` | 任务状态机，会话间接力的核心 |
| `CHANGELOG.md` | 版本历史 + TODO 池 |
| `docs/DOCUMENT_PROTOCOL.md` | 规则引擎，约束 AI 行为 |

## 快速开始

### 1. 复制模板到你的项目

```bash
# 复制所需文件
cp templates/PROJECT_CONTEXT.template.md  你的项目/PROJECT_CONTEXT.md
cp templates/SESSION_STATE.template.yaml  你的项目/SESSION_STATE.yaml
cp templates/CHANGELOG.template.md        你的项目/CHANGELOG.md
cp docs/DOCUMENT_PROTOCOL.md             你的项目/docs/DOCUMENT_PROTOCOL.md
```

### 2. 填写 PROJECT_CONTEXT.md

替换所有 `[...]` 占位符：
- 项目名称和用途
- 技术栈
- 当前开发阶段
- 主要开发规格文档路径

### 3. 初始化 SESSION_STATE.yaml

- 设置 `meta.version`
- 在 `tasks.next` 写入第一个任务
- 清空 `tasks.completed`

### 4. 告诉 AI 去读

在新会话开始时对 AI 说：
> "请先读 PROJECT_CONTEXT.md，然后读 SESSION_STATE.yaml，之后告诉我你打算做什么。"

## 和 .cursorrules 的区别

| | `.cursorrules` | ai-session-relay |
|--|----------------|-----------------|
| 状态管理 | ❌ 无 | ✅ SESSION_STATE |
| 多会话接力 | ❌ 靠人工 | ✅ 协议强制更新 |
| 文档膨胀控制 | ❌ 无 | ✅ 文档分级规则 |
| AI 工具依赖 | 仅 Cursor | 任何 AI（Claude/GPT/Gemini...） |

## 真实案例

`examples/lifeos/` 包含 LifeOS 项目的实际使用样本，这套框架正是在该项目的开发过程中提炼出来的。

## 文件结构

```
ai-session-relay/
├── README.md                        ← 本文件
├── docs/
│   └── DOCUMENT_PROTOCOL.md        ← 规则引擎（可直接使用）
├── templates/
│   ├── PROJECT_CONTEXT.template.md ← 填空模板
│   ├── SESSION_STATE.template.yaml ← 填空模板
│   └── CHANGELOG.template.md       ← 填空模板
└── examples/
    └── my-project/                 ← 示例（已填写的参考）
        ├── PROJECT_CONTEXT.md
        └── SESSION_STATE.yaml
```

## License

MIT
