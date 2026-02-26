/**
 * 会议客户端 - WebSocket 连接管理
 * 管理与服务器的实时通信，处理转写结果和会议纪要
 * 
 * @version 1.0.0
 * @date 2026-02-25
 */

class MeetingClient {
  constructor(options = {}) {
    this.options = {
      serverUrl: 'ws://localhost:8765',
      reconnectInterval: 3000,
      maxReconnectAttempts: 5,
      heartbeatInterval: 30000,
      ...options
    };
    
    this.ws = null;
    this.sessionId = null;
    this.userId = null;
    this.isConnected = false;
    this.reconnectAttempts = 0;
    this.heartbeatTimer = null;
    this.reconnectTimer = null;
    
    // 事件回调
    this.onConnect = null;
    this.onDisconnect = null;
    this.onError = null;
    this.onTranscript = null;      // 实时转写
    this.onTopic = null;           // 议题识别
    this.onConclusion = null;      // 结论提取
    this.onActionItem = null;      // 行动项
    this.onStatusChange = null;    // 状态变更
    this.onMeetingResult = null;   // 会议纪要完成
  }

  /**
   * 连接到服务器
   * @param {string} sessionId - 会议ID（可选，不传则自动生成）
   * @param {string} userId - 用户ID
   */
  async connect(sessionId = null, userId = null) {
    this.sessionId = sessionId || this._generateSessionId();
    this.userId = userId || 'anonymous';
    
    const wsUrl = `${this.options.serverUrl}/ws/meeting/${this.sessionId}?user_id=${this.userId}`;
    
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
          console.log('WebSocket 连接成功:', this.sessionId);
          this.isConnected = true;
          this.reconnectAttempts = 0;
          this._startHeartbeat();
          
          if (this.onConnect) {
            this.onConnect({ sessionId: this.sessionId });
          }
          resolve({ sessionId: this.sessionId });
        };
        
        this.ws.onmessage = (event) => {
          this._handleMessage(event.data);
        };
        
        this.ws.onclose = (event) => {
          console.log('WebSocket 连接关闭:', event.code, event.reason);
          this.isConnected = false;
          this._stopHeartbeat();
          
          if (this.onDisconnect) {
            this.onDisconnect({ code: event.code, reason: event.reason });
          }
          
          // 自动重连
          if (!event.wasClean && this.reconnectAttempts < this.options.maxReconnectAttempts) {
            this._scheduleReconnect();
          }
        };
        
