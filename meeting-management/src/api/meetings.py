# -*- coding: utf-8 -*-
"""
会议管理 API 路由
RESTful API for meeting CRUD
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy import select, desc, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db, AsyncSessionLocal
from models.meeting import (
    MeetingModel, MeetingCreate, MeetingStatus
)
from services.websocket_manager import websocket_manager
from meeting_skill import transcribe
from ai_minutes_generator import generate_minutes_with_ai
from prompts import list_templates, validate_template

logger = logging.getLogger(__name__)

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


@router.post("/meetings")
async def create_meeting(
    data: MeetingCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    创建新会议
    
    创建后获得 session_id，用于后续 WebSocket 连接和文件上传
    """
    session_id = generate_session_id()
    
    meeting = MeetingModel(
        session_id=session_id,
        title=data.title,
        status=MeetingStatus.CREATED,
        user_id=data.user_id,
        participants=data.participants or []
    )
    
    db.add(meeting)
    await db.commit()
    await db.refresh(meeting)
    
    return {
        "code": 0,
        "data": {
            "session_id": session_id,
            "title": meeting.title,
            "status": meeting.status,
            "created_at": meeting.created_at.isoformat(),  # type: ignore
            "ws_url": f"/api/v1/ws/meeting/{session_id}?user_id={data.user_id}"
        }
    }


