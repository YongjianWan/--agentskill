# 会议管理 - 浏览器→服务器通信协议

> 版本: v1.0-beta  
> 更新: 2026-02-25  
> 适用: 浏览器前端直连服务器架构

---

## 架构概述

```
┌─────────────┐      WebSocket       ┌─────────────┐
│  浏览器前端  │  <────────────────>  │  声音服务器  │
│             │   音频流 ↑  结果 ↓   │              │
└─────────────┘                      └─────────────┘
```

**传输内容**：
- 上行：音频流 (opus/PCM) + 控制指令 (JSON)
- 下行：转写结果 + 会议纪要 + 状态通知 (JSON)

---

## WebSocket 连接

### 连接地址

```
ws://{server_host}:{port}/ws/meeting/{session_id}?user_id={user_id}
```

**参数说明**：
- `session_id`: 会议唯一标识（由前端生成或服务器分配）
- `user_id`: 用户ID（用于权限隔离）

### 连接流程

```
1. 浏览器 → 创建 WebSocket 连接
2. 服务器 → 返回连接成功确认
3. 浏览器 → 发送 meeting_start 指令
4. 服务器 → 返回会议创建确认
5. 开始音频流传输...
```

---

## 消息协议

### 1. 控制指令（浏览器 → 服务器）

#### meeting_start - 开始会议
```json
{
  "type": "meeting_start",
  "session_id": "M20260225_143012_abc123",
  "title": "产品评审会",
  "start_time": "2026-02-25T14:30:12+08:00",
  "participants": ["张三", "李四"],
  "location": "会议室A"
}
```

#### meeting_end - 结束会议
```json
{
  "type": "meeting_end",
  "session_id": "M20260225_143012_abc123",
  "end_time": "2026-02-25T15:30:00+08:00"
}
```

#### meeting_pause - 暂停录音
```json
{
  "type": "meeting_pause",
  "session_id": "M20260225_143012_abc123"
}
```

#### meeting_resume - 恢复录音
```json
{
  "type": "meeting_resume",
  "session_id": "M20260225_143012_abc123"
}
```

#### audio_config - 音频配置
```json
{
  "type": "audio_config",
  "config": {
    "sample_rate": 16000,
    "channels": 1,
    "format": "opus"
  }
}
```

---

### 2. 音频数据（浏览器 → 服务器）

#### audio_chunk - 音频片段
```json
{
  "type": "audio_chunk",
  "seq": 123,
  "timestamp_ms": 15000,
  "data": "base64_encoded_audio_data...",
  "is_final": false
}
```

**字段说明**：
- `seq`: 序列号，用于顺序校验和丢包检测
- `timestamp_ms`: 相对于会议开始的时间戳（毫秒）
- `data`: Base64编码的音频数据（opus或PCM）
- `is_final`: 是否为最后一段音频

---

### 3. 服务器推送（服务器 → 浏览器）

#### transcript - 实时转写
```json
{
  "type": "transcript",
  "segment_id": "seg_001",
  "text": "我们今天讨论一下产品方案",
  "timestamp_ms": 15234,
  "is_final": true,
  "speaker_id": null
}
```

**字段说明**：
- `is_final`: true=确定文本，false=中间结果（会更新）
- `speaker_id`: 说话人标识（预留，当前为null）

#### topic_detected - 议题识别
```json
{
  "type": "topic_detected",
  "topic_id": "topic_001",
  "title": "产品方案讨论",
  "start_time_ms": 15234,
  "confidence": 0.85
}
```

#### conclusion - 结论提取
```json
{
  "type": "conclusion",
  "topic_id": "topic_001",
  "text": "决定采用方案B，下周五前完成原型",
  "timestamp_ms": 45234
}
```

#### action_item - 行动项
```json
{
  "type": "action_item",
  "action_id": "act_001",
  "action": "完成产品原型设计",
  "owner": "张三",
  "deadline": "2026-03-04",
  "status": "待处理",
  "source_text": "张三负责下周五前完成原型设计"
}
```

#### meeting_status - 会议状态变更
```json
{
  "type": "meeting_status",
  "session_id": "M20260225_143012_abc123",
  "status": "recording",
  "duration_ms": 123456,
  "segment_count": 42
}
```

**status 枚举**：
- `preparing`: 准备中
- `recording`: 录音中
- `paused`: 已暂停
- `processing`: 处理中（会议结束，生成纪要）
- `completed`: 已完成

#### meeting_result - 会议纪要完成
```json
{
  "type": "meeting_result",
  "session_id": "M20260225_143012_abc123",
  "success": true,
  "minutes": {
    "title": "产品评审会",
    "topics": [...],
    "action_items": [...]
  },
  "download_url": "/api/meeting/M20260225_143012_abc123/download"
}
```

#### error - 错误通知
```json
{
  "type": "error",
  "code": "AUDIO_FORMAT_ERROR",
  "message": "不支持的音频格式",
  "recoverable": true
}
```

---

## HTTP API

### 获取会议历史

```
GET /api/meetings?user_id={user_id}&start_date={date}&end_date={date}
```

### 获取会议详情

```
GET /api/meeting/{session_id}
```

### 下载会议纪要

```
GET /api/meeting/{session_id}/download?format={docx|json}
```

---

## 状态机

```
                    ┌─────────────┐
         ┌─────────│  preparing  │◄────────┐
         │         └──────┬──────┘         │
         │                │ meeting_start  │
         │                ▼                │
    pause│         ┌─────────────┐         │ meeting_end
         ├────────►│  recording  │─────────┤
         │         └──────┬──────┘         │
         │                │ pause          │
         │                ▼                │
         │         ┌─────────────┐         │
         └────────►│   paused    │─────────┘
                   └─────────────┘  resume

         ┌─────────────────────────────────┐
         │                                 │
         ▼                                 │
  ┌─────────────┐                    ┌────┴────┐
  │ processing  │───────────────────►│completed│
  └─────────────┘   result ready     └─────────┘
```

---

## 错误码

| 错误码 | 说明 | 可恢复 |
|--------|------|--------|
| `AUDIO_FORMAT_ERROR` | 音频格式不支持 | ✅ |
| `AUDIO_TOO_LARGE` | 音频数据过大 | ✅ |
| `SESSION_NOT_FOUND` | 会议不存在 | ❌ |
| `PERMISSION_DENIED` | 权限不足 | ❌ |
| `PROCESSING_ERROR` | 处理失败 | ✅ |
| `SERVER_ERROR` | 服务器内部错误 | ✅ |

---

## 前端接入示例

见 `sdk/browser/demo.html`
