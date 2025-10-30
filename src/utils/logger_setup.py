"""
Logging Setup
Configure comprehensive logging for the system
REQ-MON-015 to REQ-MON-022
"""

import logging
import os
from datetime import datetime
from pathlib import Path


def setup_logger(
    log_dir: str = "logs",
    log_level: str = "INFO",
    log_to_file: bool = True,
    log_to_console: bool = True
) -> logging.Logger:
    """
    Setup comprehensive logging system
    REQ-MON-015 to REQ-MON-022: Comprehensive logging with structured format

    Args:
        log_dir: Directory for log files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Enable file logging
        log_to_console: Enable console logging

    Returns:
        Configured root logger
    """
    # Create log directory (REQ-MON-020)
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Create formatter (REQ-MON-022: millisecond precision timestamps)
    log_format = (
        '%(asctime)s.%(msecs)03d | %(levelname)-8s | '
        '%(name)s | %(funcName)s:%(lineno)d | %(message)s'
    )
    date_format = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter(log_format, datefmt=date_format)

    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handler (REQ-MON-020: separate daily log files)
    if log_to_file:
        # Create daily log file (REQ-MON-021: log rotation)
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = os.path.join(log_dir, f'trading_{today}.log')

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # Log everything to file
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        # Create error log file
        error_log_file = os.path.join(log_dir, f'errors_{today}.log')
        error_handler = logging.FileHandler(error_log_file)
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        root_logger.addHandler(error_handler)

    # Log initial message
    root_logger.info("="*80)
    root_logger.info("Algorithmic Options Trading System - Logger Initialized")
    root_logger.info(f"Log Level: {log_level}")
    root_logger.info(f"Log Directory: {log_dir}")
    root_logger.info("="*80)

    return root_logger