@router.get("/meetings/{session_id}")
async def get_meeting(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    获取会议状态和信息
    
    - created: 已创建，等待开始
    - recording: 录音中
    - paused: 暂停
    - processing: 处理中
    - completed: 已完成
    """
    result = await db.execute(
        select(MeetingModel).where(MeetingModel.session_id == session_id)
    )
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    duration_ms = format_duration_ms(meeting.start_time, meeting.end_time)  # type: ignore
    
    return {
        "code": 0,
        "data": {
            "session_id": meeting.session_id,
            "title": meeting.title,
            "status": meeting.status,
            "duration_ms": duration_ms,
            "start_time": meeting.start_time.isoformat() if meeting.start_time else None,  # type: ignore
            "transcript_count": len(meeting.transcript_segments or []),  # type: ignore
            "has_recording": meeting.audio_path is not None,  # type: ignore
            "created_at": meeting.created_at.isoformat(),  # type: ignore
            "updated_at": meeting.updated_at.isoformat() if meeting.updated_at else None  # type: ignore
        }
    }


@router.post("/meetings/{session_id}/start")
async def start_meeting(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    开始会议录音
    
    从 created -> recording 状态
    """
    result = await db.execute(
        select(MeetingModel).where(MeetingModel.session_id == session_id)
    )
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    if meeting.status != MeetingStatus.CREATED:  # type: ignore
        raise HTTPException(status_code=400, detail=f"会议状态错误: {meeting.status}")
    
    meeting.status = MeetingStatus.RECORDING  # type: ignore  # type: ignore
    meeting.start_time = datetime.utcnow()  # type: ignore
    await db.commit()
    
    return {
        "code": 0,
        "data": {
            "session_id": session_id,
            "status": "recording",
            "start_time": meeting.start_time.isoformat()
        }
    }


@router.post("/meetings/{session_id}/pause")
async def pause_meeting(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    暂停会议录音
    
    从 recording -> paused 状态
    """
    result = await db.execute(
        select(MeetingModel).where(MeetingModel.session_id == session_id)
    )
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    if meeting.status != MeetingStatus.RECORDING:  # type: ignore
        raise HTTPException(status_code=400, detail=f"会议未在录音状态: {meeting.status}")
    
    meeting.status = MeetingStatus.PAUSED  # type: ignore
    await db.commit()
    
    return {
        "code": 0,
        "data": {
            "session_id": session_id,
            "status": "paused"
        }
    }


@router.post("/meetings/{session_id}/resume")
async def resume_meeting(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    恢复会议录音
    
    从 paused -> recording 状态
    """
    result = await db.execute(
        select(MeetingModel).where(MeetingModel.session_id == session_id)
    )
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    if meeting.status != MeetingStatus.PAUSED:  # type: ignore
        raise HTTPException(status_code=400, detail=f"会议未在暂停状态: {meeting.status}")
    
    meeting.status = MeetingStatus.RECORDING  # type: ignore
    await db.commit()
    
    return {
        "code": 0,
        "data": {
            "session_id": session_id,
            "status": "recording"
        }
    }


@router.post("/meetings/{session_id}/end")
async def end_meeting(
    session_id: str,
    template_style: Optional[str] = Query(default="detailed", description="纪要模板风格: detailed/concise/action/executive"),
    db: AsyncSession = Depends(get_db)
):
    """
    结束会议并触发AI纪要生成
    
    从 recording/paused -> processing -> completed
    异步执行：音频转写 -> AI生成 -> 保存结果
    
    Args:
        template_style: 纪要模板风格
            - detailed: 详细版（默认）
            - concise: 简洁版
            - action: 行动项版
            - executive: 高管摘要版
    """
    result = await db.execute(
        select(MeetingModel).where(MeetingModel.session_id == session_id)
    )
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    if meeting.status not in [MeetingStatus.RECORDING, MeetingStatus.PAUSED]:
        raise HTTPException(status_code=400, detail=f"会议状态错误: {meeting.status}")
    
    # 验证模板风格
    if template_style and not validate_template(template_style):
        raise HTTPException(status_code=400, detail=f"无效的模板风格: {template_style}")
    
    # 更新状态为处理中
    meeting.status = MeetingStatus.PROCESSING  # type: ignore
    meeting.end_time = datetime.utcnow()  # type: ignore
    await db.commit()
    
    # 异步执行转写和生成 - 使用新的数据库会话
    async def process_meeting():
        async with AsyncSessionLocal() as session:
            try:
                # 重新获取会议记录（在新的会话中）
                result = await session.execute(
                    select(MeetingModel).where(MeetingModel.session_id == session_id)
                )
                meeting_local = result.scalar_one_or_none()
                
                if not meeting_local:
                    logger.error(f"会议 {session_id} 在异步任务中不存在")
                    return
                
                # 获取音频路径
                audio_path = meeting_local.audio_path  # type: ignore
                
                if audio_path and os.path.exists(str(audio_path)):  # type: ignore
                    # 执行转写
                    transcript_result = await asyncio.get_event_loop().run_in_executor(
                        None, transcribe, str(audio_path)  # type: ignore
                    )
                    
                    # 保存转写结果
                    meeting_local.full_text = transcript_result.get("full_text", "")  # type: ignore
                    meeting_local.transcript_segments = [  # type: ignore
                        {
                            "id": f"seg-{i:04d}",
                            "text": seg.get("text", ""),
                            "start_time_ms": int(seg.get("start", 0) * 1000),
                            "end_time_ms": int(seg.get("end", 0) * 1000),
                            "speaker": seg.get("speaker", "")
                        }
                        for i, seg in enumerate(transcript_result.get("segments", []))
                    ]
                    
                    # AI生成纪要
                    if meeting_local.full_text:
                        minutes = await asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda: generate_minutes_with_ai(
                                meeting_local.full_text,  # type: ignore
                                title_hint=meeting_local.title,  # type: ignore
                                template_style=template_style or "detailed"
                            )
                        )
                        
                        if minutes:
                            # 将 minutes 存储到现有字段（B-003修复：不再使用不存在的 minutes 字段）
                            meeting_local.topics = minutes.get("topics", [])  # type: ignore
                            meeting_local.risks = minutes.get("risks", [])  # type: ignore
                            meeting_local.participants = minutes.get("participants", [])  # type: ignore
                            # 将 _meta 信息存入 summary（JSON格式）
                            meeting_local.summary = json.dumps({  # type: ignore
                                "_meta": minutes.get("_meta", {}),
                                "title": minutes.get("title", meeting_local.title),
                                "pending_confirmations": minutes.get("pending_confirmations", [])
                            }, ensure_ascii=False)
                            meeting_local.minutes_docx_path = f"output/meetings/{session_id}/minutes_{template_style}.docx"  # type: ignore
                else:
                    # 没有音频文件，设置默认数据
                    logger.warning(f"会议 {session_id} 没有音频文件，使用默认数据")
                    meeting_local.full_text = f"会议标题: {meeting_local.title}\n这是一个测试会议，没有录音文件。"  # type: ignore
                    meeting_local.topics = [{  # type: ignore
                        "title": "测试议题",
                        "discussion_points": ["这是一个自动生成的测试会议纪要"],
                        "conclusion": "测试结论",
                        "action_items": []
                    }]
                    meeting_local.summary = json.dumps({  # type: ignore
                        "_meta": {"generated_at": "2026-02-27T00:00:00", "template": template_style},
                        "title": meeting_local.title,
                        "pending_confirmations": []
                    }, ensure_ascii=False)
                
                # 更新状态为完成
                meeting_local.status = MeetingStatus.COMPLETED  # type: ignore
                await session.commit()
                
                # 通知WebSocket客户端
                await websocket_manager.send_custom_message(
                    session_id,
                    {
                        "type": "processing_completed",
                        "minutes_available": meeting_local.full_text is not None  # type: ignore
                    }
                )
                logger.info(f"会议 {session_id} 处理完成")
                
            except Exception as e:
                logger.error(f"会议处理失败: {e}", exc_info=True)
                # 重新获取会议记录并更新状态为失败
                try:
                    result = await session.execute(
                        select(MeetingModel).where(MeetingModel.session_id == session_id)
                    )
                    meeting_local = result.scalar_one_or_none()
                    if meeting_local:
                        meeting_local.status = MeetingStatus.FAILED  # type: ignore
                        meeting_local.error_message = str(e)  # type: ignore
                        await session.commit()
                except Exception as e2:
                    logger.error(f"更新失败状态时出错: {e2}")
    
    # 启动异步任务
    asyncio.create_task(process_meeting())
    
    return {
        "code": 0,
        "data": {
            "session_id": session_id,
            "status": "processing",
            "message": "会议处理中，请稍后查询结果",
            "template_style": template_style
        }
    }


@router.get("/meetings/{session_id}/result")
async def get_meeting_result(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    获取会议纪要和完整结果
    
    包含转写文本、结构化纪要、行动项等
    """
    result = await db.execute(
        select(MeetingModel).where(MeetingModel.session_id == session_id)
    )
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    # 构造 minutes 数据（从现有字段）
    minutes_data = {
        "action_items": meeting.action_items or [],
        "docx_path": meeting.minutes_docx_path
    } if meeting.action_items or meeting.minutes_docx_path else {}  # type: ignore
    
    return {
        "code": 0,
        "data": {
            "session_id": meeting.session_id,
            "title": meeting.title,
            "status": meeting.status,
            "full_text": meeting.full_text or "",
            "minutes": minutes_data,
            "transcript_segments": meeting.transcript_segments or [],
            "generated_at": meeting.updated_at.isoformat() if meeting.updated_at else None  # type: ignore
        }
    }


@router.get("/meetings/{session_id}/download")
async def download_meeting(
    session_id: str,
    format: str = Query(default="docx", description="格式: docx, json, txt"),
    db: AsyncSession = Depends(get_db)
):
    """
    下载会议纪要文件
    
    支持格式:
    - docx: Word文档（默认）
    - json: JSON数据文件
    - txt: 纯文本转写
    """
    result = await db.execute(
        select(MeetingModel).where(MeetingModel.session_id == session_id)
    )
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    if meeting.status != MeetingStatus.COMPLETED:  # type: ignore
        raise HTTPException(status_code=409, detail=f"会议未处理完成: {meeting.status}")
    
    # B-001修复: 校验format参数
    valid_formats = ["docx", "json", "txt"]
    if format not in valid_formats:
        raise HTTPException(
            status_code=400, 
            detail=f"无效的格式: {format}，支持的格式: {', '.join(valid_formats)}"
        )
    
    if format == "json":
        # 返回JSON格式 - 从现有字段组装 minutes（B-003修复）
        # 解析 summary 中的 _meta 信息
        summary_data = {}
        if meeting.summary:
            try:
                summary_data = json.loads(meeting.summary)
            except json.JSONDecodeError:
                summary_data = {"_meta": {}, "title": meeting.title, "pending_confirmations": []}
        
        # 从现有字段组装 minutes 对象
        minutes = {
            "title": summary_data.get("title", meeting.title),
            "participants": meeting.participants or [],
            "topics": meeting.topics or [],
            "risks": meeting.risks or [],
            "pending_confirmations": summary_data.get("pending_confirmations", []),
            "_meta": summary_data.get("_meta", {})
        }
        
        content = {
            "session_id": meeting.session_id,
            "title": meeting.title,
            "minutes": minutes,
            "full_text": meeting.full_text,
            "generated_at": meeting.updated_at.isoformat() if meeting.updated_at else None  # type: ignore
        }
        return JSONResponse(content=content)
    
    elif format == "txt":
        # 返回纯文本格式
        content = meeting.full_text or ""
        return JSONResponse(content={"text": content})
    
    elif format == "docx":
        # 返回Word文档
        docx_path = meeting.minutes_docx_path  # type: ignore
        if not docx_path or not os.path.exists(str(docx_path)):  # type: ignore
            raise HTTPException(status_code=404, detail="会议纪要文档尚未生成")
        
        return FileResponse(
            str(docx_path),  # type: ignore
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"{meeting.title or '会议纪要'}_{session_id}.docx"
        )


@router.get("/meetings/{session_id}/transcript")
async def get_meeting_transcript(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    获取会议完整转写文本（带时间戳）
    
    用于前端展示时间轴和全文搜索
    """
    result = await db.execute(
        select(MeetingModel).where(MeetingModel.session_id == session_id)
    )
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    segments = meeting.transcript_segments or []
    
    return {
        "code": 0,
        "data": {
            "session_id": meeting.session_id,
            "full_text": meeting.full_text or "",
            "segments": [
                {
                    "id": seg.get("id", f"seg-{i:04d}"),
                    "text": seg.get("text", ""),
                    "start_time_ms": seg.get("start_time_ms", 0),
                    "end_time_ms": seg.get("end_time_ms", 0),
                    "speaker": seg.get("speaker", "")
                }
                for i, seg in enumerate(segments)  # type: ignore
            ],
            "language": "zh",
            "total_segments": len(segments)  # type: ignore
        }
    }


@router.get("/meetings")
async def list_meetings(
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    获取会议列表（支持搜索和过滤）
    
    支持过滤:
    - user_id: 指定用户的会议
    - status: 会议状态
    - start_date/end_date: 日期范围 (YYYY-MM-DD)
    - keyword: 关键词搜索（标题、转写内容）
    """
    # 构建查询
    query = select(MeetingModel).order_by(desc(MeetingModel.created_at))
    
    # 应用过滤条件
    if user_id:
        query = query.where(MeetingModel.user_id == user_id)
    
    if status:
        try:
            status_enum = MeetingStatus(status)
            query = query.where(MeetingModel.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的状态: {status}")
    
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.where(MeetingModel.created_at >= start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="start_date格式错误，应为YYYY-MM-DD")
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
            query = query.where(MeetingModel.created_at <= end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="end_date格式错误，应为YYYY-MM-DD")
    
    if keyword:
        keyword_filter = or_(
            MeetingModel.title.ilike(f"%{keyword}%"),
            MeetingModel.full_text.ilike(f"%{keyword}%"),
            MeetingModel.minutes.cast(str).ilike(f"%{keyword}%")
        )
        query = query.where(keyword_filter)
    
    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # 分页
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    meetings = result.scalars().all()
    
    return {
        "code": 0,
        "total": total,
        "page": page,
        "page_size": page_size,
        "list": [
            {
                "session_id": m.session_id,
                "title": m.title,
                "date": m.created_at.strftime("%Y-%m-%d") if m.created_at else "",  # type: ignore
                "duration_ms": format_duration_ms(m.start_time, m.end_time),  # type: ignore
                "status": m.status,
                "action_item_count": len(m.action_items) if m.action_items else 0,  # type: ignore
                "has_download": bool(m.minutes_docx_path and Path(str(m.minutes_docx_path)).exists())  # type: ignore
            }
            for m in meetings
        ]
    }


class TranscriptUpdateRequest(BaseModel):
    """转写片段更新请求"""
    text: str


class TranscriptBatchUpdateItem(BaseModel):
    """批量更新项"""
    segment_id: str
    text: str


class TranscriptBatchUpdateRequest(BaseModel):
    """批量更新转写请求"""
    updates: List[TranscriptBatchUpdateItem]


@router.put("/meetings/{session_id}/transcript/{segment_id}")
async def update_transcript_segment(
    session_id: str,
    segment_id: str,
    data: TranscriptUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    更新单个转写片段
    
    用于前端编辑转写内容后保存
    """
    result = await db.execute(
        select(MeetingModel).where(MeetingModel.session_id == session_id)
    )
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    segments = meeting.transcript_segments or []
    
    for seg in segments:  # type: ignore
        if seg.get("id") == segment_id:
            seg["text"] = data.text  # type: ignore
            break
    else:
        raise HTTPException(status_code=404, detail="片段不存在")
    
    # 更新完整文本
    full_text_parts = []
    for seg in sorted(segments, key=lambda x: x.get("start_time_ms", 0)):  # type: ignore
        start_ms = seg.get("start_time_ms", 0)  # type: ignore
        minutes = start_ms // 60000
        seconds = (start_ms // 1000) % 60
        time_str = f"{minutes:02d}:{seconds:02d}"
        full_text_parts.append(f"[{time_str}] {seg['text']}")
    
    meeting.full_text = "\n".join(full_text_parts)  # type: ignore
    meeting.updated_at = datetime.utcnow()  # type: ignore
    await db.commit()
    
    # 同步更新WebSocket会话
    session = websocket_manager.get_session(session_id)
    if session:
        session.update_segment(segment_id, data.text)
    
    return {
        "code": 0,
        "data": {
            "segment_id": segment_id,
            "updated_text": data.text,
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
        for seg in segments:  # type: ignore
            if seg.get("id") == update.segment_id:
                seg["text"] = update.text  # type: ignore
                updated_count += 1
                break
    
    # 更新完整文本
    full_text_parts = []
    for seg in sorted(segments, key=lambda x: x.get("start_time_ms", 0)):  # type: ignore
        start_ms = seg.get("start_time_ms", 0)  # type: ignore
        minutes = start_ms // 60000
        seconds = (start_ms // 1000) % 60
        time_str = f"{minutes:02d}:{seconds:02d}"
        full_text_parts.append(f"[{time_str}] {seg['text']}")
    
    meeting.full_text = "\n".join(full_text_parts)  # type: ignore
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


# ========== Phase 4 新增 API ==========

@router.get("/templates")
async def list_meeting_templates():
    """
    获取会议纪要模板列表
    
    返回所有可用的纪要模板风格和描述
    """
    return {
        "code": 0,
        "data": list_templates()
    }


class RegenerateMinutesRequest(BaseModel):
    """重新生成纪要请求"""
    template_style: str = "detailed"  # detailed/concise/action/executive


@router.post("/meetings/{session_id}/regenerate")
async def regenerate_meeting_minutes(
    session_id: str,
    request: RegenerateMinutesRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    使用不同模板重新生成会议纪要
    
    适用于:
    1. 用户对首次生成的纪要风格不满意
    2. 需要不同风格的纪要（详细版/简洁版/行动项版等）
    
    Args:
        template_style: 模板风格
            - detailed: 详细版（完整记录）
            - concise: 简洁版（快速阅读）
            - action: 行动项版（任务导向）
            - executive: 高管摘要版（决策导向）
    """
    result = await db.execute(
        select(MeetingModel).where(MeetingModel.session_id == session_id)
    )
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    if not meeting.full_text:  # type: ignore
        raise HTTPException(status_code=400, detail="会议转写文本为空，无法生成纪要")
    
    # 验证模板风格
    if not validate_template(request.template_style):
        raise HTTPException(
            status_code=400, 
            detail=f"无效的模板风格: {request.template_style}"
        )
    
    try:
        # 重新生成纪要
        minutes = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: generate_minutes_with_ai(
                meeting.full_text,  # type: ignore
                title_hint=meeting.title,  # type: ignore
                template_style=request.template_style
            )
        )
        
        if not minutes:
            raise HTTPException(status_code=500, detail="AI纪要生成失败")
        
        # 保存新纪要（B-002修复：使用现有字段存储，不再使用不存在的 minutes/minutes_history）
        meeting.topics = minutes.get("topics", [])  # type: ignore
        meeting.risks = minutes.get("risks", [])  # type: ignore
        meeting.participants = minutes.get("participants", [])  # type: ignore
        # 将 _meta 信息存入 summary
        meeting.summary = json.dumps({  # type: ignore
            "_meta": minutes.get("_meta", {}),
            "title": minutes.get("title", meeting.title),
            "pending_confirmations": minutes.get("pending_confirmations", [])
        }, ensure_ascii=False)
        meeting.updated_at = datetime.utcnow()  # type: ignore
        await db.commit()
        
        return {
            "code": 0,
            "data": {
                "session_id": session_id,
                "template_style": request.template_style,
                "minutes": minutes,
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重新生成纪要失败: {str(e)}")
