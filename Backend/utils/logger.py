"""
Centralized logging utility for Pocket Journal backend.

Provides a unified logger factory that creates loggers with
the [STAGE][FILE] format across all modules.
"""

import logging
from typing import Optional


def get_logger(module_name: str) -> logging.Logger:
    """
    Get a logger instance for a module.
    
    Args:
        module_name: Short module name (e.g., "journal", "ranking", "routes")
    
    Returns:
        Logger instance configured for clean output
    """
    logger = logging.getLogger()
    return logger


def format_log(stage: str, module: str, message: str) -> str:
    """
    Format a log message with stage and module prefix.
    
    Args:
        stage: Log stage (REQ, RES, SRV, DB, ML, ERR)
        module: Short module name
        message: Log message
    
    Returns:
        Formatted message: [STAGE][module] message
    """
    return f"[{stage}][{module}] {message}"

