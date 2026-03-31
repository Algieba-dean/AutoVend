"""
日志系统模块

提供统一的日志记录功能，支持Rich控制台输出和文件日志。
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.logging import RichHandler
from rich.text import Text


def get_logger(
    name: str = "autovend",
    level: Optional[str] = None,
    log_file: Optional[Path] = None,
    enable_rich: bool = True
) -> logging.Logger:
    """
    获取配置好的日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径（可选）
        enable_rich: 是否启用Rich格式化输出
    
    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 设置日志级别
    log_level = level or "INFO"
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # 创建格式化器
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # 控制台处理器
    if enable_rich:
        console = Console(stderr=True)
        console_handler = RichHandler(
            console=console,
            show_time=True,
            show_path=False,
            markup=True,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    else:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # 文件处理器（如果指定了日志文件）
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    enable_rich: bool = True
) -> None:
    """
    设置全局日志配置
    
    Args:
        level: 日志级别
        log_file: 日志文件路径
        enable_rich: 是否启用Rich格式化
    """
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # 清除现有处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 添加新的处理器
    logger = get_logger(
        name="autovend",
        level=level,
        log_file=log_file,
        enable_rich=enable_rich
    )


class LogMixin:
    """日志混入类，为其他类提供日志功能"""
    
    @property
    def logger(self) -> logging.Logger:
        """获取当前类的日志记录器"""
        return get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")


def log_function_call(func):
    """装饰器：记录函数调用"""
    def wrapper(*args, **kwargs):
        logger = get_logger()
        logger.debug(f"调用函数: {func.__name__}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"函数 {func.__name__} 执行成功")
            return result
        except Exception as e:
            logger.error(f"函数 {func.__name__} 执行失败: {e}")
            raise
    return wrapper


def log_performance(func):
    """装饰器：记录函数执行时间"""
    import time
    
    def wrapper(*args, **kwargs):
        logger = get_logger()
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"函数 {func.__name__} 执行时间: {execution_time:.2f}秒")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"函数 {func.__name__} 执行失败 (耗时: {execution_time:.2f}秒): {e}")
            raise
    
    return wrapper
