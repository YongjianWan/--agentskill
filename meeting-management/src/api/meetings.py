# -*- coding: utf-8 -*-
"""
会议管理 API 路由
RESTful API for meeting CRUD
"""

import asyncio
import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
import json
import os
from pydantic import BaseModel
from sqlalchemy import select, desc, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db, AsyncSessionLocal
from models.meeting import (
    MeetingModel, MeetingCreate, MeetingResponse, MeetingResult,
    MeetingStatus, MeetingListResponse, MeetingListItem, MeetingTranscript,
    TranscriptSegment
)
from services.websocket_manager import websocket_manager
from meeting_skill import transcribe
from ai_minutes_generator import generate_minutes_with_ai

router = APIRouter()


def generate_session_id() -> str:
    """生成会议ID: MYYYYMMDD_HHMMSS_xxxxxx"""
    now = datetime.now()
    date_str = now.strftime("%Y%m%d_%H%M%S")
    random_str = uuid.uuid4().hex[:6]
    return f"M{date_str}_{random_str}"


def format_duration_ms(start: Optional[datetime], end: Optional[datetime]) -> int:
    """计算时长（毫秒）"""
    if not start:
        return 0
    end = end or datetime.utcnow()
    return int((end - start).total_seconds() * 1000)


@router.post("/meetings", response_model=MeetingResponse)
async def create_meeting(
    data: MeetingCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    创建会议
    
    - 生成session_id
    - 状态为 created
    - 返回WebSocket连接地址
    """
    session_id = generate_session_id()
    
    meeting = MeetingModel(
        session_id=session_id,
        user_id=data.user_id,
        title=data.title,
        status=MeetingStatus.CREATED,
        participants=data.participants,
        location=data.location,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(meeting)
    await db.commit()
    
    return MeetingResponse(
        session_id=session_id,
        user_id=data.user_id,
        title=data.title,
        status=MeetingStatus.CREATED,
        created_at=meeting.created_at,  # type: ignore
        updated_at=meeting.updated_at,  # type: ignore
        participants=data.participants,
        location=data.location,
        transcript_count=0
    )


@router.get("/meetings/{session_id}", response_model=MeetingResponse)
async def get_meeting(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取会议状态"""
    result = await db.execute(
        select(MeetingModel).where(MeetingModel.session_id == session_id)
    )
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    return MeetingResponse.model_validate({
        "session_id": meeting.session_id,
        "user_id": meeting.user_id,
        "title": meeting.title,
        "status": meeting.status,
        "created_at": meeting.created_at,
        "updated_at": meeting.updated_at,
        "start_time": meeting.start_time,
        "end_time": meeting.end_time,
        "duration_ms": format_duration_ms(meeting.start_time, meeting.end_time),
        "participants": meeting.participants or [],
        "location": meeting.location or "",
        "audio_path": meeting.audio_path,
        "transcript_count": len(meeting.transcript_segments or [])  # type: ignore
    })


@router.post("/meetings/{session_id}/start")
async def start_meeting(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """开始录音"""
    result = await db.execute(
        select(MeetingModel).where(MeetingModel.session_id == session_id)
    )
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    if meeting.status not in [MeetingStatus.CREATED, MeetingStatus.PAUSED]:  # type: ignore
        raise HTTPException(status_code=409, detail=f"当前状态不允许开始: {meeting.status}")
    
    meeting.status = MeetingStatus.RECORDING  # type: ignore
    if not meeting.start_time:  # type: ignore
        meeting.start_time = datetime.utcnow()  # type: ignore
    meeting.updated_at = datetime.utcnow()  # type: ignore
    
    await db.commit()
    
    return {
        "code": 0,
        "data": {
            "session_id": session_id,
            "status": MeetingStatus.RECORDING,
            "started_at": meeting.start_time.isoformat() if meeting.start_time else None
        }
    }


@router.post("/meetings/{session_id}/pause")
async def pause_meeting(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """暂停录音"""
    result = await db.execute(
        select(MeetingModel).where(MeetingModel.session_id == session_id)
    )
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    if meeting.status != MeetingStatus.RECORDING:  # type: ignore
        raise HTTPException(status_code=409, detail=f"当前状态不允许暂停: {meeting.status}")
    
    meeting.status = MeetingStatus.PAUSED  # type: ignore
    meeting.updated_at = datetime.utcnow()  # type: ignore
    await db.commit()
    
    return {
        "code": 0,
        "data": {
            "session_id": session_id,
            "status": MeetingStatus.PAUSED,
            "duration_ms": format_duration_ms(meeting.start_time, datetime.utcnow())
        }
    }


@router.post("/meetings/{session_id}/resume")
async def resume_meeting(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """恢复录音"""
    result = await db.execute(
        select(MeetingModel).where(MeetingModel.session_id == session_id)
    )
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    if meeting.status != MeetingStatus.PAUSED:  # type: ignore
        raise HTTPException(status_code=409, detail=f"当前状态不允许恢复: {meeting.status}")
    
    meeting.status = MeetingStatus.RECORDING  # type: ignore
    meeting.updated_at = datetime.utcnow()  # type: ignore
    await db.commit()
    
    return {
        "code": 0,
        "data": {
            "session_id": session_id,
            "status": MeetingStatus.RECORDING,
            "duration_ms": format_duration_ms(meeting.start_time, datetime.utcnow())
        }
    }


async def generate_minutes_task(session_id: str) -> None:
    """
    异步生成会议纪要任务
    
    - 查询会议获取音频路径
    - 调用 transcribe 转写音频
    - 调用 generate_minutes_with_ai 生成纪要
    - 更新会议状态为 COMPLETED
    - 保存 topics, action_items, risks 等到数据库
    """
    async with AsyncSessionLocal() as db:
        try:
            # 查询会议
            result = await db.execute(
                select(MeetingModel).where(MeetingModel.session_id == session_id)
            )
            meeting = result.scalar_one_or_none()
            
            if not meeting or not meeting.audio_path:
                print(f"[generate_minutes_task] 会议不存在或音频路径为空: {session_id}")
                return
            
            # 转写音频
            print(f"[generate_minutes_task] 开始转写音频: {meeting.audio_path}")
            transcription_result = transcribe(meeting.audio_path)
            full_text = transcription_result.get("text", "")
            
            if not full_text:
                print(f"[generate_minutes_task] 转写结果为空: {session_id}")
                return
            
            # 更新转写文本
            meeting.full_text = full_text  # type: ignore
            meeting.transcript_segments = transcription_result.get("segments", [])  # type: ignore
            await db.commit()
            
            # 生成会议纪要
            print(f"[generate_minutes_task] 开始生成纪要: {session_id}")
            minutes = generate_minutes_with_ai(
                transcription=full_text,
                title_hint=meeting.title or ""
            )
            
            if not minutes:
                print(f"[generate_minutes_task] 纪要生成失败: {session_id}")
                return
            
            # 提取 action_items（从 topics 中扁平化）
            action_items = []
            for topic in minutes.get("topics", []):
                for action in topic.get("action_items", []):
                    action_items.append({
                        "topic": topic.get("title", ""),
                        "action": action.get("action", ""),
                        "owner": action.get("owner", "待定"),
                        "deadline": action.get("deadline", "")
                    })
            
            # 更新会议状态和数据
            meeting.status = MeetingStatus.COMPLETED  # type: ignore
            meeting.summary = minutes.get("title", "")  # type: ignore
            meeting.topics = minutes.get("topics", [])  # type: ignore
            meeting.action_items = action_items  # type: ignore
            meeting.risks = minutes.get("risks", [])  # type: ignore
            meeting.updated_at = datetime.utcnow()  # type: ignore
            await db.commit()
            
            print(f"[generate_minutes_task] 纪要生成完成: {session_id}")
            
        except Exception as e:
            print(f"[generate_minutes_task] 异常: {session_id}, 错误: {e}")
            await db.rollback()


@router.post("/meetings/{session_id}/end")
async def end_meeting(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    结束会议
    
    - 停止录音
    - 状态变为 processing
    - 触发AI纪要生成（异步）
    """
    result = await db.execute(
        select(MeetingModel).where(MeetingModel.session_id == session_id)
    )
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    if meeting.status not in [MeetingStatus.RECORDING, MeetingStatus.PAUSED]:
        raise HTTPException(status_code=409, detail=f"当前状态不允许结束: {meeting.status}")
    
    meeting.status = MeetingStatus.PROCESSING
    meeting.end_time = datetime.utcnow()  # type: ignore
    meeting.updated_at = datetime.utcnow()  # type: ignore
    await db.commit()
    
    # 触发AI纪要生成（异步）
    asyncio.create_task(generate_minutes_task(session_id))
    
    return {
        "code": 0,
        "data": {
            "session_id": session_id,
            "status": MeetingStatus.PROCESSING,
            "duration_ms": format_duration_ms(meeting.start_time, meeting.end_time),
            "message": "正在生成会议纪要..."
        }
    }


@router.get("/meetings/{session_id}/result", response_model=MeetingResult)
async def get_meeting_result(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取会议纪要结果"""
    result = await db.execute(
        select(MeetingModel).where(MeetingModel.session_id == session_id)
    )
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    return MeetingResult(
        session_id=meeting.session_id,
        title=meeting.title,
        status=meeting.status,
        duration_ms=format_duration_ms(meeting.start_time, meeting.end_time),
        summary=meeting.summary or "",
        topics=meeting.topics or [],
        action_items=meeting.action_items or [],
        risks=meeting.risks or [],
        download_urls={
            "docx": f"/api/v1/meetings/{session_id}/download?format=docx",
            "json": f"/api/v1/meetings/{session_id}/download?format=json"
        } if meeting.status == MeetingStatus.COMPLETED else {}
    )


@router.get("/meetings/{session_id}/download")
async def download_meeting(
    session_id: str,
    format: str = Query(..., description="文件格式: docx 或 json"),
    db: AsyncSession = Depends(get_db)
):
    """
    下载会议纪要文件
    
    - format=docx: 下载 Word 文件
    - format=json: 下载 JSON 格式的纪要数据
    """
    # 查询会议记录
    result = await db.execute(
        select(MeetingModel).where(MeetingModel.session_id == session_id)
    )
    meeting = result.scalar_one_or_none()
    
    # 404: 会议不存在
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    # 400: 格式不支持
    if format not in ["docx", "json"]:
        raise HTTPException(status_code=400, detail="格式不支持，仅支持 docx 或 json")
    
    # 409: 会议尚未完成
    if meeting.status != MeetingStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="会议尚未完成，文件未生成")
    
    if format == "docx":
        # 检查 Word 文件路径是否存在
        if not meeting.minutes_docx_path or not os.path.exists(meeting.minutes_docx_path):
            raise HTTPException(status_code=404, detail="Word 文件不存在")
        
        # 返回 Word 文件
        return FileResponse(
            path=meeting.minutes_docx_path,
            filename=f"{meeting.title}_{session_id}.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    
    else:  # format == "json"
        # 构建 JSON 响应数据
        json_data = {
            "session_id": meeting.session_id,
            "title": meeting.title,
            "status": meeting.status,
            "duration_ms": format_duration_ms(meeting.start_time, meeting.end_time),
            "summary": meeting.summary or "",
            "topics": meeting.topics or [],
            "action_items": meeting.action_items or [],
            "risks": meeting.risks or [],
            "participants": meeting.participants or [],
            "location": meeting.location or "",
            "start_time": meeting.start_time.isoformat() if meeting.start_time else None,
            "end_time": meeting.end_time.isoformat() if meeting.end_time else None,
            "created_at": meeting.created_at.isoformat() if meeting.created_at else None,
        }
        
        # 返回 JSON 文件
        return JSONResponse(
            content=json_data,
            headers={
                "Content-Disposition": f'attachment; filename="{meeting.title}_{session_id}.json"'
            }
        )


@router.get("/meetings/{session_id}/transcript", response_model=MeetingTranscript)
async def get_transcript(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取完整转写文本"""
    result = await db.execute(
        select(MeetingModel).where(MeetingModel.session_id == session_id)
    )
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    return MeetingTranscript(
        session_id=session_id,
        full_text=meeting.full_text or "",
        segments=meeting.transcript_segments or []
    )


@router.get("/meetings", response_model=MeetingListResponse)
async def list_meetings(
    user_id: str = Query(..., description="用户ID"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db)
):
    """查询会议列表"""
    # 构建查询
    query = select(MeetingModel).where(MeetingModel.user_id == user_id)
    
    # 日期范围过滤
    if start_date:
        query = query.where(func.date(MeetingModel.created_at) >= start_date)
    if end_date:
        query = query.where(func.date(MeetingModel.created_at) <= end_date)
    
    # 关键词搜索（标题、转写文本、纪要内容）
    if keyword:
        query = query.where(
            or_(
                MeetingModel.title.ilike(f"%{keyword}%"),
                MeetingModel.full_text.ilike(f"%{keyword}%"),
                MeetingModel.summary.ilike(f"%{keyword}%")
            )
        )
    
    # 总数
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()
    
    # 分页
    query = query.order_by(desc(MeetingModel.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    meetings = result.scalars().all()
    
    # 转换为列表项
    items = []
    for m in meetings:
        items.append(MeetingListItem(
            session_id=m.session_id,
            title=m.title,
            date=m.created_at.strftime("%Y-%m-%d"),
            duration_ms=format_duration_ms(m.start_time, m.end_time),
            status=m.status,
            action_item_count=len(m.action_items or []),
            has_download=m.status == MeetingStatus.COMPLETED
        ))
    
    return MeetingListResponse(
        total=total,
        page=page,
        page_size=page_size,
        list=items
    )


# ========== 转写文本编辑接口 ==========

class TranscriptUpdateRequest(BaseModel):
    """转写文本编辑请求"""
    segment_id: str
    text: str


class TranscriptBatchUpdateRequest(BaseModel):
    """批量转写文本编辑请求"""
    updates: List[TranscriptUpdateRequest]


@router.put("/meetings/{session_id}/transcript/{segment_id}")
async def update_transcript_segment(
    session_id: str,
    segment_id: str,
    data: TranscriptUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    更新转写片段文本
    
    支持前端编辑转写结果后保存
    """
    result = await db.execute(
        select(MeetingModel).where(MeetingModel.session_id == session_id)
    )
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    # 查找并更新片段
    segments = meeting.transcript_segments or []
    updated = False
    
    for seg in segments:
        if seg.get("id") == segment_id:
            seg["text"] = data.text
            updated = True
            break
    
    if not updated:
        raise HTTPException(status_code=404, detail="转写片段不存在")
    
    # 更新完整文本
    full_text_parts = []
    for seg in segments:
        start_ms = seg.get("start_time_ms", 0)
        minutes = start_ms // 60000
        seconds = (start_ms // 1000) % 60
        time_str = f"{minutes:02d}:{seconds:02d}"
        full_text_parts.append(f"[{time_str}] {seg['text']}")
    
    meeting.full_text = "\n".join(full_text_parts)
    meeting.updated_at = datetime.utcnow()  # type: ignore
    await db.commit()
    
    # 同步更新 WebSocket 会话中的数据（如果有活跃连接）
    session = websocket_manager.get_session(session_id)
    if session:
        session.update_segment(segment_id, data.text)
    
    return {
        "code": 0,
        "data": {
            "segment_id": segment_id,
            "updated": True,
            "updated_at": meeting.updated_at.isoformat()  # type: ignore
        }
    }


@router.put("/meetings/{session_id}/transcript")
async def batch_update_transcript(
    session_id: str,
    data: TranscriptBatchUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    批量更新转写片段
    
    用于前端批量编辑后一次性保存
    """
    result = await db.execute(
        select(MeetingModel).where(MeetingModel.session_id == session_id)
    )
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    segments = meeting.transcript_segments or []
    updated_count = 0
    
    for update in data.updates:
        for seg in segments:
            if seg.get("id") == update.segment_id:
                seg["text"] = update.text
                updated_count += 1
                break
    
    # 更新完整文本
    full_text_parts = []
    for seg in sorted(segments, key=lambda x: x.get("start_time_ms", 0)):
        start_ms = seg.get("start_time_ms", 0)
        minutes = start_ms // 60000
        seconds = (start_ms // 1000) % 60
        time_str = f"{minutes:02d}:{seconds:02d}"
        full_text_parts.append(f"[{time_str}] {seg['text']}")
    
    meeting.full_text = "\n".join(full_text_parts)
    meeting.updated_at = datetime.utcnow()  # type: ignore
    await db.commit()
    
    # 同步更新 WebSocket 会话
    session = websocket_manager.get_session(session_id)
    if session:
        for update in data.updates:
            session.update_segment(update.segment_id, update.text)
    
    return {
        "code": 0,
        "data": {
            "updated_count": updated_count,
            "total_count": len(data.updates),
            "updated_at": meeting.updated_at.isoformat()  # type: ignore
        }
    }
