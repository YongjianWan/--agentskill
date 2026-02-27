# -*- coding: utf-8 -*-
"""
文件上传 API 路由
处理录音文件上传
"""

import asyncio
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import get_db, AsyncSessionLocal
from models.meeting import MeetingModel, MeetingStatus
from meeting_skill import transcribe, generate_minutes, save_meeting

router = APIRouter()

# 上传文件存储目录
UPLOAD_DIR = Path(__file__).parent.parent.parent / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 输出目录
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 允许的文件格式
ALLOWED_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.webm', '.ogg', '.flac'}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB


def get_file_extension(filename: str | None) -> str:
    """获取文件扩展名"""
    if filename is None:
        return ""
    return Path(filename).suffix.lower()


def generate_session_id() -> str:
    """生成会议ID"""
    now = datetime.now()
    date_str = now.strftime("%Y%m%d_%H%M%S")
    random_str = uuid.uuid4().hex[:6]
    return f"M{date_str}_{random_str}"


async def _update_meeting_status(
    session_id: str, 
    status: MeetingStatus, 
    error_msg: str | None = None,
    **kwargs
):
    """更新会议状态（后台任务使用）"""
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(MeetingModel).where(MeetingModel.session_id == session_id)
            )
            meeting = result.scalar_one_or_none()
            
            if meeting:
                meeting.status = status  # type: ignore
                meeting.updated_at = datetime.utcnow()  # type: ignore
                
                # 更新其他字段
                for key, value in kwargs.items():
                    if hasattr(meeting, key):
                        setattr(meeting, key, value)
                
                await db.commit()
                print(f"[INFO] 会议 {session_id} 状态更新为: {status}")
        except Exception as e:
            await db.rollback()
            print(f"[ERROR] 更新会议状态失败: {e}")
        finally:
            await db.close()


async def transcribe_file_task(session_id: str, file_path: Path, title: str, user_id: str):
    """
    异步转写任务
    
    流程：
    1. 调用 meeting_skill.transcribe() 转写音频
    2. 调用 meeting_skill.generate_minutes() 生成会议纪要
    3. 调用 meeting_skill.save_meeting() 保存会议纪要到文件
    4. 更新数据库状态为 COMPLETED 并保存结果
    """
    print(f"[INFO] 开始转写任务: session_id={session_id}, file={file_path}")
    
    try:
        # 更新状态为处理中
        await _update_meeting_status(session_id, MeetingStatus.PROCESSING)
        
        # Step 1: 音频转写
        print(f"[INFO] 开始音频转写: {file_path}")
        transcribe_result = transcribe(str(file_path))
        
        full_text = transcribe_result.get("full_text", "")
        participants = transcribe_result.get("participants", [])
        duration = transcribe_result.get("duration", 0)
        segments = transcribe_result.get("segments", [])
        
        print(f"[INFO] 转写完成: 时长={duration}s, 片段数={len(segments)}, 参会人={participants}")
        
        # Step 2: 生成会议纪要
        print(f"[INFO] 开始生成会议纪要...")
        meeting = generate_minutes(
            transcription=full_text,
            meeting_id=session_id,
            title=title,
            date=datetime.now().strftime("%Y-%m-%d"),
            participants=participants,
            audio_path=str(file_path)
        )
        
        print(f"[INFO] 会议纪要生成完成: 议题数={len(meeting.topics)}")
        
        # Step 3: 保存会议纪要到文件
        print(f"[INFO] 保存会议纪要...")
        files = save_meeting(meeting, output_dir=str(OUTPUT_DIR), create_version=True)
        
        minutes_docx_path = files.get("docx", "")
        minutes_json_path = files.get("json", "")
        
        print(f"[INFO] 会议纪要保存完成: DOCX={minutes_docx_path}, JSON={minutes_json_path}")
        
        # Step 4: 更新数据库为完成状态
        topics_data = []
        action_items_data = []
        for topic in meeting.topics:
            topic_dict = topic.to_dict()
            topics_data.append(topic_dict)
            for action in topic.action_items:
                action_items_data.append(action.to_dict())
        
        await _update_meeting_status(
            session_id,
            MeetingStatus.COMPLETED,
            full_text=full_text,
            transcript_segments=[{
                "timestamp": s.get("timestamp", ""),
                "speaker": s.get("speaker", ""),
                "text": s.get("text", "")
            } for s in segments],
            participants=participants,
            audio_duration_ms=duration * 1000,
            summary=meeting.topics[0].conclusion if meeting.topics else "",
            topics=topics_data,
            action_items=action_items_data,
            risks=meeting.risks,
            minutes_docx_path=minutes_docx_path
        )
        
        print(f"[INFO] 转写任务完成: session_id={session_id}")
        
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] 转写任务失败: {error_msg}")
        import traceback
        traceback.print_exc()
        
        # 更新数据库为失败状态
        await _update_meeting_status(session_id, MeetingStatus.FAILED, error_msg=error_msg)


