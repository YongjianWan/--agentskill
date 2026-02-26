# 真实流程测试页面

这是一个完整的浏览器端测试页面，模拟灵犀前端的真实使用流程。

## 功能

- ✅ 浏览器录音 (MediaRecorder API)
- ✅ WebSocket 实时通信
- ✅ start/chunk/end 协议
- ✅ 实时显示转写结果
- ✅ 显示最终会议纪要

## 使用步骤

### 1. 启动后端服务

```bash
cd meeting-management/src
uvicorn main:app --reload --port 8765
```

### 2. 打开测试页面

方法A：直接在浏览器中打开 `index.html`
```
file:///C:/.../meeting-management/test/real/index.html
```

方法B：用 Python 启动简单 HTTP 服务器
```bash
cd meeting-management/test/real
python -m http.server 8080
# 然后访问 http://localhost:8080
```

### 3. 开始测试

1. 点击 **"开始会议"** 按钮
2. 允许浏览器使用麦克风
3. 对着麦克风说话（建议 10-30 秒）
4. 点击 **"结束会议"** 按钮
5. 等待 AI 生成会议纪要

## 页面说明

| 区域 | 说明 |
|------|------|
| 连接配置 | WebSocket 地址、会议标题、用户ID |
| 会议控制 | 开始/结束会议按钮 |
| 统计信息 | chunks 数量、转写片段数、会议时长 |
| 实时转写 | 显示后端推送的转写文本 |
| 会议纪要 | 会议结束后显示 AI 生成的纪要 |
| 系统日志 | 详细的调试日志 |

## 测试验证点

- [ ] WebSocket 连接成功
- [ ] 麦克风权限获取成功
- [ ] MediaRecorder 创建成功
- [ ] start 消息发送成功
- [ ] chunks 正常发送（每秒一个）
- [ ] 收到 started 响应
- [ ] 收到 transcript 实时转写
- [ ] 收到 completed 最终纪要
- [ ] 会议纪要文档生成

## 常见问题

### Q: 浏览器提示 "无法访问麦克风"
A: 检查浏览器权限设置，确保允许页面访问麦克风

### Q: WebSocket 连接失败
A: 检查后端服务是否启动，端口是否为 8765

### Q: 没有收到转写结果
A: 检查：
1. 是否正确说话了（麦克风工作正常）
2. 后端 ffmpeg 是否已安装
3. 后端日志是否有错误

### Q: 会议纪要为空
A: 可能是：
1. 录音时间太短（建议至少 10 秒）
2. Whisper 转写失败（检查后端日志）
3. AI 生成失败（检查 DeepSeek API）

## 浏览器兼容性

- Chrome 90+ ✅
- Edge 90+ ✅
- Firefox 88+ ✅
- Safari 14.1+ ✅ (有限支持)

## 技术细节

- **录音格式**: WebM/Opus (浏览器 MediaRecorder 默认)
- **采样率**: 48kHz
- **声道**: 立体声
- **比特率**: 128kbps
- **Chunk 间隔**: 1 秒
