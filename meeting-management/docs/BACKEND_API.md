# 会议管理后端 API 规范

> **只负责后端！** 前端接口由后端定义，前端按此接入
> 版本: v1.2.0
> 更新: 2026-02-27
>
> **Phase 4 更新（2026-02-27）**：多模板支持、繁简转换、公司API框架、Docker部署、健康检查增强
>
> **⚠️ 架构变更（2026-02-26）**：已抛弃Handy，浏览器直连后端WebSocket
>
> - 新协议：`start` → `chunk` → `end`
> - 音频处理：后端接收音频块，本地Whisper转写

---

## 架构

```
┌─────────────┐      HTTP/REST       ┌─────────────┐
│   浏览器     │  <────────────────>  │   后端API    │
│  (前端不管)   │                    │   (你负责)    │
└─────────────┘      WebSocket       └─────────────┘
```

**后端职责**：

- REST API：会议管理、文件上传、历史查询
- WebSocket：实时音频流、实时字幕推送
- 音频处理：Whisper转写、AI纪要生成

---

## REST API

### 基础信息

- **Base URL**: `http://{host}:8765/api/v1`
- **Content-Type**: `application/json`
- **CORS**: 支持跨域

### 1. 会议管理

#### POST /meetings - 创建会议

> **⚠️ 状态：可选**
> 新架构下可直接通过 WebSocket `start` 消息创建会议。此API保留用于需要预创建会议场景。

创建新会议，获取session_id用于后续操作。

**Request**:

```json
{
  "title": "产品评审会",
  "participants": ["张三", "李四"],
  "location": "会议室A",
  "user_id": "user_001"
}
```

**Response**:

```json
{
  "code": 0,
  "data": {
    "session_id": "M20260225_143012_abc123",
    "title": "产品评审会",
    "status": "created",
    "created_at": "2026-02-25T14:30:12+08:00",
    "ws_url": "ws://localhost:8765/api/v1/ws/meeting/M20260225_143012_abc123?user_id=user_001"
  }
}
```

#### GET /meetings/{session_id} - 获取会议状态

> **状态：有效**

**Response**:

```json
{
  "code": 0,
  "data": {
    "session_id": "M20260225_143012_abc123",
    "title": "产品评审会",
    "status": "recording",
    "duration_ms": 123456,
    "start_time": "2026-02-25T14:30:12+08:00",
    "transcript_count": 42,
    "has_recording": true
  }
}
```

**Status枚举**: `created` | `recording` | `paused` | `processing` | `completed`

#### POST /meetings/{session_id}/start - 开始录音

> **⚠️ 状态：已弃用（WebSocket内处理）**
> 新架构下通过 WebSocket `start` 消息处理，此API保留但不再必需。

#### POST /meetings/{session_id}/pause - 暂停录音

> **状态：有效（保留功能）**

#### POST /meetings/{session_id}/resume - 恢复录音

> **状态：有效（保留功能）**

#### POST /meetings/{session_id}/end - 结束会议

> **状态：有效（v1.2.0 更新）**

结束会议并触发AI纪要生成，支持选择模板风格。

**Query参数**:

- `template_style`: 纪要模板风格（可选，默认`detailed`）
  - `detailed`: 详细版（默认）
  - `concise`: 简洁版
  - `action`: 行动项版
  - `executive`: 高管摘要版

**Response**:

```json
{
  "code": 0,
  "data": {
    "session_id": "M20260225_143012_abc123",
    "status": "processing",
    "message": "会议处理中，请稍后查询结果",
    "template_style": "action"
  }
}
```

**说明**:

- 从 recording/paused -> processing -> completed
- 异步执行：音频转写 -> AI生成 -> 保存结果
- 通过WebSocket `processing_completed` 通知或轮询查询结果

#### GET /meetings/{session_id}/result - 获取会议纪要

会议结束后查询生成结果。

**Response**:

