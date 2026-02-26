# 会议管理后端 API 规范

> **只负责后端！** 前端接口由后端定义，前端按此接入  
> 版本: v1.0  
> 更新: 2026-02-25

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
    "ws_url": "ws://localhost:8765/ws/meeting/M20260225_143012_abc123"
  }
}
```

#### GET /meetings/{session_id} - 获取会议状态

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

通知后端开始接收音频流（通过WebSocket）。

**Response**:
```json
{
  "code": 0,
  "data": {
    "session_id": "M20260225_143012_abc123",
    "status": "recording",
    "started_at": "2026-02-25T14:30:12+08:00"
  }
}
```

#### POST /meetings/{session_id}/pause - 暂停录音

**Response**:
```json
{
  "code": 0,
  "data": {
    "session_id": "M20260225_143012_abc123",
    "status": "paused",
    "duration_ms": 60000
  }
}
```

#### POST /meetings/{session_id}/resume - 恢复录音

同上，status变为`recording`。

#### POST /meetings/{session_id}/end - 结束会议

通知后端停止接收音频，开始生成纪要。

**Response**:
```json
{
  "code": 0,
  "data": {
    "session_id": "M20260225_143012_abc123",
    "status": "processing",
    "duration_ms": 123456,
    "message": "正在生成会议纪要..."
  }
}
```

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
        "speaker_id": null
      }
    ]
  }
}
```

#### GET /meetings/{session_id}/download - 下载会议纪要

**Query参数**:
- `format`: `docx` | `json`

**Response**: 文件流

---

### 4. 系统接口

#### GET /health - 健康检查

**Response**:
```json
{
  "code": 0,
  "data": {
    "status": "healthy",
    "version": "1.0.0",
    "active_sessions": 3,
    "whisper_status": "ready"
  }
}
```

---

## WebSocket 实时通信

### 连接地址

```
ws://{host}:8765/ws/meeting/{session_id}?user_id={user_id}
```

### 连接流程

```
1. POST /meetings 创建会议，获取session_id
2. 连接 WebSocket ws://host/ws/meeting/{session_id}
3. POST /meetings/{session_id}/start 开始录音
4. 浏览器 → 发送音频流（二进制或Base64）
5. 后端 → 推送实时转写结果
6. POST /meetings/{session_id}/end 结束
7. 后端 → 推送会议纪要
```

### 上行消息（浏览器→后端）

#### 音频数据

**方式A：Base64 JSON（推荐，兼容性好）**
```json
{
  "type": "audio",
  "seq": 123,
  "timestamp_ms": 15000,
  "data": "base64_encoded_audio_data...",
  "mime_type": "audio/webm;codecs=opus"
}
```

**方式B：二进制帧（性能更好）**
- 直接发送WebM/Opus二进制数据
- 元数据通过控制消息发送

#### 控制指令

```json
{
  "type": "ping"
}
```

### 下行消息（后端→浏览器）

#### transcript - 实时转写

```json
{
  "type": "transcript",
  "segment_id": "seg_001",
  "text": "我们今天讨论产品方案",
  "timestamp_ms": 15234,
  "is_final": true
}
```

**is_final**: 
- `false` = 中间结果（可能变化）
- `true` = 确定结果（不会变化）

#### topic - 议题识别

```json
{
  "type": "topic",
  "topic_id": "topic_001",
  "title": "产品方案讨论",
  "start_time_ms": 15234,
  "confidence": 0.85
}
```

#### action_item - 行动项

```json
{
  "type": "action_item",
  "action_id": "act_001",
  "action": "完成设计文档",
  "owner": "张三",
  "deadline": "2026-03-04",
  "source_text": "张三负责下周五前完成设计文档"
}
```

#### status - 状态变更

```json
{
  "type": "status",
  "status": "recording",
  "duration_ms": 123456,
  "transcript_count": 42
}
```

#### result - 会议纪要完成

```json
{
  "type": "result",
  "success": true,
  "minutes": {
    "title": "产品评审会",
    "topics": [...],
    "action_items": [...]
  }
}
```

#### error - 错误

```json
{
  "type": "error",
  "code": "AUDIO_DECODE_ERROR",
  "message": "音频解码失败",
  "recoverable": true
}
```

---

## 错误码

### HTTP状态码

| 码 | 说明 |
|----|------|
| 200 | 成功 |
| 400 | 参数错误 |
| 404 | 会议不存在 |
| 409 | 状态冲突（如在recording时start）|
| 500 | 服务器内部错误 |

### 业务错误码

| Code | 说明 | 处理建议 |
|------|------|----------|
| `SESSION_NOT_FOUND` | 会议不存在 | 检查session_id |
| `SESSION_EXPIRED` | 会议已过期 | 重新创建会议 |
| `INVALID_STATUS` | 状态错误 | 检查当前状态 |
| `AUDIO_FORMAT_ERROR` | 音频格式不支持 | 检查mime_type |
| `PROCESSING_ERROR` | 处理失败 | 重试或联系管理员 |
| `AI_GENERATION_FAILED` | AI生成失败 | 返回基础结构 |

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

- [ ] REST API路由实现
- [ ] WebSocket连接管理
- [ ] 音频流接收与缓存
- [ ] Whisper转写集成
- [ ] AI纪要生成集成
- [ ] 文件上传处理
- [ ] 数据库存储（会议/转写/纪要）
- [ ] 状态机管理
- [ ] 错误处理与日志
- [ ] 性能优化（音频队列/并发）

---

**只负责后端！前端按此文档接入。**
