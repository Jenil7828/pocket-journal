import logging
import time
from flask import request

logger = logging.getLogger("pocket_journal.routes")


def log_request():
    user = getattr(request, "user", None)
    if user:
        uid = user.get("uid", "anonymous")
        email = user.get("email", "anonymous")
    else:
        uid = "anonymous"
        email = "anonymous"
    logger.info(
        "HTTP REQUEST: method=%s path=%s uid=%s email=%s params=%s",
        request.method,
        request.full_path,
        uid,
        email,
        dict(request.args),
    )

def log_response(status_code, start_time):
    user = getattr(request, "user", None)
    if user:
        uid = user.get("uid", "anonymous")
        email = user.get("email", "anonymous")
    else:
        uid = "anonymous"
        email = "anonymous"
    duration_ms = int((time.time() - start_time) * 1000)
    logger.info(
        "HTTP RESPONSE: method=%s path=%s uid=%s email=%s status=%s duration_ms=%d params=%s",
        request.method,
        request.full_path,
        uid,
        email,
        status_code,
        duration_ms,
        dict(request.args),
    )
