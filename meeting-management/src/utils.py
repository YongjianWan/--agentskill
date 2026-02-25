#!/usr/bin/env python3
"""
工具函数模块
提供边界情况处理、安全检查等辅助功能

更新记录:
- 2026-02-25: 添加磁盘空间检查、安全文件写入、超时装饰器
"""

import functools
import shutil
import signal
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Callable, Any

# 配置常量
MIN_FREE_SPACE_MB = 100  # 最小可用空间（MB）
MAX_FILE_SIZE_MB = 100   # 单个文件最大大小（MB）


class DiskFullError(Exception):
    """磁盘空间不足异常"""
    pass


class TimeoutError(Exception):
    """操作超时异常"""
    pass


class FileTooLargeError(Exception):
    """文件过大异常"""
    pass


def get_disk_free_space(path: str = ".") -> float:
    """
    获取指定路径的磁盘可用空间（MB）
    
    Args:
        path: 路径
        
    Returns:
        可用空间（MB）
    """
    try:
        stat = shutil.disk_usage(path)
        return stat.free / (1024 * 1024)  # 转换为 MB
    except Exception as e:
        raise RuntimeError(f"无法获取磁盘空间: {e}")


def check_disk_space(path: str = ".", min_free_mb: float = MIN_FREE_SPACE_MB) -> bool:
    """
    检查磁盘空间是否充足
    
    Args:
        path: 路径
        min_free_mb: 最小可用空间（MB）
        
    Returns:
        空间是否充足
        
    Raises:
        DiskFullError: 空间不足时抛出
    """
    free_mb = get_disk_free_space(path)
    if free_mb < min_free_mb:
        raise DiskFullError(
            f"磁盘空间不足: 可用 {free_mb:.1f}MB, 需要至少 {min_free_mb}MB"
        )
    return True


def safe_write_file(
    file_path: Path,
    content: str,
    encoding: str = "utf-8",
    check_space: bool = True,
    max_size_mb: float = MAX_FILE_SIZE_MB
) -> Path:
    """
    安全地写入文件（带磁盘空间检查）
    
    Args:
        file_path: 目标文件路径
        content: 文件内容
        encoding: 编码
        check_space: 是否检查磁盘空间
        max_size_mb: 内容最大大小（MB）
        
    Returns:
        写入的文件路径
        
    Raises:
        DiskFullError: 磁盘空间不足
        FileTooLargeError: 内容过大
    """
    # 检查内容大小
    content_bytes = content.encode(encoding)
    content_mb = len(content_bytes) / (1024 * 1024)
    
    if content_mb > max_size_mb:
        raise FileTooLargeError(
            f"内容过大: {content_mb:.1f}MB, 最大允许 {max_size_mb}MB"
        )
    
    # 检查磁盘空间
    if check_space:
        check_disk_space(file_path.parent, MIN_FREE_SPACE_MB)
    
    # 创建临时文件并写入
    temp_file = None
    try:
        # 使用临时文件，确保原子性写入
        fd, temp_path = tempfile.mkstemp(
            dir=file_path.parent,
            prefix=f".tmp_{file_path.stem}_",
            suffix=file_path.suffix
        )
        temp_file = Path(temp_path)
        
        try:
            with os.fdopen(fd, 'wb') as f:
                f.write(content_bytes)
        except OSError as e:
            # 写入失败，清理临时文件
            temp_file.unlink(missing_ok=True)
            if e.errno == 28:  # ENOSPC - 磁盘满
                raise DiskFullError(f"磁盘已满，无法写入文件: {file_path}")
            raise
        
        # 原子性地移动到目标位置
        temp_file.replace(file_path)
        
        return file_path
        
    except Exception:
        # 清理临时文件
        if temp_file and temp_file.exists():
            temp_file.unlink(missing_ok=True)
        raise


def safe_write_json(
    file_path: Path,
    data: Any,
    encoding: str = "utf-8",
    indent: int = 2,
    **kwargs
) -> Path:
    """
    安全地写入 JSON 文件
    
    Args:
        file_path: 目标文件路径
        data: JSON 数据
        encoding: 编码
        indent: 缩进
        **kwargs: 传递给 json.dumps 的参数
        
    Returns:
        写入的文件路径
    """
    import json
    content = json.dumps(data, ensure_ascii=False, indent=indent, default=str, **kwargs)
    return safe_write_file(file_path, content, encoding)


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    截断文本到指定长度
    
    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 截断后缀
        
    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    
    if max_length <= len(suffix):
        return suffix
    
    return text[:max_length - len(suffix)] + suffix


def validate_text_length(text: str, min_length: int = 0, max_length: Optional[int] = None) -> tuple[bool, str]:
    """
    验证文本长度
    
    Args:
        text: 文本
        min_length: 最小长度
        max_length: 最大长度
        
    Returns:
        (是否有效, 错误信息)
    """
    if text is None:
        return False, "文本不能为空"
    
    if not isinstance(text, str):
        return False, f"文本必须是字符串类型，当前类型: {type(text)}"
    
    length = len(text)
    
    if length < min_length:
        return False, f"文本过短: {length} 字符，最少需要 {min_length} 字符"
    
    if max_length is not None and length > max_length:
        return False, f"文本过长: {length} 字符，最多允许 {max_length} 字符"
    
    return True, ""