```json
{
  "code": 0,
  "data": {
    "session_id": "M20260225_143012_abc123",
    "status": "completed",
    "title": "产品评审会",
    "duration_ms": 123456,
    "summary": "会议讨论了产品方案...",
    "topics": [
      {
        "title": "技术方案",
        "discussion_points": ["对比了方案A和B", "成本分析"],
        "conclusion": "采用方案B",
        "uncertain": []
      }
    ],
    "action_items": [
      {
        "action": "完成设计文档",
        "owner": "张三",
        "deadline": "2026-03-04",
        "status": "待处理"
      }
    ],
    "risks": [],
    "download_urls": {
      "docx": "/api/v1/meetings/M20260225_143012_abc123/download?format=docx",
      "json": "/api/v1/meetings/M20260225_143012_abc123/download?format=json"
    }
  }
}
```

---

### 2. 文件上传

#### POST /upload/audio - 上传录音文件

上传已有录音文件，后端异步转写生成纪要。

**Request**: `multipart/form-data`

```
file: [音频文件.mp3/wav/m4a]
title: "产品评审会"
user_id: "user_001"
```

**Response**:

```json
{
  "code": 0,
  "data": {
    "session_id": "M20260225_143012_abc123",
    "file_name": "meeting.mp3",
    "file_size": 1024567,
    "status": "uploaded",
    "message": "文件上传成功，正在处理..."
  }
}
```

**处理流程**:

1. 上传文件 → 返回session_id
2. 后端异步转写（Whisper）
3. AI生成纪要
4. 通过WebSocket或轮询通知前端完成

#### GET /upload/{session_id}/status - 查询处理状态

**Response**:

```json
{
  "code": 0,
  "data": {
    "session_id": "M20260225_143012_abc123",
    "status": "processing",
    "progress": 45,
    "stage": "transcribing"
  }
}
```

**Stage枚举**: `uploaded` | `transcribing` | `generating` | `completed` | `failed`

---

### 3. 历史查询

#### GET /meetings - 查询会议列表

**Query参数**:

- `user_id`: 用户ID（必填）
- `start_date`: 开始日期 `2026-02-01`
- `end_date`: 结束日期 `2026-02-28`
- `keyword`: 关键词搜索
- `page`: 页码，默认1
- `page_size`: 每页数量，默认20

**Response**:

```json
{
  "code": 0,
  "data": {
    "total": 45,
    "page": 1,
    "page_size": 20,
    "list": [
      {
        "session_id": "M20260225_143012_abc123",
        "title": "产品评审会",
        "date": "2026-02-25",
        "duration_ms": 123456,
        "status": "completed",
        "action_item_count": 3,
        "has_download": true
      }
    ]
  }
}
```

#### GET /meetings/{session_id}/transcript - 获取完整转写文本

**Response**:

```json
{
  "code": 0,
  "data": {
    "session_id": "M20260225_143012_abc123",
    "full_text": "[00:00] 张三: 我们开始开会吧...",
    "segments": [
      {
        "id": "seg_001",
        "text": "我们开始开会吧",
        "start_time_ms": 0,
        "end_time_ms": 3000,
        "speaker": "张三"
      }
    ],
    "language": "zh",
    "total_segments": 1
  }
}
```

#### PUT /meetings/{session_id}/transcript - 批量更新转写片段

> **状态：已实现 (v1.2.0)**

批量更新转写文本片段，用于人工校对后修正。

**Request**:

```json
{
  "segments": [
    {
      "id": "seg_001",
      "text": "修正后的文本",
      "speaker": "张三"
    }
  ]
}
```

**Response**:

```json
{
  "code": 0,
  "data": {
    "updated_count": 1,
    "message": "更新成功"
  }
}
```

#### PUT /meetings/{session_id}/transcript/{segment_id} - 更新单个转写片段

> **状态：已实现 (v1.2.0)**

更新单个转写片段的内容或发言人。

**Request**:

```json
{
  "text": "修正后的文本",
  "speaker": "张三"
}
```

**Response**:

```json
{
  "code": 0,
  "data": {
    "segment_id": "seg_001",
    "text": "修正后的文本",
    "speaker": "张三"
  }
}
```

