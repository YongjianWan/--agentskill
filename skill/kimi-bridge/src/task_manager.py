"""
任务队列管理器 - 处理任务的创建、状态流转和持久化
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class Task:
    """任务定义"""
    task_id: str
    type: str  # file_edit, analyze, search, batch
    instruction: str
    working_dir: str
    files: List[str]
    dry_run: bool
    timeout: int
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict] = None
    error: Optional[str] = None
    session_id: Optional[str] = None  # OpenClaw session ID，用于上下文保持

    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            "status": self.status.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Task":
        data = data.copy()
        data["status"] = TaskStatus(data.get("status", "pending"))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class TaskManager:
    """任务队列管理器"""
    
    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        self.base_dir = Path(base_dir)
        self.tasks_dir = self.base_dir / "tasks"
        
        # 确保目录存在
        for subdir in ["pending", "completed", "failed"]:
            (self.tasks_dir / subdir).mkdir(parents=True, exist_ok=True)
    
    def create_task(
        self,
        task_type: str,
        instruction: str,
        working_dir: str = ".",
        files: Optional[List[str]] = None,
        dry_run: bool = False,
        timeout: int = 120,
        session_id: Optional[str] = None
    ) -> Task:
        """创建新任务"""
        
        # 生成任务 ID
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        short_uuid = uuid.uuid4().hex[:8]
        task_id = f"{task_type}-{timestamp}-{short_uuid}"
        
        task = Task(
            task_id=task_id,
            type=task_type,
            instruction=instruction,
            working_dir=os.path.abspath(working_dir),
            files=files or [],
            dry_run=dry_run,
            timeout=timeout,
            created_at=datetime.now().isoformat(),
            session_id=session_id
        )
        
        # 保存到 pending 目录
        self._save_task(task, "pending")
        
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务（任意状态）"""
        for status_dir in ["pending", "completed", "failed"]:
            task_file = self.tasks_dir / status_dir / f"{task_id}.json"
            if task_file.exists():
                return self._load_task(task_file)
        return None
    
    def list_pending(self) -> List[Task]:
        """列出所有待处理任务"""
        pending_dir = self.tasks_dir / "pending"
        tasks = []
        for task_file in sorted(pending_dir.glob("*.json")):
            task = self._load_task(task_file)
            if task:
                tasks.append(task)
        return tasks
    
    def update_status(self, task_id: str, status: TaskStatus, result: Optional[Dict] = None, error: Optional[str] = None) -> bool:
        """更新任务状态"""
        task = self.get_task(task_id)
        if not task:
            return False
        
        task.status = status
        
        if status == TaskStatus.RUNNING:
            task.started_at = datetime.now().isoformat()
        elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.TIMEOUT]:
            task.completed_at = datetime.now().isoformat()
        
        if result:
            task.result = result
        if error:
            task.error = error
        
        # 确定目标目录
        if status == TaskStatus.PENDING:
            target_dir = "pending"
        elif status == TaskStatus.RUNNING:
            target_dir = "pending"  # 运行中仍在 pending
        elif status == TaskStatus.COMPLETED:
            target_dir = "completed"
        else:
            target_dir = "failed"
        
        # 从原位置删除
        for src_dir in ["pending", "completed", "failed"]:
            src_file = self.tasks_dir / src_dir / f"{task_id}.json"
            if src_file.exists() and src_dir != target_dir:
                src_file.unlink()
        
        # 保存到新位置
        self._save_task(task, target_dir)
        
        return True
    
    def _save_task(self, task: Task, status_dir: str):
        """保存任务到文件"""
        task_file = self.tasks_dir / status_dir / f"{task.task_id}.json"
        with open(task_file, 'w', encoding='utf-8') as f:
            json.dump(task.to_dict(), f, indent=2, ensure_ascii=False)
    
    def _load_task(self, task_file: Path) -> Optional[Task]:
        """从文件加载任务"""
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return Task.from_dict(data)
        except Exception as e:
            print(f"[Error] 加载任务失败 {task_file}: {e}")
            return None
    
    def get_task_path(self, task_id: str, status: str) -> Path:
        """获取任务文件路径"""
        return self.tasks_dir / status / f"{task_id}.json"
