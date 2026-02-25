//! 会议管理桥接命令

use crate::meeting_bridge::MeetingBridge;
use std::sync::Arc;
use tauri::State;

/// 启用会议桥接
#[tauri::command]
#[specta::specta]
pub async fn enable_meeting_bridge(
    meeting_bridge: State<'_, Arc<MeetingBridge>>,
    ws_url: String,
    session_id: Option<String>,
) -> Result<(), String> {
    meeting_bridge.enable(ws_url, session_id).await;
    Ok(())
}

/// 禁用会议桥接
#[tauri::command]
#[specta::specta]
pub async fn disable_meeting_bridge(
    meeting_bridge: State<'_, Arc<MeetingBridge>>,
) -> Result<(), String> {
    meeting_bridge.disable().await;
    Ok(())
}

/// 检查会议桥接是否启用
#[tauri::command]
#[specta::specta]
pub fn is_meeting_bridge_enabled(meeting_bridge: State<'_, Arc<MeetingBridge>>) -> bool {
    meeting_bridge.is_enabled()
}