#### POST /meetings/{session_id}/regenerate - 重新生成纪要

> **状态：已实现 (v1.2.0)**

使用不同模板风格重新生成会议纪要。

**Request**:

```json
{
  "template_style": "action"
}
```

**Response**:

```json
{
  "code": 0,
  "data": {
    "session_id": "M20260225_143012_abc123",
    "template_style": "action",
    "minutes": {
      "title": "产品评审会",
      "topics": [...],
      "action_items": [...]
    },
    "generated_at": "2026-02-26T14:30:00+08:00"
  }
}
```

**说明**:

- 适用于用户对首次生成结果不满意
- 保留历史版本（可通过多次调用对比）
- 需要会议已完成且有转写文本

**错误码**:
- `404`: 会议不存在
- `400`: 转写文本为空或模板风格无效

---

#### GET /templates - 获取纪要模板列表

> **状态：已实现 (v1.2.0)**

获取所有可用的纪要模板列表。

**Response**:

```json
{
  "code": 0,
  "data": [
    {
      "id": "detailed",
      "name": "详细版",
      "description": "完整记录讨论过程和决策依据，适合正式会议",
      "icon": "📋"
    },
    {
      "id": "concise",
      "name": "简洁版",
      "description": "高度概括，2分钟快速阅读，适合日常站会",
      "icon": "⚡"
    },
    {
      "id": "action",
      "name": "行动项版",
      "description": "以任务执行为核心，便于跟踪和跟进",
      "icon": "✅"
    },
    {
      "id": "executive",
      "name": "高管摘要版",
      "description": "聚焦决策、资源、风险，一页纸汇报",
      "icon": "📊"
    }
  ]
}
```

**说明**:

- 用于前端展示模板选择界面
- `icon` 字段为 emoji 图标，可直接展示

---

#### GET /meetings/{session_id}/download - 下载会议纪要

> **状态：已实现 (v1.1.1)**

下载会议纪要文件（Word 或 JSON 格式）。

**Query参数**:

- `format`: `docx` | `json`

**Response**: 
- `docx`: 文件流 (`application/vnd.openxmlformats-officedocument.wordprocessingml.document`)
- `json`: JSON 响应 (`application/json`)

**错误码**:
- `404`: 会议不存在或文件未生成
- `400`: 格式不支持（非 docx/json）
- `409`: 会议尚未完成，文件未生成

**示例**:
```bash
# 下载 Word 文档
curl -OJ "http://localhost:8765/api/v1/meetings/M20260226_143012_abc123/download?format=docx"

# 下载 JSON
curl "http://localhost:8765/api/v1/meetings/M20260226_143012_abc123/download?format=json"
```

---

### 4. 系统接口

#### GET /health - 健康检查

> **实际端点**: `/api/v1/health`  
> **版本**: v1.2.0 - 支持三级状态和多组件健康检测

**Response**:

```json
{
  "code": 0,
  "data": {
    "status": "ok",
    "version": "1.2.0",
    "uptime_seconds": 3600,
    "components": {
      "api": {
        "status": "ok"
      },
      "database": {
        "status": "ok"
      },
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
        "used_gb": 55,
        "usage_percent": 55
      },
      "websocket": {
        "active_sessions": 3
      }
    }
  }
}
```

**状态说明**:

| 状态 | 含义 | 触发条件 |
|------|------|----------|
| `ok` | 健康 | 所有组件正常 |
| `degraded` | 降级 | 磁盘空间不足(<1GB) 或 模型未加载 |
| `error` | 故障 | 关键组件不可用 |

**组件字段说明**:

| 组件 | 字段 | 说明 |
|------|------|------|
| `model` | `name` | 当前模型名称 (small/medium/large-v3) |
| | `loaded` | 模型是否已加载到内存 |
| | `device` | 运行设备 (cpu/cuda) |
| | `gpu_available` | GPU 是否可用 |
| `disk` | `total_gb` | 总空间 (GB) |
| | `free_gb` | 剩余空间 (GB) |
| | `usage_percent` | 使用率 (%) |
| `websocket` | `active_sessions` | 当前活跃会议数 |

