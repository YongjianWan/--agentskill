#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志配置模块
提供统一的日志配置和结构化日志支持

Usage:
    from logger_config import setup_logging, get_logger
    
    setup_logging(log_dir="../output/logs", log_level="INFO")
    logger = get_logger(__name__)
    logger.info("Application started")
"""

import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# 日志格式
CONSOLE_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
FILE_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'


class JSONFormatter(logging.Formatter):
    """JSON 格式的日志格式化器，用于结构化日志"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "filename": record.filename,
            "line": record.lineno,
            "function": record.funcName,
        }
        
        # 添加额外字段
        if hasattr(record, "session_id"):
            log_data["session_id"] = record.session_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)
        
        # 异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False, default=str)


class SessionAdapter(logging.LoggerAdapter):
    """带会话上下文信息的日志适配器"""
    
    def process(self, msg, kwargs):
        # 添加上下文信息到 extra
        if "extra" not in kwargs:
            kwargs["extra"] = {}
        
        if self.extra:
            kwargs["extra"].update(self.extra)
        
        return msg, kwargs


def setup_logging(
    log_dir: Optional[str] = None,
    log_level: str = "INFO",
    enable_console: bool = True,
    enable_file: bool = True,
    enable_json: bool = False,
    app_name: str = "meeting-server"
) -> Path:
    """
    配置日志系统
    
    Args:
        log_dir: 日志文件目录，None 则只输出到控制台
        log_level: 日志级别 (DEBUG/INFO/WARNING/ERROR)
        enable_console: 是否启用控制台输出
        enable_file: 是否启用文件输出
        enable_json: 是否启用 JSON 格式（用于结构化日志）
        app_name: 应用名称（用于日志文件名）
        
    Returns:
        日志目录路径
    """
    # 根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # 清除已有处理器
    root_logger.handlers = []
    
    handlers = []
    
    # 控制台处理器
    if enable_console:
        # Windows 下强制使用 UTF-8 编码
        if sys.platform == 'win32':
            console_handler = logging.StreamHandler(
                open(sys.stdout.fileno(), mode='w', encoding='utf-8', errors='replace', closefd=False)
            )
        else:
            console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_formatter = logging.Formatter(CONSOLE_FORMAT, datefmt='%H:%M:%S')
        console_handler.setFormatter(console_formatter)
        handlers.append(console_handler)
    
    # 文件处理器
    if enable_file and log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # 普通文本日志 - 按日期轮转
        log_file = log_path / f"{app_name}.log"
        file_handler = logging.handlers.TimedRotatingFileHandler(
            log_file,
            when='midnight',  # 每天午夜切换
            interval=1,       # 每天
            backupCount=30,   # 保留最近30天
            encoding='utf-8',
            delay=False
        )
        # 自定义文件名格式: server_YYYY-MM-DD.log
        file_handler.namer = lambda name: str(Path(name).parent / f"{app_name}_{Path(name).suffix[1:]}.log")
        file_handler.setLevel(logging.DEBUG)  # 文件记录更详细
        file_formatter = logging.Formatter(FILE_FORMAT)
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)
        
        # 错误日志（单独文件）- 按日期轮转
        error_file = log_path / f"{app_name}.error.log"
        error_handler = logging.handlers.TimedRotatingFileHandler(
            error_file,
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8',
            delay=False
        )
        error_handler.namer = lambda name: str(Path(name).parent / f"{app_name}.error_{Path(name).suffix[1:]}.log")
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        handlers.append(error_handler)
        
        # JSON 结构化日志 - 按日期轮转
        if enable_json:
            json_file = log_path / f"{app_name}.json.log"
            json_handler = logging.handlers.TimedRotatingFileHandler(
                json_file,
                when='midnight',
                interval=1,
                backupCount=30,
                encoding='utf-8',
                delay=False
            )
            json_handler.namer = lambda name: str(Path(name).parent / f"{app_name}.json_{Path(name).suffix[1:]}.log")
            json_handler.setLevel(logging.DEBUG)
            json_formatter = JSONFormatter()
            json_handler.setFormatter(json_formatter)
            handlers.append(json_handler)
    
    # 添加处理器
    for handler in handlers:
        root_logger.addHandler(handler)
    
    # 设置第三方库的日志级别
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    logging.info(f"Logging configured: level={log_level}, log_dir={log_dir}")
    
    return Path(log_dir) if log_dir else None  # type: ignore


def get_logger(name: str, session_id: str = None, user_id: str = None) -> logging.Logger:
    """
    获取日志记录器
    
    Args:
        name: 模块名称 (__name__)
        session_id: 会话 ID（可选）
        user_id: 用户 ID（可选）
        
    Returns:
        Logger 实例
    """
    logger = logging.getLogger(name)
    
    if session_id or user_id:
        extra = {}
        if session_id:
            extra["session_id"] = session_id
        if user_id:
            extra["user_id"] = user_id
        return SessionAdapter(logger, extra)
    
    return logger


def log_request(logger: logging.Logger, request_type: str, data: dict):
    """
    记录请求日志
    
    Args:
        logger: 日志记录器
        request_type: 请求类型
        data: 请求数据
    """
    logger.info(f"Request [{request_type}]: {json.dumps(data, ensure_ascii=False, default=str)}")


def log_error(logger: logging.Logger, error: Exception, context: dict = None):
    """
    记录错误日志
    
    Args:
        logger: 日志记录器
        error: 异常对象
        context: 上下文信息
    """
    extra = {"extra_data": context} if context else {}
    logger.error(f"Error: {error}", exc_info=True, extra=extra)


# 便捷函数
def debug(msg: str, *args, **kwargs):
    """记录 DEBUG 级别日志"""
    logging.debug(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs):
    """记录 INFO 级别日志"""
    logging.info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs):
    """记录 WARNING 级别日志"""
    logging.warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs):
    """记录 ERROR 级别日志"""
    logging.error(msg, *args, **kwargs)


def critical(msg: str, *args, **kwargs):
    """记录 CRITICAL 级别日志"""
    logging.critical(msg, *args, **kwargs)


if __name__ == "__main__":
    # 测试日志配置
    log_dir = setup_logging(
        log_dir="../output/logs",
        log_level="DEBUG",
        enable_json=True
    )
    
    logger = get_logger(__name__)
    
    # 测试不同级别的日志
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # 测试带上下文的日志
    session_logger = get_logger(__name__, session_id="test-123", user_id="user-456")
    session_logger.info("Message with session context")
    
    # 测试结构化日志
    log_request(logger, "create_meeting", {"title": "测试会议", "participants": 5})
    
    try:
        raise ValueError("Test exception")
    except Exception as e:
        log_error(logger, e, {"operation": "test", "session_id": "test-123"})
    
    print(f"\n日志文件位置: {log_dir}")
