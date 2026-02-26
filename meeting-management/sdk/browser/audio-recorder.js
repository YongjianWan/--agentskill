/**
 * 会议录音器 - 浏览器端音频采集
 * 使用 MediaRecorder API 录制音频并实时发送至服务器
 * 
 * @version 1.0.0
 * @date 2026-02-25
 */

class MeetingAudioRecorder {
  constructor(options = {}) {
    this.options = {
      sampleRate: 16000,
      channelCount: 1,
      mimeType: 'audio/webm;codecs=opus',
      timeslice: 1000,  // 每秒发送一次音频数据
      ...options
    };
    
    this.mediaRecorder = null;
    this.audioStream = null;
    this.isRecording = false;
    this.isPaused = false;
    this.seq = 0;
    this.startTime = null;
    this.onAudioChunk = null;  // 回调：音频片段 ready
    this.onError = null;       // 回调：错误
    this.onStateChange = null; // 回调：状态变更
  }

  /**
   * 请求麦克风权限并初始化
   */
  async initialize() {
    try {
      this.audioStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: this.options.sampleRate,
          channelCount: this.options.channelCount,
          echoCancellation: true,
          noiseSuppression: true
        }
      });
      
      this._updateState('initialized');
      return true;
    } catch (err) {
      console.error('麦克风权限获取失败:', err);
      this._triggerError('MICROPHONE_PERMISSION_DENIED', err.message);
      return false;
    }
  }

  /**
   * 开始录音
   */
  start() {
    if (!this.audioStream) {
      throw new Error('请先调用 initialize() 初始化');
    }
    
    if (this.isRecording && !this.isPaused) {
      console.warn('录音已在进行中');
      return;
    }

    // 如果是暂停后恢复
    if (this.isPaused) {
      this.mediaRecorder.resume();
      this.isPaused = false;
      this._updateState('recording');
      return;
    }

    // 创建 MediaRecorder
    const options = {};
    if (MediaRecorder.isTypeSupported(this.options.mimeType)) {
      options.mimeType = this.options.mimeType;
    }
    
    this.mediaRecorder = new MediaRecorder(this.audioStream, options);
    this.seq = 0;
    this.startTime = Date.now();
    
    // 收集音频数据
    let audioChunks = [];
    
    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.push(event.data);
        
        // 转换为 base64 并发送
        const blob = new Blob(audioChunks, { type: event.data.type });
        this._sendAudioChunk(blob);
        audioChunks = [];
      }
    };
    
    this.mediaRecorder.onstart = () => {
      this.isRecording = true;
      this.isPaused = false;
      this._updateState('recording');
    };
    
    this.mediaRecorder.onpause = () => {
      this.isPaused = true;
      this._updateState('paused');
    };
    
    this.mediaRecorder.onresume = () => {
      this.isPaused = false;
      this._updateState('recording');
    };
    
    this.mediaRecorder.onstop = () => {
      this.isRecording = false;
      this._updateState('stopped');
    };
    
    this.mediaRecorder.onerror = (err) => {
      console.error('MediaRecorder 错误:', err);
      this._triggerError('RECORDER_ERROR', err.message);
    };
    
    // 开始录制，按 timeslice 分割
    this.mediaRecorder.start(this.options.timeslice);
  }

  /**
   * 暂停录音
   */
  pause() {
    if (this.mediaRecorder && this.isRecording && !this.isPaused) {
      this.mediaRecorder.pause();
    }
  }

  /**
   * 恢复录音
   */
  resume() {
    if (this.mediaRecorder && this.isPaused) {
      this.mediaRecorder.resume();
    }
  }

  /**
   * 停止录音
   */
  stop() {
    if (this.mediaRecorder && this.isRecording) {
      this.mediaRecorder.stop();
    }
  }

  /**
   * 获取当前录音时长（毫秒）
   */
  getDuration() {
    if (!this.startTime) return 0;
    return Date.now() - this.startTime;
  }

  /**
   * 释放资源
   */
  destroy() {
    this.stop();
    
    if (this.audioStream) {
      this.audioStream.getTracks().forEach(track => track.stop());
      this.audioStream = null;
    }
    
    this.mediaRecorder = null;
    this._updateState('destroyed');
  }

  /**
   * 将音频 blob 转换为 base64
   * @private
   */
  async _blobToBase64(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64 = reader.result.split(',')[1];
        resolve(base64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  }

  /**
   * 发送音频片段
   * @private
   */
  async _sendAudioChunk(blob) {
    if (!this.onAudioChunk) return;
    
    try {
      const base64Data = await this._blobToBase64(blob);
      const timestampMs = this.getDuration();
      
      this.onAudioChunk({
        seq: this.seq++,
        timestamp_ms: timestampMs,
        data: base64Data,
        mime_type: blob.type,
        size: blob.size
      });
    } catch (err) {
      console.error('音频编码失败:', err);
      this._triggerError('AUDIO_ENCODE_ERROR', err.message);
    }
  }

  /**
   * 更新状态并触发回调
   * @private
   */
  _updateState(state) {
    if (this.onStateChange) {
      this.onStateChange(state, {
        isRecording: this.isRecording,
        isPaused: this.isPaused,
        duration: this.getDuration()
      });
    }
  }

  /**
   * 触发错误回调
   * @private
   */
  _triggerError(code, message) {
    if (this.onError) {
      this.onError({ code, message });
    }
  }
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
  module.exports = MeetingAudioRecorder;
}
