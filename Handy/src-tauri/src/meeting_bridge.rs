//! 会议管理 Skill 桥接模块
//! 通过 WebSocket 实时推送转写结果到会议管理系统

use log::{debug, error, info, warn};
use serde::{Deserialize, Serialize};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use tokio::sync::Mutex;
use tokio_tungstenite::{connect_async, tungstenite::protocol::Message};
use url::Url;

/// 转写片段数据结构
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct TranscriptionSegment {
    /// 片段ID
    pub id: String,
    /// 转写文本
    pub text: String,
    /// 开始时间（相对于会议开始，毫秒）
    pub start_time_ms: u64,
    /// 结束时间（相对于会议开始，毫秒）
    pub end_time_ms: u64,
    /// 说话人标识（如果有）
    pub speaker_id: Option<String>,
    /// 是否已结束（true=确定文本，false=中间结果）
    pub is_final: bool,
    /// 时间戳
    pub timestamp: String,
}

/// 发送到会议管理系统的消息
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum MeetingMessage {
    #[serde(rename = "session_start")]
    SessionStart {
        session_id: String,
        title: Option<String>,
        start_time: String,
    },
    #[serde(rename = "transcription")]
    Transcription {
        session_id: String,
        segment: TranscriptionSegment,
    },
    #[serde(rename = "session_end")]
    SessionEnd {
        session_id: String,
        end_time: String,
        full_text: String,
    },
}

/// 会议桥接管理器
pub struct MeetingBridge {
    enabled: Arc<AtomicBool>,
    ws_url: Arc<Mutex<Option<String>>>,
    session_id: Arc<Mutex<Option<String>>>,
    meeting_start_time: Arc<Mutex<Option<std::time::Instant>>>,
}

impl MeetingBridge {
    pub fn new() -> Self {
        Self {
            enabled: Arc::new(AtomicBool::new(false)),
            ws_url: Arc::new(Mutex::new(None)),
            session_id: Arc::new(Mutex::new(None)),
            meeting_start_time: Arc::new(Mutex::new(None)),
        }
    }

    /// 检查是否启用了会议桥接
    pub fn is_enabled(&self) -> bool {
        self.enabled.load(Ordering::Relaxed)
    }

    /// 启用会议桥接
    pub async fn enable(&self, ws_url: String, session_id: Option<String>) {
        let mut url_guard = self.ws_url.lock().await;
        *url_guard = Some(ws_url);
        drop(url_guard);

        let mut session_guard = self.session_id.lock().await;
        *session_guard = session_id.or_else(|| Some(uuid::Uuid::new_v4().to_string()));
        drop(session_guard);

        self.enabled.store(true, Ordering::Relaxed);

        // 启动会话
        self.start_session().await;
        
        info!("Meeting bridge enabled for session: {:?}", self.session_id.lock().await);
    }

    /// 禁用会议桥接
    pub async fn disable(&self) {
        if !self.enabled.load(Ordering::Relaxed) {
            return;
        }

        // 结束会话
        self.end_session().await;

        self.enabled.store(false, Ordering::Relaxed);
        
        let mut url_guard = self.ws_url.lock().await;
        *url_guard = None;
        drop(url_guard);

        let mut session_guard = self.session_id.lock().await;
        *session_guard = None;
        drop(session_guard);

        info!("Meeting bridge disabled");
    }

    /// 开始新会话
    async fn start_session(&self) {
        let session_id = self.session_id.lock().await.clone();
        let ws_url = self.ws_url.lock().await.clone();
        
        if let (Some(session_id), Some(ws_url)) = (session_id, ws_url) {
            let start_time = chrono::Utc::now().to_rfc3339();
            *self.meeting_start_time.lock().await = Some(std::time::Instant::now());

            let msg = MeetingMessage::SessionStart {
                session_id,
                title: None,
                start_time,
            };

            // 异步发送，不阻塞
            tokio::spawn(async move {
                if let Err(e) = Self::send_ws_message(&ws_url, msg).await {
                    warn!("Failed to send session start: {}", e);
                }
            });
        }
    }

    /// 结束会话
    async fn end_session(&self) {
        let session_id = self.session_id.lock().await.clone();
        let ws_url = self.ws_url.lock().await.clone();
        
        if let (Some(session_id), Some(ws_url)) = (session_id, ws_url) {
            let msg = MeetingMessage::SessionEnd {
                session_id,
                end_time: chrono::Utc::now().to_rfc3339(),
                full_text: String::new(), // 可以从历史记录中获取完整文本
            };

            tokio::spawn(async move {
                if let Err(e) = Self::send_ws_message(&ws_url, msg).await {
                    warn!("Failed to send session end: {}", e);
                }
            });
        }

        *self.meeting_start_time.lock().await = None;
    }

    /// 发送转写片段
    pub async fn send_transcription(&self, text: &str, is_final: bool) {
        if !self.enabled.load(Ordering::Relaxed) || text.is_empty() {
            return;
        }

        let session_id = match self.session_id.lock().await.clone() {
            Some(id) => id,
            None => return,
        };

        let ws_url = match self.ws_url.lock().await.clone() {
            Some(url) => url,
            None => return,
        };

        let start_offset_ms = self
            .meeting_start_time
            .lock()
            .await
            .map(|t| t.elapsed().as_millis() as u64)
            .unwrap_or(0);

        let segment = TranscriptionSegment {
            id: uuid::Uuid::new_v4().to_string(),
            text: text.to_string(),
            start_time_ms: start_offset_ms,
            end_time_ms: start_offset_ms + 1000, // 估算值
            speaker_id: None,
            is_final,
            timestamp: chrono::Utc::now().to_rfc3339(),
        };

        let msg = MeetingMessage::Transcription {
            session_id,
            segment,
        };

        // 异步发送
        tokio::spawn(async move {
            if let Err(e) = Self::send_ws_message(&ws_url, msg).await {
                debug!("Failed to send transcription: {}", e);
            }
        });
    }

    /// WebSocket 发送消息
    async fn send_ws_message(ws_url: &str, msg: MeetingMessage) -> anyhow::Result<()> {
        let url = Url::parse(ws_url)?;
        let (mut ws_stream, _) = connect_async(url).await?;

        let json = serde_json::to_string(&msg)?;
        ws_stream.send(Message::Text(json)).await?;
        ws_stream.close(None).await?;

        Ok(())
    }
}

impl Default for MeetingBridge {
    fn default() -> Self {
        Self::new()
    }
}
