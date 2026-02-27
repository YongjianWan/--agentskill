# 前端对接极简指南

> **目标**：10分钟接入，只学必要内容

## 1. 唯一重要的地址

```
WebSocket: ws://172.20.3.70:8765/api/v1/ws/meeting/{meeting_id}?user_id={user_id}
```

`meeting_id` 你自己生成，比如 `'M' + Date.now()`

---

## 2. 三步完成会议

### 第1步：连接并发送 start

```javascript
const ws = new WebSocket(`ws://172.20.3.70:8765/api/v1/ws/meeting/M123?user_id=user_001`);

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'start',
    title: '产品评审会'
  }));
};
```

### 第2步：录音并发送音频

```javascript
// 收到 started 后开始录音
ws.onmessage = async (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'started') {
    // 开始录音
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
    
    let seq = 0;
    recorder.ondataavailable = async (e) => {
      const buffer = await e.data.arrayBuffer();
      const base64 = btoa(String.fromCharCode(...new Uint8Array(buffer)));
      
      ws.send(JSON.stringify({
        type: 'chunk',
        sequence: seq++,
        data: base64
      }));
    };
    
    recorder.start(1000);  // 每秒一个chunk
  }
  
  // 显示实时转写
  if (data.type === 'transcript') {
    console.log('转写:', data.text);
  }
};
```

### 第3步：结束并获取结果

```javascript
// 用户点击结束按钮
function endMeeting() {
  ws.send(JSON.stringify({ type: 'end' }));
}

// 接收结果
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'completed') {
    console.log('完整转写:', data.full_text);
    console.log('纪要文件:', data.minutes_path);
    
    // 下载Word
    window.open(`http://172.20.3.70:8765/api/v1/meetings/${data.meeting_id}/download?format=docx`);
  }
};
```

---

## 3. 消息速查

### 发送的消息

| 类型 | 什么时候发 | 内容 |
|------|-----------|------|
| `start` | 连接成功后 | `{type: 'start', title: '会议标题'}` |
| `chunk` | 每秒一次 | `{type: 'chunk', sequence: 0, data: 'base64音频'}` |
| `end` | 点击结束 | `{type: 'end'}` |

### 接收的消息

| 类型 | 什么时候收 | 干什么 |
|------|-----------|--------|
| `started` | 开始成功后 | 开始录音 |
| `transcript` | 每30秒 | 显示转写文字 |
| `completed` | 结束后 | 显示结果、下载文件 |
| `error` | 出错时 | 显示错误提示 |

---

## 4. 完整示例

```html
<!DOCTYPE html>
<html>
<body>
  <button onclick="start()">开始会议</button>
  <button onclick="end()">结束会议</button>
  <div id="transcript"></div>
  
  <script>
    let ws, recorder;
    
    async function start() {
      const meetingId = 'M' + Date.now();
      ws = new WebSocket(`ws://172.20.3.70:8765/api/v1/ws/meeting/${meetingId}?user_id=user_001`);
      
      ws.onopen = () => ws.send(JSON.stringify({type: 'start', title: '测试会议'}));
      
      ws.onmessage = async (e) => {
        const data = JSON.parse(e.data);
        
        if (data.type === 'started') {
          const stream = await navigator.mediaDevices.getUserMedia({audio: true});
          recorder = new MediaRecorder(stream, {mimeType: 'audio/webm;codecs=opus'});
          
          let seq = 0;
          recorder.ondataavailable = async (e) => {
            const base64 = btoa(String.fromCharCode(...new Uint8Array(await e.data.arrayBuffer())));
            ws.send(JSON.stringify({type: 'chunk', sequence: seq++, data: base64}));
          };
          
          recorder.start(1000);
        }
        
        if (data.type === 'transcript') {
          document.getElementById('transcript').innerText += data.text + '\n';
        }
        
        if (data.type === 'completed') {
          alert('会议完成！纪要：' + data.minutes_path);
          window.open(`http://172.20.3.70:8765/api/v1/meetings/${data.meeting_id}/download?format=docx`);
        }
      };
    }
    
    function end() {
      recorder?.stop();
      ws.send(JSON.stringify({type: 'end'}));
    }
  </script>
</body>
</html>
```

---

## 5. 常见问题

**Q: 为什么30秒才收到一次转写？**  
A: 正常，后端每30秒批量转写一次。

**Q: 结束会议后多久收到 completed？**  
A: 通常5-15秒，取决于录音长度。

**Q: 出现"转写文本为空"怎么办？**  
A: 检查麦克风权限，确保说话声音被录进去。

---

**详细文档**：http://172.20.3.70:8765/docs/quickstart
