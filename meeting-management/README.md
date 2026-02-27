# Meeting Management - 会议管理后端服务

```yaml
role: 灵犀第二大脑 - "帮我听"声音模块（后端服务）
purpose: 实时音频转写 + AI会议纪要生成
usage: 浏览器 → WebSocket → 后端 → Whisper → DeepSeek API
version: 1.2.0
status: 生产就绪
```

# Identity & Communication

1. You are a pragmatic AI with Linus Torvalds' code philosophy and taste
2. Speak directly - say "stupid" when it's stupid, say "brilliant" when it's brilliant
3. No customer service tone. Treat me as an equal, push back when I'm wrong
4. Skip filler words, empty encouragement, and template phrases
5. Short responses when content is simple. Don't pad for format's sake

# Code Philosophy

6. Good taste first: eliminate edge cases rather than adding conditionals
7. Never over-engineer. "Good enough" that works beats "perfect" that's complex
8. Think before coding. Vibe coding = amateur hour
9. Max 3 levels of indentation. If you need more, fix the design
10. Trust internal code. Only add error handling where it actually fails

# Behavior Rules

11. Don't create new files when updating existing ones - modify in place
12. Commit messages: say what changed, not write an essay
13. Context-aware strictness: production = careful, scripts = fast and dirty
14. Never break existing interfaces without explicit instruction

# Forbidden

15. No "warm smile", "deep in thought" or other roleplay action descriptions
16. Don't escalate simple topics into life philosophy
17. Don't ask "what do you think?" at the end of every response
18. No bullet-point padding when one sentence suffices

## 架构概览

**当前架构（v1.2.0）**：浏览器直连自建转写后端

```
浏览器(MediaRecorder) ←──WebSocket──→ 声音模块后端
                │                          │
                │ 音频流(webm) ─────────> │ 1. 存audio.webm
                │ sequence按序处理        │ 2. Whisper转写
                │ <── 实时字幕 ────────── │ 3. 30秒触发一次
                │ <── 会议纪要 ────────── │ 4. 会后全量生成
```

**后端职责**:

- REST API: 会议CRUD、文件上传、历史查询、下载
- WebSocket: 实时音频流接收、转写结果推送
- 音频处理: Whisper转写、繁简转换、AI纪要生成
- 文件存储: WebM音频、DOCX/JSON纪要

---

## 快速开始

### 方式一：Docker 部署（推荐）

```bash
# 1. 克隆仓库
git clone <repository-url> meeting-management
cd meeting-management

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填写 DEEPSEEK_API_KEY

# 3. 启动服务
docker-compose up -d

# 4. 验证健康状态
curl http://localhost:8765/api/v1/system/health

# 5. 打开测试页面
test/real/index.html
```

### 方式二：本地部署

```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env

# 4. 启动服务
cd src
uvicorn main:app --host 0.0.0.0 --port 8765
```

---

## 核心功能

| 功能               | 说明                               | 状态      |
| ------------------ | ---------------------------------- | --------- |
| **实时录音** | 浏览器MediaRecorder采集音频        | ✅        |
| **语音转写** | faster-whisper small模型，中文识别 | ✅        |
| **繁简转换** | opencc集成，政府场景必备           | ✅        |
| **AI纪要**   | DeepSeek API，4种模板风格          | ✅        |
| **文件导出** | Word/JSON格式下载                  | ✅        |
| **文件上传** | 历史音频文件转写                   | ✅        |
| **健康检查** | 三级状态，组件详情                 | ✅ v1.2.0 |
| **Docker**   | 一键部署，数据持久化               | ✅ v1.2.0 |

---

## 技术栈

| 层级               | 技术                    | 说明                            |
| ------------------ | ----------------------- | ------------------------------- |
| **后端框架** | FastAPI                 | 异步、现代、自动生成Swagger文档 |
| **数据库**   | SQLite / HighGoDB       | 开发用SQLite，生产用瀚高        |
| **转写引擎** | faster-whisper          | small模型(~244MB)，支持CPU/GPU  |
| **繁简转换** | opencc-python           | 政府场景适配                    |
| **纪要生成** | DeepSeek API            | 4种模板风格                     |
| **文档生成** | python-docx             | Word文档导出                    |
| **部署**     | Docker + Docker Compose | 单机容器化部署                  |

---

## 目录结构

```
meeting-management/
├── src/                        # 核心源码
│   ├── main.py                # FastAPI 入口
│   ├── meeting_skill.py       # Skill 核心实现
│   ├── api/                   # API 路由
│   │   ├── meetings.py        # REST API
│   │   ├── websocket.py       # WebSocket 实时通信
│   │   ├── upload.py          # 文件上传
│   │   └── system.py          # 系统接口（健康检查）
│   ├── services/              # 服务层
│   │   ├── transcription_service.py  # 转写服务
│   │   └── websocket_manager.py      # 连接管理
│   └── models/                # 数据模型
├── Dockerfile                 # Docker 镜像定义
├── docker-compose.yml         # Docker Compose 配置
├── test/                      # 测试文件
│   └── real/
│       └── index.html         # 浏览器测试控制台
├── docs/                      # 文档
│   ├── BACKEND_API.md         # API 文档
│   ├── DEPLOYMENT.md          # 部署指南
│   └── DOCUMENT_AUDIT.md      # 文档评估报告
├── output/                    # 会议输出目录（自动创建）
├── data/                      # 数据库目录（自动创建）
├── .env.example               # 环境变量示例
└── README.md                  # 本文件
```

