# MeetingClient.js - 浏览器 SDK

会议管理后端的前端 JavaScript SDK，提供 WebSocket 实时通信和浏览器录音功能。

## 功能特性

- ✅ WebSocket 连接管理（自动重连）
- ✅ 浏览器录音（MediaRecorder API）
- ✅ 实时转写接收
- ✅ 会议纪要获取
- ✅ 完整的错误处理

## 快速开始

### 1. 引入 SDK

```html
<script src="meeting-client.js"></script>
```

### 2. 创建客户端实例

```javascript
const client = new MeetingClient({
  baseUrl: 'http://172.20.3.70:8765',  // 服务器地址
  userId: 'user_001',                    // 用户ID
  
  // 实时转写回调
  onTranscript: (text, sequence) => {
    console.log('转写:', text);
  },
  
  // 会议完成回调
  onCompleted: (data) => {
    console.log('会议纪要:', data);
  },
  
  // 错误回调
  onError: (error) => {
    console.error('错误:', error);
  }
});
```

### 3. 开始会议

```javascript
// 开始会议并录音
await client.startMeeting('产品评审会');
```

### 4. 结束会议

```javascript
// 结束录音并生成纪要
client.endMeeting();
```

## 完整示例

```html
<!DOCTYPE html>
<html>
<head>
  <script src="meeting-client.js"></script>
</head>
<body>
  <button onclick="start()">开始会议</button>
  <button onclick="end()">结束会议</button>
  <div id="transcript"></div>
  
  <script>
    let client;
    
    async function start() {
      client = new MeetingClient({
        baseUrl: 'http://172.20.3.70:8765',
        userId: 'user_test',
        onTranscript: (text) => {
          document.getElementById('transcript').innerText += text + '\n';
        },
        onCompleted: (data) => {
          alert(`会议完成！转写长度: ${data.fullText.length}`);
        }
      });
      
      await client.startMeeting('测试会议');
    }
    
    function end() {
      client.endMeeting();
    }
  </script>
</body>
</html>
```

## API 参考

### MeetingClient(options)

创建客户端实例。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| baseUrl | string | 是 | 服务器地址，如 `http://172.20.3.70:8765` |
| userId | string | 是 | 用户ID |
| onTranscript | function | 否 | 实时转写回调 `(text, sequence, isFinal) => {}` |
| onCompleted | function | 否 | 会议完成回调 `(data) => {}` |
| onError | function | 否 | 错误回调 `(error) => {}` |
| chunkInterval | number | 否 | 音频块发送间隔（毫秒），默认 1000 |

### 方法

#### startMeeting(title)

开始会议并启动录音。

**参数：**
- `title` (string): 会议标题

**返回：** Promise&lt;{meetingId, audioPath}&gt;

#### endMeeting()

结束会议并生成纪要。

#### disconnect()

断开 WebSocket 连接。

#### getState()

获取当前状态。

**返回：** {connected, recording, sessionId, chunkSequence}

## 事件回调

### onTranscript(text, sequence, isFinal)

收到实时转写结果时触发。

- `text`: 转写文本
- `sequence`: 序号
- `isFinal`: 是否最终结果

### onCompleted(data)

会议完成时触发。

- `data.meetingId`: 会议ID
- `data.fullText`: 完整转写文本
- `data.minutesPath`: 纪要文件路径
- `data.chunkCount`: 接收的音频块数量

### onError(error)

发生错误时触发。

- `error.code`: 错误码
- `error.message`: 错误消息
- `error.type`: 错误类型

## 浏览器兼容性

- Chrome 57+
- Firefox 25+
- Edge 79+
- Safari 14.1+

## 注意事项

1. **HTTPS 要求**：公网部署必须使用 HTTPS，否则无法获取麦克风权限
2. **音频格式**：默认使用 WebM/Opus 格式
3. **Chunk 大小**：建议 1000ms 发送一次
4. **权限**：需要用户授权麦克风访问

## 示例文件

- `example.html` - 完整演示页面
- `meeting-client.js` - SDK 源码

## 更多信息

后端 API 文档：`http://{host}:8765/docs`
