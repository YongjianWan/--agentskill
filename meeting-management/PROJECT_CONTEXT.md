# PROJECT_CONTEXT

# AI首读文件 - 新会话必须先读此文件

```yaml
meta:
  project: "meeting-management"
  version: "1.0-beta"
  updated: "2026-02-26"
  status: active
  read_first: true
```

## 1. 这是什么项目

**灵犀第二大脑 - "帮我听" 声音模块（后端服务）**

> **⚠️ 只负责后端！前端按API文档接入，后端不管前端实现**

### 架构演进

**当前架构（2026-02-26 重构）**：浏览器直连自建转写后端

```
浏览器(MediaRecorder) ←──WebSocket──→ 声音模块后端
                │                          │
                │ 音频流(webm) ─────────> │ 1. 存audio.webm
                │ sequence按序处理        │ 2. Whisper转写
                │ <── 实时字幕 ────────── │ 3. 30秒触发一次
                │ <── 会议纪要 ────────── │ 4. 会后全量生成
```

**历史架构（已废弃）**：Handy转写 → 后端接收文字
```
Handy客户端(本地Whisper) ──WebSocket──→ 后端只收文字
```

### 后端职责

| 模块 | 功能 | 接口类型 |
|------|------|----------|
| **REST API** | 会议CRUD、历史查询、下载 | HTTP |
| **WebSocket** | 接收音频流、推送转写结果 | WS |
| **音频处理** | 存webm、Whisper转写、临时文件给模型 | 内部 |
| **纪要生成** | 会后全量AI生成、导出Word | 内部 |

**前端职责（不管）**：浏览器录音(MediaRecorder)、界面展示、用户交互

## 2. 核心原则与技术选型（已确认）

| 原则/选型 | 说明 |
|----------|------|
| **后端框架** | FastAPI（异步、现代、自动生成Swagger文档） |
| **数据库** | SQLite（开发）+ 瀚高HighGoDB（生产） |
| **音频输入** | WebM/Opus（浏览器MediaRecorder默认输出） |
| **转写引擎** | faster-whisper (small模型，~244MB) |
| **转写触发** | **每30秒触发一次**（不按块数，块大小不固定） |
| **纪要生成** | **会议结束后全量生成**（非实时增量） |
| **文件存储** | `output/meetings/YYYY/MM/{meeting_id}/audio.webm` |
| **通信方式** | REST API + WebSocket |
| **旧代码处理** | **直接删除，不留legacy** |

### 音频处理流程

```
浏览器 ──chunk──> 后端 ──追加──> audio.webm
                    │
                    └─每30秒─> 读取片段 ──> 临时文件 ──> Whisper ──> transcripts表
                    │
                    └─end──> 全量转写剩余 ──> AI生成纪要 ──> minutes.docx
```

## 3. 当前阶段

**架构重构期** — 抛弃Handy，浏览器直连自建转写后端（2026-02-26）

| Phase | 目标 | 状态 | 关键交付 |
|-------|------|------|----------|
| Phase 1 | REST API骨架 | ✅ 完成 | FastAPI + 瀚高/双数据库 + 会议CRUD |
| Phase 2 | WebSocket实时转写 | ✅ 完成 | 音频流接收 + 缓存合并 + 实时字幕 |
| **Phase 3** | **架构重构：自建转写后端** | 🔄 **进行中** | **浏览器音频流 → Whisper → 纪要** |
| Phase 4 | AI纪要生成 | ⏳ 待开始 | 会后全量生成 |
| Phase 5 | 历史检索完善 | ⏳ 待开始 | 搜索、筛选、导出 |
| Phase 6 | 测试文档 | ⏳ 待开始 | 完整测试 |

### 重构任务清单

1. **数据库扩展** - 新增transcripts/topics/action_items表
2. **meeting_skill改造** - MeetingSessionManager + transcribe_bytes
3. **WebSocket简化** - start/chunk/end协议，30秒触发转写
4. **端到端测试** - Python模拟音频流客户端
5. **清理旧代码** - 删除Handy相关脚本