**降级场景处理**:
- `disk` 为 `degraded`: 及时清理 output/ 目录，或扩容磁盘
- `model` 为 `degraded`: 首次启动模型加载中，等待 30-60 秒后重试
- 生产环境建议设置告警: `status != 'ok'` 时通知运维

---

## WebSocket 实时通信（v1.1 新协议）

### 连接地址

```
ws://{host}:8765/api/v1/ws/meeting/{session_id}?user_id={user_id}
```

**注意**：需要包含 `/api/v1` 前缀

### 连接流程（新协议）

```
1. 连接 WebSocket ws://host:8765/api/v1/ws/meeting/{session_id}?user_id=xxx
2. 发送 {"type": "start", "title": "会议标题"}  初始化会议
3. 循环发送音频块 {"type": "chunk", "sequence": n, "data": "base64..."}
4. 发送 {"type": "end"} 结束会议
5. 接收 {"type": "completed", ...} 获取纪要结果
```

### 上行消息（浏览器→后端）

#### 1. start - 开始会议

```json
{
  "type": "start",
  "title": "产品评审会"
}
```

**说明**：

- 创建会议目录和音频文件
- 初始化 Whisper 转写会话
- 第一个必须发送的消息

#### 2. chunk - 音频数据块

```json
{
  "type": "chunk",
  "sequence": 1,
  "data": "base64_encoded_webm_audio_data..."
}
```

**说明**：

- 音频格式：WebM/Opus（浏览器 MediaRecorder 默认输出）
- Base64 编码
- 后端每30秒触发一次转写

#### 3. end - 结束会议

```json
{
  "type": "end"
}
```

**说明**：

- 触发全量转写
- AI 生成会议纪要
- 导出 Word 文档
- 返回 `completed` 消息后关闭连接

#### 4. ping - 心跳

```json
{
  "type": "ping"
}
```

### 下行消息（后端→浏览器）

#### started - 会议已启动

```json
{
  "type": "started",
  "meeting_id": "WS_TEST_1234567890",
  "audio_path": "output/meetings/2026/02/WS_TEST_1234567890/audio.webm"
}
```

#### transcript - 实时转写结果

```json
{
  "type": "transcript",
  "text": "我们今天讨论产品方案",
  "sequence": 1,
  "is_final": false
}
```

**说明**：

- 每30秒推送一次（触发转写时）
- `is_final`: 当前固定为 `false`（实时结果）

#### completed - 会议完成

```json
{
  "type": "completed",
  "meeting_id": "WS_TEST_1234567890",
  "full_text": "完整的转写文本...",
  "minutes_path": "output/meetings/2026/02/WS_TEST_1234567890/minutes.docx",
  "chunk_count": 15
}
```

#### style_selected - 模板选择确认（Phase 4新增）

```json
{
  "type": "style_selected",
  "style": "executive",
  "message": "已选择模板: executive"
}
```

#### error - 错误

```json
{
  "type": "error",
  "code": "START_FAILED",
  "message": "启动会议失败: ...",
  "recoverable": false
}
```

**错误码**：

- `START_FAILED` - 启动失败
- `DECODE_ERROR` - 音频解码失败
- `CHUNK_ERROR` - 处理音频块失败
- `END_FAILED` - 结束会议失败
- `MESSAGE_TOO_LARGE` - 消息过大（>1MB）
- `INVALID_STYLE` - 无效的模板风格（Phase 4新增）

---

## 错误码

### HTTP状态码

| 码  | 说明                             |
| --- | -------------------------------- |
| 200 | 成功                             |
| 400 | 参数错误                         |
| 404 | 会议不存在                       |
| 409 | 状态冲突（如在recording时start） |
| 500 | 服务器内部错误                   |

### 业务错误码

