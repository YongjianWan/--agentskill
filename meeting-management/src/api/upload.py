"""
文件上传 API 路由
处理录音文件上传
"""

import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.meeting import MeetingModel, MeetingStatus

router = APIRouter()

# 上传文件存储目录
UPLOAD_DIR = Path(__file__).parent.parent.parent / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

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
    
    # TODO: Phase 3 - 触发异步转写
    # asyncio.create_task(transcribe_file_task(session_id, file_path))
    
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
    
    if meeting.status == MeetingStatus.PROCESSING:
        # TODO: 根据实际处理阶段计算进度
        progress = 50  # 临时值
        stage = "transcribing"
    elif meeting.status == MeetingStatus.COMPLETED:
        progress = 100
        stage = "completed"
    
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
    format: str = Query("docx", regex="^(docx|json)$"),
    db: AsyncSession = Depends(get_db)
):
    """下载会议纪要"""
    from sqlalchemy import select
    result = await db.execute(
        select(MeetingModel).where(MeetingModel.session_id == session_id)
    )
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    if meeting.status != MeetingStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="会议纪要尚未生成完成")
    
    # TODO: Phase 4 - 生成DOCX/JSON文件并返回
    # 临时返回JSON
    if format == "json":
        return {
            "code": 0,
            "data": {
                "session_id": session_id,
                "title": meeting.title,
                "topics": meeting.topics,
                "action_items": meeting.action_items
            }
        }
    else:
        # TODO: 生成DOCX文件
        raise HTTPException(status_code=501, detail="DOCX格式暂不支持")