## 4. 关键文件

| 文件 | 用途 |
|------|------|
| `SESSION_STATE.yaml` | **当前任务状态（先看这个）** |
| `src/api/websocket.py` | WebSocket端点（需改造） |
| `src/services/websocket_manager.py` | 连接管理（需扩展音频文件句柄） |
| `src/services/transcription_service.py` | 转写服务（需支持bytes直接转写） |
| `src/meeting_skill.py` | Skill核心（需新增流式处理方法） |
| `src/models/meeting.py` | 数据模型（需扩展表结构） |
| `src/database/connection.py` | 数据库连接（无需改动） |

## 5. 目录结构

```
meeting-management/
├── src/
│   ├── main.py               # FastAPI 应用入口
│   ├── meeting_skill.py      # Skill 核心实现（需新增流式处理）
│   ├── logger_config.py      # 日志配置
│   ├── utils.py              # 工具函数
│   ├── api/
│   │   ├── meetings.py       # 会议管理 REST API
│   │   ├── websocket.py      # WebSocket 实时音频流（需改造）
│   │   ├── upload.py         # 文件上传
│   │   └── system.py         # 系统接口
│   ├── services/
│   │   ├── websocket_manager.py    # WebSocket连接管理（需扩展）
│   │   └── transcription_service.py # 转写服务（需支持bytes）
│   ├── models/
│   │   └── meeting.py        # SQLAlchemy模型（需扩展表结构）
│   └── database/
│       └── connection.py     # 数据库连接管理
├── scripts/                  # 工具脚本（删除Handy相关）
├── output/                   # 会议输出目录
│   └── meetings/YYYY/MM/{id}/
│       ├── audio.webm        # 音频文件（流式追加）
│       └── minutes.docx      # Word纪要
├── test/                     # 测试脚本
├── docs/
│   ├── SKILL.md              # 主开发规格
│   ├── DOCUMENT_PROTOCOL.md  # AI 协作协议
│   └── BACKEND_API.md        # 后端API文档
├── PROJECT_CONTEXT.md        # ← 本文件
├── SESSION_STATE.yaml        # 任务状态
└── CHANGELOG.md              # 变更日志
```

## 6. 新会话必读顺序

按 `docs/DOCUMENT_PROTOCOL.md` 规定：

1. ✅ **本文件** (`PROJECT_CONTEXT.md`) — 项目定位、当前阶段
2. ⏩ **`SESSION_STATE.yaml`** — 找 `tasks.next`，确认本次工作内容
3. 📋 **`docs/SKILL.md`** — 按需读对应章节（接口/数据模型）

**会话结束时必须**：

- 更新 `SESSION_STATE.yaml`
- 新 TODO 追加到 `CHANGELOG.md`
- 提交 commit

## 7. 架构决策记录

### 2026-02-26 架构重构决策

| 决策项 | 选择 | 原因 |
|--------|------|------|
| 音频源 | 浏览器MediaRecorder | 抛弃Handy，减少依赖 |
| 接收数据 | 音频块(bytes) | 后端自己转写，控制力强 |
| 存储格式 | webm（原样存储） | 不做实时转码，够用就行 |
| 转写触发 | 每30秒一次 | 按时间稳定，块大小不固定 |
| 纪要生成 | 会后全量 | 实时增量复杂度不值得 |
| 旧代码 | 直接删除 | 不留legacy，代码即负债 |

### 2026-02-25 前期决策（仍有效）

- **定位**: 灵犀"帮我听"声音模块，后端独立服务
- **边界**: 只负责后端，前端按API接入
- **通信**: REST API + WebSocket
- **AI角色**: AI处理语义、生成纪要

---

# END_OF_CONTEXT - 请继续阅读 SESSION_STATE.yaml