---

## API 接口

### REST API

| 方法 | 端点                                 | 说明                      |
| ---- | ------------------------------------ | ------------------------- |
| GET  | `/api/v1/system/health`            | 健康检查（v1.2.0 增强版） |
| GET  | `/api/v1/meetings`                 | 会议列表                  |
| GET  | `/api/v1/meetings/{id}`            | 会议详情                  |
| GET  | `/api/v1/meetings/{id}/download`   | 下载纪要（docx/json）     |
| POST | `/api/v1/meetings/{id}/regenerate` | 重新生成纪要              |
| POST | `/api/v1/upload/audio`             | 上传音频文件              |
| GET  | `/api/v1/templates`                | 获取模板列表              |

### WebSocket

```
ws://host:8765/api/v1/ws/meeting/{session_id}?user_id={user_id}
```

**协议**: start → chunk → end

```json
// 客户端发送
{"type": "start", "title": "会议标题"}
{"type": "chunk", "sequence": 1, "data": "base64..."}
{"type": "end"}

// 服务器推送
{"type": "started", "meeting_id": "xxx"}
{"type": "transcript", "text": "转写内容"}
{"type": "completed", "full_text": "...", "minutes_path": "..."}
```

完整 API 文档见: `http://localhost:8765/docs`

---

## 健康检查

```bash
curl http://localhost:8765/api/v1/system/health
```

**响应示例**:

```json
{
  "code": 0,
  "data": {
    "status": "ok",
    "version": "1.2.0",
    "uptime_seconds": 3600,
    "components": {
      "api": {"status": "ok"},
      "database": {"status": "ok"},
      "model": {
        "status": "ok",
        "name": "small",
        "loaded": true,
        "device": "cpu",
        "gpu_available": false
      },
      "disk": {
        "status": "ok",
        "total_gb": 100,
        "free_gb": 45,
        "usage_percent": 55
      },
      "websocket": {
        "active_sessions": 0
      }
    }
  }
}
```

**状态说明**:

- `ok` - 健康
- `degraded` - 降级（磁盘不足或模型未加载）
- `error` - 故障

---

## 配置说明

关键环境变量:

```bash
# 基础配置
PORT=8765
LOG_LEVEL=INFO

# 数据库
DATABASE_URL=sqlite:///data/meetings.db

# 转写配置
WHISPER_MODEL=small              # tiny/base/small/medium/large-v3
WHISPER_DEVICE=cpu               # cpu/cuda/auto
WHISPER_COMPUTE_TYPE=int8        # int8/float16/float32
WHISPER_LANGUAGE=zh              # zh/en/auto

# AI纪要配置
AI_PROVIDER=deepseek             # deepseek / company
DEEPSEEK_API_KEY=your_api_key
ENABLE_AI_MINUTES=true

# 政府场景
ENABLE_SIMPLIFIED_CHINESE=true   # 繁简转换开关
```

完整配置见 `.env.example`

---

## 测试

### 浏览器测试

打开 `test/real/index.html`:

- WebSocket 实时会议测试
- REST API 控制台（健康检查/会议列表/文件上传）

### 命令行测试

```bash
# 健康检查
curl http://localhost:8765/api/v1/system/health

# 获取模板列表
curl http://localhost:8765/api/v1/templates

# 上传音频文件
curl -X POST -F "file=@meeting.mp3" -F "title=测试会议" \
  http://localhost:8765/api/v1/upload/audio
```

---

## 状态

| 组件        | 状态 | 说明                   |
| ----------- | ---- | ---------------------- |
| REST API    | ✅   | 完整可用               |
| WebSocket   | ✅   | 实时通信               |
| Whisper转写 | ✅   | small模型，CPU/GPU支持 |
| AI纪要      | ✅   | DeepSeek API，4模板    |
| Docker部署  | ✅   | v1.2.0 新增            |
| 健康检查    | ✅   | v1.2.0 增强            |

---

## 文档索引

| 文档                                     | 说明                    |
| ---------------------------------------- | ----------------------- |
| [BACKEND_API.md](docs/BACKEND_API.md)       | API 详细规范            |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md)         | 部署指南（Docker/本地） |
| [CHANGELOG.md](CHANGELOG.md)                | 版本变更记录            |
| [DOCUMENT_AUDIT.md](docs/DOCUMENT_AUDIT.md) | 文档体系评估            |

---

**版本**: v1.2.0
**更新**: 2026-02-27
**状态**: 生产就绪，支持 Docker 部署