        this.ws.onerror = (error) => {
          console.error('WebSocket 错误:', error);
          if (this.onError) {
            this.onError({ type: 'CONNECTION_ERROR', error });
          }
          reject(error);
        };
        
      } catch (err) {
        reject(err);
      }
    });
  }

  /**
   * 断开连接
   */
  disconnect() {
    this._clearReconnect();
    if (this.ws) {
      this.ws.close(1000, '用户主动断开');
      this.ws = null;
    }
    this.isConnected = false;
  }

  /**
   * 开始会议
   * @param {Object} meetingInfo - 会议信息
   */
  startMeeting(meetingInfo = {}) {
    this._send({
      type: 'meeting_start',
      session_id: this.sessionId,
      title: meetingInfo.title || '未命名会议',
      start_time: new Date().toISOString(),
      participants: meetingInfo.participants || [],
      location: meetingInfo.location || ''
    });
  }

  /**
   * 结束会议
   */
  endMeeting() {
    this._send({
      type: 'meeting_end',
      session_id: this.sessionId,
      end_time: new Date().toISOString()
    });
  }

  /**
   * 暂停录音
   */
  pauseRecording() {
    this._send({
      type: 'meeting_pause',
      session_id: this.sessionId
    });
  }

  /**
   * 恢复录音
   */
  resumeRecording() {
    this._send({
      type: 'meeting_resume',
      session_id: this.sessionId
    });
  }

  /**
   * 发送音频数据
   * @param {Object} audioChunk - 音频片段
   */
  sendAudioChunk(audioChunk) {
    this._send({
      type: 'audio_chunk',
      seq: audioChunk.seq,
      timestamp_ms: audioChunk.timestamp_ms,
      data: audioChunk.data,
      mime_type: audioChunk.mime_type
    });
  }

  /**
   * 发送配置信息
   * @param {Object} config - 音频配置
   */
  sendAudioConfig(config) {
    this._send({
      type: 'audio_config',
      config: {
        sample_rate: config.sampleRate || 16000,
        channels: config.channels || 1,
        format: config.format || 'opus',
        ...config
      }
    });
  }

  /**
   * 处理收到的消息
   * @private
   */
  _handleMessage(data) {
    try {
      const msg = JSON.parse(data);
      
      switch (msg.type) {
        case 'transcript':
          if (this.onTranscript) {
            this.onTranscript({
              segmentId: msg.segment_id,
              text: msg.text,
              timestampMs: msg.timestamp_ms,
              isFinal: msg.is_final,
              speakerId: msg.speaker_id
            });
          }
          break;
          
        case 'topic_detected':
          if (this.onTopic) {
            this.onTopic({
              topicId: msg.topic_id,
              title: msg.title,
              startTimeMs: msg.start_time_ms,
              confidence: msg.confidence
            });
          }
          break;
          
        case 'conclusion':
          if (this.onConclusion) {
            this.onConclusion({
              topicId: msg.topic_id,
              text: msg.text,
              timestampMs: msg.timestamp_ms
            });
          }
          break;
          
        case 'action_item':
          if (this.onActionItem) {
            this.onActionItem({
              actionId: msg.action_id,
              action: msg.action,
              owner: msg.owner,
              deadline: msg.deadline,
              status: msg.status,
              sourceText: msg.source_text
            });
          }
          break;
          
        case 'meeting_status':
          if (this.onStatusChange) {
            this.onStatusChange({
              sessionId: msg.session_id,
              status: msg.status,
              durationMs: msg.duration_ms,
              segmentCount: msg.segment_count
            });
          }
          break;
          
        case 'meeting_result':
          if (this.onMeetingResult) {
            this.onMeetingResult({
              sessionId: msg.session_id,
              success: msg.success,
              minutes: msg.minutes,
              downloadUrl: msg.download_url
            });
          }
          break;
          
        case 'error':
          console.error('服务器错误:', msg.code, msg.message);
          if (this.onError) {
            this.onError({
              type: 'SERVER_ERROR',
              code: msg.code,
              message: msg.message,
              recoverable: msg.recoverable
            });
          }
          break;
          
        case 'pong':
          // 心跳响应
          break;
          
        default:
          console.warn('未知消息类型:', msg.type);
      }
    } catch (err) {
      console.error('消息解析失败:', err);
    }
  }

  /**
   * 发送消息
   * @private
   */
  _send(data) {
    if (this.ws && this.isConnected) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket 未连接，消息发送失败');
    }
  }

  /**
   * 启动心跳
   * @private
   */
  _startHeartbeat() {
    this.heartbeatTimer = setInterval(() => {
      if (this.isConnected) {
        this._send({ type: 'ping', timestamp: Date.now() });
      }
    }, this.options.heartbeatInterval);
  }

  /**
   * 停止心跳
   * @private
   */
  _stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  /**
   * 计划重连
   * @private
   */
  _scheduleReconnect() {
    this.reconnectAttempts++;
    console.log(`计划 ${this.options.reconnectInterval}ms 后重连 (第 ${this.reconnectAttempts} 次)`);
    
    this.reconnectTimer = setTimeout(() => {
      this.connect(this.sessionId, this.userId);
    }, this.options.reconnectInterval);
  }

  /**
   * 清除重连定时器
   * @private
   */
  _clearReconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  /**
   * 生成会话ID
   * @private
   */
  _generateSessionId() {
    const now = new Date();
    const date = now.toISOString().slice(0, 10).replace(/-/g, '');
    const time = now.toTimeString().slice(0, 8).replace(/:/g, '');
    const random = Math.random().toString(36).substring(2, 8);
    return `M${date}_${time}_${random}`;
  }
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
  module.exports = MeetingClient;
}
