"""
Unified logging utilities for Pocket Journal.

All modules should use these functions to ensure consistent,
clean logging across the entire backend.
"""

import logging
import time
from flask import request


def get_logger():
    """Get root logger instance."""
    return logging.getLogger()


def get_semantic_action(method: str, status_code: int) -> str:
    """Map HTTP method + status to semantic action."""
    if status_code >= 500:
        return "ERROR"
    elif status_code == 404:
        return "NOT_FOUND"
    elif status_code == 403:
        return "FORBIDDEN"
    elif status_code == 401:
        return "UNAUTHORIZED"
    elif status_code >= 400:
        return "ERROR"
    
    if status_code == 204:
        return "DELETED"
    elif method == "POST":
        return "CREATED"
    elif method in ["PUT", "PATCH"]:
        return "UPDATED"
    elif method == "DELETE":
        return "DELETED"
    
    return "OK"


def _get_uid() -> str:
    """Get user ID from request context."""
    user = getattr(request, "user", None)
    return user.get("uid", "anonymous") if user else "anonymous"


def _get_email() -> str:
    """Get email from request context."""
    user = getattr(request, "user", None)
    return user.get("email", "anonymous") if user else "anonymous"


def log_request():
    """Log incoming HTTP request [REQ][routes]."""
    logger = get_logger()
    uid = _get_uid()
    email = _get_email()
    
    logger.info(
        "[REQ][routes] %s %s uid=%s email=%s params=%s",
        request.method,
        request.full_path,
        uid,
        email,
        dict(request.args),
    )


def log_response(status_code: int, start_time: float):
    """Log outgoing HTTP response [RES][routes]."""
    logger = get_logger()
    duration_ms = int((time.time() - start_time) * 1000)
    action = get_semantic_action(request.method, status_code)
    
    logger.info(
        "[RES][routes] %s %d %s (%dms)",
        request.method,
        status_code,
        action,
        duration_ms,
    )






