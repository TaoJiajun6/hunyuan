"""
日志配置模块
提供统一的日志配置，支持文件输出和日志轮转
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(
    log_dir: str = None,
    log_file: str = "podcast.log",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    level: int = logging.INFO,
    format_string: str = None
):
    """
    配置日志系统，同时输出到控制台和文件
    
    Args:
        log_dir: 日志文件目录，如果为None则使用项目根目录下的logs文件夹
        log_file: 日志文件名
        max_bytes: 单个日志文件最大大小（字节），默认10MB
        backup_count: 保留的备份文件数量，默认5个
        level: 日志级别，默认INFO
        format_string: 日志格式字符串，如果为None则使用默认格式
    
    Returns:
        str: 日志文件的完整路径
    """
    # 获取项目根目录
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_file_dir)
    
    # 确定日志目录
    if log_dir is None:
        log_dir = os.path.join(project_root, "logs")
    else:
        log_dir = os.path.abspath(log_dir)
    
    # 创建日志目录
    os.makedirs(log_dir, exist_ok=True)
    
    # 日志文件路径
    log_path = os.path.join(log_dir, log_file)
    
    # 默认日志格式
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # 创建格式化器
    formatter = logging.Formatter(format_string)
    
    # 获取根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 清除现有的处理器（避免重复添加）
    root_logger.handlers.clear()
    
    # 控制台处理器（StreamHandler）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 文件处理器（RotatingFileHandler，支持日志轮转）
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # 记录日志配置信息
    root_logger.info(f"日志系统已配置，日志文件: {log_path}")
    root_logger.info(f"  日志级别: {logging.getLevelName(level)}")
    root_logger.info(f"  最大文件大小: {max_bytes / (1024 * 1024):.1f} MB")
    root_logger.info(f"  保留备份数量: {backup_count}")
    
    return log_path


def get_log_file_path(log_dir: str = None, log_file: str = "podcast.log") -> str:
    """
    获取日志文件的完整路径（不创建日志系统）
    
    Args:
        log_dir: 日志文件目录，如果为None则使用项目根目录下的logs文件夹
        log_file: 日志文件名
    
    Returns:
        str: 日志文件的完整路径
    """
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_file_dir)
    
    if log_dir is None:
        log_dir = os.path.join(project_root, "logs")
    else:
        log_dir = os.path.abspath(log_dir)
    
    return os.path.join(log_dir, log_file)