| Code                     | 说明           | 处理建议         |
| ------------------------ | -------------- | ---------------- |
| `SESSION_NOT_FOUND`    | 会议不存在     | 检查session_id   |
| `SESSION_EXPIRED`      | 会议已过期     | 重新创建会议     |
| `INVALID_STATUS`       | 状态错误       | 检查当前状态     |
| `AUDIO_FORMAT_ERROR`   | 音频格式不支持 | 检查mime_type    |
| `PROCESSING_ERROR`     | 处理失败       | 重试或联系管理员 |
| `AI_GENERATION_FAILED` | AI生成失败     | 返回基础结构     |

---

## 状态机

```
                    ┌─────────────┐
         ┌─────────│   created   │◄────────┐
         │         └──────┬──────┘         │
         │                │ start          │ upload
         │                ▼                │
    pause│         ┌─────────────┐         │
         ├────────►│  recording  │─────────┤
         │         └──────┬──────┘         │
         │                │ pause          │ transcribing
         │                ▼                │
         │         ┌─────────────┐         │
         └────────►│   paused    │─────────┘
                   └─────────────┘  resume
                          │
                          │ end
                          ▼
                   ┌─────────────┐
              ┌───►│  processing │
              │    └──────┬──────┘
              │           │
         error│           │ complete
              │           ▼
              │    ┌─────────────┐
              └───►│  completed  │
                   └─────────────┘
```

---

## 数据模型

### Meeting 会议

```typescript
interface Meeting {
  session_id: string;        // 会议ID
  user_id: string;           // 用户ID
  title: string;             // 标题
  status: MeetingStatus;     // 状态
  start_time?: string;       // ISO8601
  end_time?: string;         // ISO8601
  duration_ms: number;       // 时长
  created_at: string;        // ISO8601
  updated_at: string;        // ISO8601
}
```

### Minutes 会议纪要

```typescript
interface Minutes {
  session_id: string;
  title: string;
  date: string;
  duration_ms: number;
  participants: string[];
  topics: Topic[];
  action_items: ActionItem[];
  risks: string[];
  summary?: string;
}

interface Topic {
  title: string;
  discussion_points: string[];
  conclusion?: string;
  uncertain?: string[];
}

interface ActionItem {
  action: string;
  owner?: string;
  deadline?: string;
  status: "待处理" | "进行中" | "已完成";
}
```

---

## 后端实现 checklist

- [x] REST API路由实现
- [x] WebSocket连接管理
- [x] 音频流接收与缓存（WebSocket chunk消息）
- [x] Whisper转写集成（faster-whisper small模型）
- [x] AI纪要生成集成（DeepSeek API）
- [x] 文件上传处理
- [x] 数据库存储（SQLite + 瀚高HighGoDB）
- [x] 状态机管理
- [x] 错误处理与日志
- [x] **会议纪要下载接口** (v1.1.1)
- [x] **REST API 异步 AI 生成** (v1.1.1)
- [x] **会议列表搜索（日期+关键词）** (v1.1.1)
- [x] **会议纪要模板列表接口** (v1.2.0)
- [x] **重新生成纪要接口（支持多模板）** (v1.2.0)
- [x] **繁简转换支持** (v1.2.0)
- [x] **公司API接入框架** (v1.2.0)
- [ ] 性能优化（音频队列/并发）- 未来
- [ ] 流式生成预览 - 暂缓（10秒等得起）

---

## 配置说明

### 环境变量

```bash
# === 基础配置 ===
PORT=8765
LOG_LEVEL=INFO

# === 转写配置 ===
WHISPER_MODEL=small              # tiny/base/small/medium/large-v3
WHISPER_DEVICE=cpu               # cpu/cuda/auto
WHISPER_COMPUTE_TYPE=int8        # int8/float16/float32
WHISPER_LANGUAGE=zh              # zh/en/auto

# === AI纪要配置 ===
AI_PROVIDER=deepseek             # deepseek / company
DEEPSEEK_API_KEY=xxx
ENABLE_AI_MINUTES=true

# === 政府场景配置（Phase 4）===
ENABLE_SIMPLIFIED_CHINESE=true   # 繁简转换开关

# === 公司自研API（预留）===
# COMPANY_API_KEY=xxx
# COMPANY_BASE_URL=https://api.your-company.com/v1
```

