import logging
import time
from flask import request

logger = logging.getLogger("pocket_journal.routes")


def log_request():
    uid = getattr(request, "user", {}).get("uid", "anonymous") if hasattr(request, "user") else "anonymous"
    logger.info(
        "HTTP REQUEST: method=%s path=%s uid=%s params=%s",
        request.method,
        request.full_path,
        uid,
        dict(request.args),
    )

def log_response(status_code, start_time):
    uid = getattr(request, "user", {}).get("uid", "anonymous") if hasattr(request, "user") else "anonymous"
    duration_ms = int((time.time() - start_time) * 1000)
    logger.info(
        "HTTP RESPONSE: method=%s path=%s uid=%s status=%s duration_ms=%d params=%s",
        request.method,
        request.full_path,
        uid,
        status_code,
        duration_ms,
        dict(request.args),
    )
