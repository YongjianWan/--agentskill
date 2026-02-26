"""
Kimi Bridge Skill - OpenClaw 与 Kimi Code CLI 的协作桥接
"""

try:
    from .executor import KimiExecutor
    from .task_manager import TaskManager
except ImportError:
    from executor import KimiExecutor
    from task_manager import TaskManager

__version__ = "1.0.0"
__all__ = ["KimiExecutor", "TaskManager"]