---

## 架构演进记录

### v1.1 → v1.2（2026-02-26）

**Phase 4 更新**：
- 多风格纪要模板（4种风格）
- 繁简转换支持（政府场景）
- 公司API接入框架（预留切换能力）
- 不接入通义千问（用户明确）

### v1.0 → v1.1（2026-02-26）

**变更原因**：
- Handy 编译复杂（需要 Rust/Vulkan/LLVM）
- 前端需要浏览器直连，不能依赖桌面客户端

**架构变化**：

| 方面 | v1.0（旧） | v1.1（新） |
|------|-----------|-----------|
| 音频输入 | Handy客户端（本地Whisper） | 浏览器MediaRecorder |
| 后端接收 | 转写后的文字 | 音频块（WebM） |
| WebSocket协议 | 单向推送文字 | 双向：start/chunk/end |
| 转写触发 | Handy控制 | 后端每30秒触发 |
| 纪要生成 | 原有逻辑 | 会后全量AI生成 |

**向前兼容**：
- REST API 保持兼容（部分标记为弃用）
- WebSocket URL 需要更新为 `/api/v1/ws/meeting/{session_id}`

---

**前端按此文档接入。**


---

## 前端对接示例

### JavaScript/TypeScript SDK

#### 完整示例：浏览器录音 + WebSocket 实时转写

```javascript
class MeetingClient {
  constructor(baseUrl, userId) {
    this.baseUrl = baseUrl;           // 如: 'http://172.20.3.70:8765'
    this.userId = userId;             // 如: 'user_001'
    this.ws = null;
    this.mediaRecorder = null;
    this.sessionId = null;
    this.chunkSequence = 0;
    this.onTranscript = null;         // 实时转写回调
    this.onCompleted = null;          // 会议完成回调
    this.onError = null;              // 错误回调
  }

  /**
   * 开始会议
   * @param {string} title - 会议标题
   */
  async startMeeting(title = '未命名会议') {
    // 生成唯一会议ID
    this.sessionId = `MT${Date.now()}`;
    
    // 构建 WebSocket URL
    const wsUrl = `${this.baseUrl.replace('http', 'ws')}/api/v1/ws/meeting/${this.sessionId}?user_id=${this.userId}`;
    
    // 连接 WebSocket
    this.ws = new WebSocket(wsUrl);
    
    return new Promise((resolve, reject) => {
      this.ws.onopen = () => {
        // 发送 start 消息
        this.ws.send(JSON.stringify({
          type: 'start',
          title: title,
          user_id: this.userId
        }));
      };
      
      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        this.handleMessage(data, resolve, reject);
      };
      
      this.ws.onerror = (error) => {
        if (this.onError) this.onError(error);
        reject(error);
      };
    });
  }

  /**
   * 处理 WebSocket 消息
   */
  handleMessage(data, resolve, reject) {
    switch (data.type) {
      case 'started':
        console.log('会议已启动:', data.meeting_id);
        this.startRecording();
        resolve(data);
        break;
        
      case 'transcript':
        console.log('实时转写:', data.text);
        if (this.onTranscript) this.onTranscript(data.text);
        break;
        
      case 'completed':
        console.log('会议完成:', data);
        this.stopRecording();
        if (this.onCompleted) this.onCompleted(data);
        break;
        
      case 'error':
        console.error('错误:', data.message);
        if (this.onError) this.onError(data);
        reject(data);
        break;
    }
  }

  /**
   * 开始录音
   */
  async startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      // 使用 MediaRecorder 录制音频 (WebM/Opus 格式)
      this.mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });
      
      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0 && this.ws?.readyState === WebSocket.OPEN) {
          this.sendAudioChunk(event.data);
        }
      };
      
      // 每 1000ms 发送一个音频块
      this.mediaRecorder.start(1000);
      
    } catch (error) {
      console.error('录音失败:', error);
      if (this.onError) this.onError(error);
    }
  }

  /**
   * 发送音频块
   */
  async sendAudioChunk(blob) {
    const reader = new FileReader();
    reader.onloadend = () => {
      const base64 = reader.result.split(',')[1];
      this.ws.send(JSON.stringify({
        type: 'chunk',
        sequence: this.chunkSequence++,
        data: base64
      }));
    };
    reader.readAsDataURL(blob);
  }

  /**
   * 结束会议
   */
  endMeeting() {
    if (this.mediaRecorder?.state !== 'inactive') {
      this.mediaRecorder?.stop();
    }
    
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'end' }));
    }
  }

  /**
   * 停止录音
   */
  stopRecording() {
    if (this.mediaRecorder?.state !== 'inactive') {
      this.mediaRecorder?.stop();
      this.mediaRecorder?.stream.getTracks().forEach(track => track.stop());
    }
  }

  /**
   * 关闭连接
   */
  disconnect() {
    this.stopRecording();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

// ============ 使用示例 ============

async function main() {
  // 创建客户端实例 (替换为你的服务器地址)
  const client = new MeetingClient('http://172.20.3.70:8765', 'user_test');
  
  // 设置回调
  client.onTranscript = (text) => {
    document.getElementById('transcript').innerText += text + '\n';
  };
  
  client.onCompleted = (data) => {
    console.log('会议纪要:', data);
    alert(`会议完成！\n转写长度: ${data.full_text?.length || 0} 字符\n纪要文件: ${data.minutes_path}`);
  };
  
  client.onError = (error) => {
    console.error('错误:', error);
    alert('会议出错: ' + (error.message || JSON.stringify(error)));
  };
  
  // 开始会议
  try {
    await client.startMeeting('产品评审会');
    console.log('会议开始成功');
    
    // 30秒后自动结束（实际场景由用户点击结束）
    setTimeout(() => {
      client.endMeeting();
    }, 30000);
    
  } catch (error) {
    console.error('启动失败:', error);
  }
}

// 启动
main();
```