@router.post("/upload/audio")
async def upload_audio(
    file: UploadFile = File(..., description="音频文件 (mp3/wav/m4a/webm)"),
    title: str = Form(..., min_length=1, max_length=200, description="会议标题"),
    user_id: str = Form(..., min_length=1, description="用户ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    上传录音文件
    
    - 支持格式: mp3, wav, m4a, webm, ogg, flac
    - 大小限制: 100MB
    - 上传后异步转写生成纪要
    """
    # 检查文件格式
    ext = get_file_extension(file.filename)  # type: ignore
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {ext}，支持: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # 生成session_id
    session_id = generate_session_id()
    
    # 保存文件
    safe_filename = f"{session_id}{ext}"
    file_path = UPLOAD_DIR / safe_filename
    
    try:
        content = await file.read()
        
        # 检查文件大小
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"文件大小超过限制: {MAX_FILE_SIZE / 1024 / 1024}MB"
            )
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        file_size = len(content)
        
    except Exception as e:
        # 清理已保存的文件
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")
    
    # 创建会议记录
    meeting = MeetingModel(
        session_id=session_id,
        user_id=user_id,
        title=title,
        status=MeetingStatus.PROCESSING,  # 直接变为处理中
        audio_path=str(file_path),
        participants=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(meeting)
    await db.commit()
    
    # Phase 3 - 触发异步转写任务
    asyncio.create_task(transcribe_file_task(session_id, file_path, title, user_id))
    
    return {
        "code": 0,
        "data": {
            "session_id": session_id,
            "file_name": file.filename,
            "file_size": file_size,
            "status": "uploaded",
            "message": "文件上传成功，正在处理..."
        }
    }


@router.get("/upload/{session_id}/status")
async def get_upload_status(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """查询文件处理状态"""
    from sqlalchemy import select
    result = await db.execute(
        select(MeetingModel).where(MeetingModel.session_id == session_id)
    )
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    # 计算进度
    progress = 0
    stage = meeting.status
    
    if meeting.status == MeetingStatus.PROCESSING:  # type: ignore
        # 可以根据实际处理阶段计算进度
        progress = 50
        stage = "transcribing"
    elif meeting.status == MeetingStatus.COMPLETED:  # type: ignore
        progress = 100
        stage = "completed"
    elif meeting.status == MeetingStatus.FAILED:  # type: ignore
        progress = 0
        stage = "failed"
    
    return {
        "code": 0,
        "data": {
            "session_id": session_id,
            "status": meeting.status,
            "progress": progress,
            "stage": stage
        }
    }


@router.get("/meetings/{session_id}/download")
async def download_meeting(
    session_id: str,
    format: str = Query("docx", pattern="^(docx|json)$"),  # type: ignore
    db: AsyncSession = Depends(get_db)
):
    """下载会议纪要"""
    from sqlalchemy import select
    from fastapi.responses import FileResponse
    
    result = await db.execute(
        select(MeetingModel).where(MeetingModel.session_id == session_id)
    )
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    if meeting.status != MeetingStatus.COMPLETED:  # type: ignore
        raise HTTPException(status_code=409, detail="会议纪要尚未生成完成")
    
    if format == "json":
        # 返回JSON格式的会议纪要
        return {
            "code": 0,
            "data": {
                "session_id": session_id,
                "title": meeting.title,
                "topics": meeting.topics,
                "action_items": meeting.action_items,
                "risks": meeting.risks,
                "summary": meeting.summary,
                "participants": meeting.participants,
                "transcript_segments": meeting.transcript_segments
            }
        }
    else:
        # 返回DOCX文件
        if meeting.minutes_docx_path and Path(str(meeting.minutes_docx_path)).exists():  # type: ignore
            return FileResponse(
                path=str(meeting.minutes_docx_path),  # type: ignore
                filename=f"{meeting.title}_会议纪要.docx",
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        else:
            raise HTTPException(status_code=404, detail="会议纪要文件不存在")
