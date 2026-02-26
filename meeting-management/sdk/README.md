# 灵犀会议 - 浏览器 SDK

> 浏览器前端直连服务器，实时录音转写

---

## 快速开始

### 1. 引入 SDK

```html
<script src="sdk/browser/audio-recorder.js"></script>
<script src="sdk/browser/meeting-client.js"></script>
```

### 2. 基础用法

```javascript
// 创建会议客户端
const client = new MeetingClient({
  serverUrl: 'ws://localhost:8765'
});

// 连接服务器
await client.connect();

// 开始会议
client.startMeeting({
  title: '产品评审会',
  participants: ['张三', '李四']
});

// 监听转写结果
client.onTranscript = (data) => {
  console.log(`${data.timestampMs}: ${data.text}`);
};

// 监听会议纪要
client.onMeetingResult = (data) => {
  console.log('会议纪要:', data.minutes);
};
```

### 3. 录音并发送音频

```javascript
// 创建录音器
const recorder = new MeetingAudioRecorder({
  sampleRate: 16000,
  timeslice: 1000  // 每秒发送一次
});

// 初始化麦克风
await recorder.initialize();

// 音频片段回调 - 自动发送到服务器
recorder.onAudioChunk = (chunk) => {
  client.sendAudioChunk(chunk);
};

// 开始录音
recorder.start();
```

---

## 完整示例

查看 `browser/demo.html` 获取完整演示：

```bash
# 1. 启动服务器
cd meeting-management/scripts
python websocket_server_v2.py --port 8765

# 2. 打开浏览器访问
open sdk/browser/demo.html
```

---

## API 文档

### MeetingClient

| 方法 | 说明 |
|------|------|
| `connect(sessionId?, userId?)` | 连接服务器 |
| `disconnect()` | 断开连接 |
| `startMeeting(info)` | 开始会议 |
| `endMeeting()` | 结束会议 |
| `pauseRecording()` | 暂停录音 |
| `resumeRecording()` | 恢复录音 |
| `sendAudioChunk(chunk)` | 发送音频片段 |

### MeetingAudioRecorder

| 方法 | 说明 |
|------|------|
| `initialize()` | 初始化麦克风 |
| `start()` | 开始录音 |
| `pause()` | 暂停录音 |
| `resume()` | 恢复录音 |
| `stop()` | 停止录音 |
| `destroy()` | 释放资源 |

### 事件回调

```javascript
// 转写结果
client.onTranscript = ({ segmentId, text, timestampMs, isFinal }) => {}

// 识别议题
client.onTopic = ({ topicId, title, confidence }) => {}

// 行动项
client.onActionItem = ({ actionId, action, owner, deadline }) => {}

// 会议完成
client.onMeetingResult = ({ success, minutes, downloadUrl }) => {}
```

---

## 与灵犀前端集成

### 推荐接入方式

```javascript
// 1. 用户点击"开始会议"
async function startMeeting(meetingInfo) {
  // 连接服务器
  await meetingClient.connect();
  
  // 开始会议
  meetingClient.startMeeting(meetingInfo);
  
  // 初始化录音
  await audioRecorder.initialize();
  audioRecorder.onAudioChunk = (chunk) => {
    meetingClient.sendAudioChunk(chunk);
  };
  
  // 开始录音
  audioRecorder.start();
}

// 2. 实时显示转写
meetingClient.onTranscript = (data) => {
  // 更新UI显示转写文本
  addTranscriptToUI(data);
};

// 3. 用户点击"结束会议"
function endMeeting() {
  audioRecorder.stop();
  audioRecorder.destroy();
  meetingClient.endMeeting();
}

// 4. 收到会议纪要
meetingClient.onMeetingResult = (data) => {
  // 显示会议纪要，提供下载链接
  showMeetingMinutes(data.minutes);
};
```

---

## 注意事项

1. **麦克风权限**：首次使用需要用户授权
2. **HTTPS**：生产环境需要 HTTPS 才能使用麦克风
3. **音频格式**：默认使用 WebM/Opus，服务器自动处理
4. **网络断开**：SDK 内置自动重连机制

---

## 文件说明

```
sdk/
├── browser/
│   ├── meeting-client.js    # WebSocket 客户端
│   ├── audio-recorder.js    # 录音模块
│   └── demo.html            # 演示页面
├── protocol.md              # 通信协议文档
└── README.md                # 本文件
```
