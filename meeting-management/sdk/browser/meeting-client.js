/**
 * MeetingClient - 会议管理 JavaScript SDK
 * 
 * 功能：
 * - WebSocket 连接管理
 * - 浏览器录音（MediaRecorder）
 * - 实时转写接收
 * - 会议纪要获取
 * 
 * 版本: v1.1
 * 协议: WebSocket + REST API
 */

class MeetingClient {
  /**
   * 创建会议客户端实例
   * @param {Object} options 配置选项
   * @param {string} options.baseUrl - 服务器地址，如 'http://172.20.3.70:8765'
   * @param {string} options.userId - 用户ID，如 'user_001'
   * @param {Function} options.onTranscript - 实时转写回调 (text) => void
   * @param {Function} options.onCompleted - 会议完成回调 (data) => void
   * @param {Function} options.onError - 错误回调 (error) => void
   * @param {number} options.chunkInterval - 音频块发送间隔（毫秒），默认 1000
   */
  constructor(options = {}) {
    this.baseUrl = options.baseUrl || 'http://localhost:8765';
    this.userId = options.userId || 'anonymous';
    this.onTranscript = options.onTranscript || null;
    this.onCompleted = options.onCompleted || null;
    this.onError = options.onError || null;
    this.chunkInterval = options.chunkInterval || 1000;

    this.ws = null;
    this.mediaRecorder = null;
    this.sessionId = null;
    this.chunkSequence = 0;
    this.isRecording = false;
  }

  /**
   * 开始会议
   * @param {string} title - 会议标题
   * @returns {Promise<Object>} 会议信息 {meeting_id, audio_path}
   */
  async startMeeting(title = '未命名会议') {
    // 生成唯一会议ID
    this.sessionId = `MT${Date.now()}${Math.random().toString(36).substr(2, 5)}`;
    this.chunkSequence = 0;

    // 构建 WebSocket URL
    const wsBaseUrl = this.baseUrl.replace(/^http/, 'ws');
    const wsUrl = `${wsBaseUrl}/api/v1/ws/meeting/${this.sessionId}?user_id=${this.userId}`;

    console.log('[MeetingClient] 连接 WebSocket:', wsUrl);

    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('[MeetingClient] WebSocket 连接成功');
        // 发送 start 消息
        this.send({
          type: 'start',
          title: title,
          user_id: this.userId
        });
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleMessage(data, resolve, reject);
        } catch (e) {
          console.error('[MeetingClient] 消息解析失败:', e);
        }
      };

      this.ws.onerror = (error) => {
        console.error('[MeetingClient] WebSocket 错误:', error);
        if (this.onError) this.onError({ type: 'websocket_error', error });
        reject(error);
      };

      this.ws.onclose = () => {
        console.log('[MeetingClient] WebSocket 连接关闭');
        this.isRecording = false;
      };
    });
  }

  /**
   * 处理 WebSocket 消息
   * @private
   */
  handleMessage(data, resolve, reject) {
    console.log('[MeetingClient] 收到消息:', data.type, data);

    switch (data.type) {
      case 'started':
        // 会议已启动，开始录音
        this.startRecording().then(() => {
          resolve({
            meetingId: data.meeting_id,
            audioPath: data.audio_path
          });
        }).catch(reject);
        break;

      case 'transcript':
        // 实时转写结果
        if (this.onTranscript && data.text) {
          this.onTranscript(data.text, data.sequence, data.is_final);
        }
        break;

      case 'completed':
        // 会议完成
        console.log('[MeetingClient] 会议完成:', data);
        this.stopRecording();
        if (this.onCompleted) {
          this.onCompleted({
            meetingId: data.meeting_id,
            fullText: data.full_text,
            minutesPath: data.minutes_path,
            chunkCount: data.chunk_count
          });
        }
        break;

      case 'error':
        // 错误消息
        console.error('[MeetingClient] 服务器错误:', data);
        if (this.onError) {
          this.onError({
            code: data.code,
            message: data.message,
            recoverable: data.recoverable
          });
        }
        if (data.code === 'START_FAILED') {
          reject(data);
        }
        break;

      default:
        console.log('[MeetingClient] 未知消息类型:', data.type);
    }
  }

  /**
   * 开始录音
   * @private
   */
  async startRecording() {
    try {
      // 请求麦克风权限
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000
        }
      });

      // 创建 MediaRecorder
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm';

      this.mediaRecorder = new MediaRecorder(stream, {
        mimeType: mimeType,
        audioBitsPerSecond: 16000
      });

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0 && this.ws?.readyState === WebSocket.OPEN) {
          this.sendAudioChunk(event.data);
        }
      };

      this.mediaRecorder.onstop = () => {
        // 停止所有音轨
        stream.getTracks().forEach(track => track.stop());
      };

      this.mediaRecorder.onerror = (error) => {
        console.error('[MeetingClient] MediaRecorder 错误:', error);
        if (this.onError) this.onError({ type: 'recorder_error', error });
      };

      // 开始录制，每 chunkInterval 毫秒发送一个 chunk
      this.mediaRecorder.start(this.chunkInterval);
      this.isRecording = true;

      console.log('[MeetingClient] 录音已开始');

    } catch (error) {
      console.error('[MeetingClient] 录音启动失败:', error);
      if (this.onError) this.onError({ type: 'permission_denied', error });
      throw error;
    }
  }

  /**
   * 发送音频块
   * @private
   */
  async sendAudioChunk(blob) {
    try {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64 = reader.result.split(',')[1];
        this.send({
          type: 'chunk',
          sequence: this.chunkSequence++,
          data: base64
        });
      };
      reader.readAsDataURL(blob);
    } catch (error) {
      console.error('[MeetingClient] 发送音频块失败:', error);
    }
  }

  /**
   * 结束会议
   */
  endMeeting() {
    console.log('[MeetingClient] 正在结束会议...');

    // 停止录音
    this.stopRecording();

    // 发送 end 消息
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.send({ type: 'end' });
    }
  }

  /**
   * 停止录音
   * @private
   */
  stopRecording() {
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
      this.isRecording = false;
      console.log('[MeetingClient] 录音已停止');
    }
  }

  /**
   * 发送 WebSocket 消息
   * @private
   */
  send(data) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn('[MeetingClient] WebSocket 未连接');
    }
  }

  /**
   * 断开连接
   */
  disconnect() {
    this.stopRecording();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.isRecording = false;
    console.log('[MeetingClient] 已断开连接');
  }

  /**
   * 获取当前状态
   */
  getState() {
    return {
      connected: this.ws?.readyState === WebSocket.OPEN,
      recording: this.isRecording,
      sessionId: this.sessionId,
      chunkSequence: this.chunkSequence
    };
  }
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
  module.exports = MeetingClient;
}