#### REST API 调用示例

```javascript
// 获取会议列表
async function getMeetings(userId) {
  const response = await fetch(
    `http://172.20.3.70:8765/api/v1/meetings?user_id=${userId}`
  );
  return await response.json();
}

// 获取会议详情
async function getMeeting(sessionId, userId) {
  const response = await fetch(
    `http://172.20.3.70:8765/api/v1/meetings/${sessionId}?user_id=${userId}`
  );
  return await response.json();
}

// 下载会议纪要
function downloadMinutes(sessionId, format = 'docx') {
  window.open(
    `http://172.20.3.70:8765/api/v1/meetings/${sessionId}/download?format=${format}`,
    '_blank'
  );
}

// 上传音频文件
async function uploadAudio(file, title, userId) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('title', title);
  formData.append('user_id', userId);
  
  const response = await fetch(
    'http://172.20.3.70:8765/api/v1/upload/audio',
    {
      method: 'POST',
      body: formData
    }
  );
  return await response.json();
}
```

---

## 快速开始

### 1. 启动后端服务

```bash
cd meeting-management/src
python -m uvicorn main:app --host 0.0.0.0 --port 8765
```

### 2. 浏览器打开测试页面

```
http://localhost:8765/static/index.html
```

或直接打开 `test/real/index.html`

### 3. 验证 API

```bash
# 健康检查
curl http://localhost:8765/api/v1/system/health

# 获取 API 文档
open http://localhost:8765/docs
```

---

## 注意事项

1. **浏览器兼容性**：需要支持 MediaRecorder API（Chrome 57+, Firefox 25+, Edge 79+）
2. **HTTPS 要求**：如果部署到公网，必须使用 HTTPS，否则无法获取麦克风权限
3. **音频格式**：默认使用 WebM/Opus，如需其他格式请联系后端
4. **chunk 大小**：建议 1000ms 发送一次，过大可能导致消息超限

---

**前端按此文档接入。**