# 超时装饰器（Unix/Linux only）
if sys.platform != "win32":
    def timeout_decorator(seconds: int, error_message: str = "操作超时"):
        """
        超时装饰器（仅 Unix/Linux）
        
        Args:
            seconds: 超时秒数
            error_message: 超时错误信息
            
        Usage:
            @timeout_decorator(30)
            def slow_function():
                time.sleep(60)
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                def _handle_timeout(signum, frame):
                    raise TimeoutError(error_message)
                
                # 设置信号处理器
                old_handler = signal.signal(signal.SIGALRM, _handle_timeout)
                signal.alarm(seconds)
                
                try:
                    result = func(*args, **kwargs)
                finally:
                    signal.alarm(0)  # 取消闹钟
                    signal.signal(signal.SIGALRM, old_handler)  # 恢复旧处理器
                
                return result
            return wrapper
        return decorator
else:
    # Windows 不支持 signal.SIGALRM，使用 asyncio 替代
    def timeout_decorator(seconds: int, error_message: str = "操作超时"):
        """
        超时装饰器（Windows 兼容版本，使用 asyncio）
        
        Args:
            seconds: 超时秒数
            error_message: 超时错误信息
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                import asyncio
                
                async def run_with_timeout():
                    return await asyncio.wait_for(
                        asyncio.to_thread(func, *args, **kwargs),
                        timeout=seconds
                    )
                
                try:
                    return asyncio.run(run_with_timeout())
                except asyncio.TimeoutError:
                    raise TimeoutError(error_message)
            return wrapper
        return decorator


@contextmanager
def timer(name: str = "Operation", logger=None):
    """
    计时上下文管理器
    
    Usage:
        with timer("Database query", logger):
            result = db.query()
    """
    start = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start
        msg = f"{name} completed in {elapsed:.2f}s"
        if logger:
            logger.info(msg)
        else:
            print(msg)


def get_memory_usage() -> dict:
    """
    获取当前进程内存使用情况
    
    Returns:
        内存使用信息字典
    """
    try:
        import psutil
        process = psutil.Process()
        mem_info = process.memory_info()
        return {
            "rss_mb": mem_info.rss / (1024 * 1024),
            "vms_mb": mem_info.vms / (1024 * 1024),
            "percent": process.memory_percent()
        }
    except ImportError:
        return {"error": "psutil not installed"}


def check_memory_usage(max_percent: float = 80.0) -> bool:
    """
    检查内存使用情况
    
    Args:
        max_percent: 最大允许内存使用百分比
        
    Returns:
        内存使用是否正常
    """
    try:
        import psutil
        mem = psutil.virtual_memory()
        if mem.percent > max_percent:
            raise RuntimeError(f"内存使用过高: {mem.percent:.1f}%, 最大允许 {max_percent}%")
        return True
    except ImportError:
        return True  # 无法检查时默认通过


if __name__ == "__main__":
    # 测试工具函数
    import os
    
    print("=" * 60)
    print("工具函数测试")
    print("=" * 60)
    
    # 测试磁盘空间检查
    print("\n1. 磁盘空间检查:")
    try:
        free_mb = get_disk_free_space(".")
        print(f"   可用空间: {free_mb:.1f} MB")
        check_disk_space(".", 10)
        print("   ✓ 空间充足")
    except Exception as e:
        print(f"   ✗ 错误: {e}")
    
    # 测试文件写入
    print("\n2. 安全文件写入:")
    try:
        test_path = Path("./test_output.txt")
        result = safe_write_file(test_path, "Hello, World!" * 1000)
        print(f"   ✓ 写入成功: {result}")
        test_path.unlink()  # 清理
    except Exception as e:
        print(f"   ✗ 错误: {e}")
    
    # 测试 JSON 写入
    print("\n3. 安全 JSON 写入:")
    try:
        test_path = Path("./test_output.json")
        result = safe_write_json(test_path, {"key": "value", "list": [1, 2, 3]})
        print(f"   ✓ 写入成功: {result}")
        test_path.unlink()  # 清理
    except Exception as e:
        print(f"   ✗ 错误: {e}")
    
    # 测试文本截断
    print("\n4. 文本截断:")
    long_text = "A" * 1000
    truncated = truncate_text(long_text, 50)
    print(f"   原始长度: {len(long_text)}, 截断后: {len(truncated)}")
    print(f"   结果: {truncated}")
    
    # 测试文本长度验证
    print("\n5. 文本长度验证:")
    valid, msg = validate_text_length("Hello", min_length=3, max_length=100)
    print(f"   'Hello': valid={valid}, msg={msg}")
    
    valid, msg = validate_text_length("Hi", min_length=3, max_length=100)
    print(f"   'Hi': valid={valid}, msg={msg}")
    
    # 测试计时器
    print("\n6. 计时器:")
    with timer("Sleep test"):
        time.sleep(0.5)
    
    # 测试内存使用
    print("\n7. 内存使用:")
    mem = get_memory_usage()
    print(f"   {mem}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
