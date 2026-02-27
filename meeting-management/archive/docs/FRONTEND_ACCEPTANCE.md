# 前后端联调验收单

---

## ✅ 功能验收

### 1. 连接建立

| 检查项                  | 状态 | 备注 |
| ----------------------- | ---- | ---- |
| WebSocket 能正常连接    | ⬜   |      |
| 发送 start 收到 started | ⬜   |      |
| 会议 ID 唯一性保证      | ⬜   |      |

### 2. 实时转写

| 检查项                       | 状态 | 备注 |
| ---------------------------- | ---- | ---- |
| MediaRecorder 能正常录音     | ⬜   |      |
| chunk 正确发送（Base64）     | ⬜   |      |
| 30 秒内收到第一次 transcript | ⬜   |      |
| transcript 内容正确显示      | ⬜   |      |
| 多段 transcript 能追加显示   | ⬜   |      |

### 3. 会议纪要生成

| 检查项                         | 状态 | 备注 |
| ------------------------------ | ---- | ---- |
| 发送 end 后收到 progress       | ⬜   |      |
| progress 显示正常（步骤+消息） | ⬜   |      |
| 最终收到 completed             | ⬜   |      |
| completed 包含 full_text       | ⬜   |      |
| completed 包含 minutes_path    | ⬜   |      |
| 能正常下载 Word 文档           | ⬜   |      |

### 4. 错误处理

| 检查项                 | 状态 | 备注 |
| ---------------------- | ---- | ---- |
| 麦克风权限被拒绝有提示 | ⬜   |      |
| 网络中断有提示         | ⬜   |      |
| 收到 error 消息能显示  | ⬜   |      |
| 超时情况有处理         | ⬜   |      |

---

## 🔧 接口确认

### WebSocket 地址

```
ws://172.20.3.70:8765/api/v1/ws/meeting/{meeting_id}?user_id={user_id}
```

双方确认以上地址可用：⬜

### 消息格式

**start 消息**:

```json
{ "type": "start", "title": "会议标题" }
```

双方确认格式正确：⬜

**chunk 消息**:

```json
{ "type": "chunk", "sequence": 0, "data": "base64..." }
```

双方确认格式正确：⬜

**end 消息**:

```json
{ "type": "end" }
```

双方确认格式正确：⬜

---

## 📊 性能指标

| 指标                 | 约定值   | 实测值 | 通过 |
| -------------------- | -------- | ------ | ---- |
| 首次 transcript 延迟 | ≤ 35 秒 | ______ | ⬜   |
| 纪要生成时间         | ≤ 20 秒 | ______ | ⬜   |
| 会议结束到 completed | ≤ 30 秒 | ______ | ⬜   |
| 并发会议数           | ≥ 5 个  | ______ | ⬜   |

---

## 🐛 已知问题

写在这

## 📎 附件

- [FRONTEND_CONTRACT.md](./FRONTEND_CONTRACT.md) - 完整协议文档
- [FRONTEND_QUICKSTART.md](./FRONTEND_QUICKSTART.md) - 快速上手指南
- [FRONTEND_TROUBLESHOOTING.md](./FRONTEND_TROUBLESHOOTING.md) - 问题排查指南
