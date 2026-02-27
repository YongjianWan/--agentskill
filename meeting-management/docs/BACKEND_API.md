# 会议管理后端 API 规范（简化版）

> 版本: v1.2.0 | 更新: 2026-02-27
> 
> 本文档只包含**前端必须实现**的核心接口，可选接口标记为⭐可选。

---

## 核心API速查

| 优先级 | 接口 | 用途 |
|:------:|------|------|
| ⭐⭐⭐ | **WebSocket** | 录音+转写+结束（唯一必须） |
| ⭐⭐⭐ | GET /meetings/{id}/result | 获取会议纪要 |
| ⭐⭐⭐ | GET /meetings/{id}/download | 下载Word/JSON |
| ⭐⭐ | GET /meetings | 会议列表 |
| ⭐ | GET /templates | 模板列表（可选） |
| ⭐ | POST /upload/audio | 文件上传（可选） |

---

## WebSocket 协议（核心）

### 连接地址
```
ws://{host}:8765/api/v1/ws/meeting/{meeting_id}?user_id={user_id}
```

### 消息流程
```
前端 → 后端: {type: "start", title: "会议标题"}
后端 → 前端: {type: "started", meeting_id: "..."}
前端 → 后端: {type: "chunk", sequence: 0, data: "base64..."}  (每秒发送)
后端 → 前端: {type: "transcript", text: "..."}  (每30秒)
前端 → 后端: {type: "end"}
后端 → 前端: {type: "completed", full_text: "...", minutes_path: "..."}
```

### 上行消息（前端→后端）

**start** - 开始会议
```json
{"type": "start", "title": "产品评审会"}
```

**chunk** - 音频数据
```json
{"type": "chunk", "sequence": 0, "data": "base64音频数据"}
```

**end** - 结束会议
```json
{"type": "end"}
```

### 下行消息（后端→前端）

**started** - 会议已开始
```json
{"type": "started", "meeting_id": "M20260227_123456"}
```

**transcript** - 实时转写
```json
{"type": "transcript", "text": "转写文本", "sequence": 5}
```

**completed** - 会议完成
```json
{
  "type": "completed",
  "meeting_id": "M20260227_123456",
  "full_text": "完整转写文本...",
  "minutes_path": "output/.../minutes_v1.docx",
  "chunk_count": 45,
  "ai_success": true,
  "fallback_reason": null
}
```

**error** - 错误
```json
{"type": "error", "code": "END_FAILED", "message": "错误描述"}
```

---

## REST API

### GET /meetings/{session_id}/result

> 优先级: ⭐⭐⭐ **必须**

获取会议纪要。

**Response:**
```json
{
  "code": 0,
  "data": {
    "session_id": "M20260227_123456",
    "title": "产品评审会",
    "full_text": "[00:00] 张三: 我们开始开会吧...",
    "minutes": {
      "topics": [{
        "title": "项目进度",
        "discussion_points": ["完成了80%"],
        "action_items": [{"action": "提交代码", "owner": "李四"}]
      }]
    }
  }
}
```

---

### GET /meetings/{session_id}/download

> 优先级: ⭐⭐⭐ **必须**

下载纪要文件。

**Query:** `?format=docx` 或 `?format=json`

**Response:** 文件流

---

### GET /meetings

> 优先级: ⭐⭐ **推荐**

会议列表。

**Query:** `?user_id=xxx&page=1&page_size=20`

**Response:**
```json
{
  "code": 0,
  "data": {
    "total": 45,
    "list": [{"session_id": "...", "title": "...", "status": "completed"}]
  }
}
```

---

## 可选接口

### GET /templates ⭐可选

获取模板列表。

**Response:**
```json
{
  "code": 0,
  "data": [
    {"id": "detailed", "name": "详细版"},
    {"id": "concise", "name": "简洁版"},
    {"id": "action", "name": "行动项版"},
    {"id": "executive", "name": "高管摘要版"}
  ]
}
```

### POST /upload/audio ⭐可选

上传音频文件处理。

**Request:** `multipart/form-data`
- `file`: 音频文件
- `title`: 会议标题
- `user_id`: 用户ID

---

## 前端MVP实现步骤

1. **WebSocket连接** → 实现 start/chunk/end
2. **处理消息** → 处理 started/transcript/completed
3. **结果查询** → GET /meetings/{id}/result
4. **下载文件** → GET /meetings/{id}/download?format=docx

完成这4步即可跑通全流程。

---

*详细文档: http://172.20.3.70:8765/docs*
