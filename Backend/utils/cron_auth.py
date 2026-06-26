import hmac
import os
import logging
from flask import request, jsonify

logger = logging.getLogger()


def cron_secret_required():
    """
    Flask before_request hook/middleware to protect all routes starting with /job/.
    It validates that the X-Cron-Secret header matches the configured CRON_SECRET.
    """
    # 8. Skip authentication for every endpoint except /job/*
    if request.path == "/job" or request.path.startswith("/job/"):
        cron_secret = os.environ.get("CRON_SECRET")

        # 9. If CRON_SECRET is not configured, fail safely.
        if not cron_secret:
            logger.error("[AUTH][JOB] CRON_SECRET is not configured")
            return jsonify({"error": "CRON_SECRET is not configured"}), 500

        incoming_secret = request.headers.get("X-Cron-Secret", "")

        # 7. Make the comparison secure using Python's hmac.compare_digest()
        if not hmac.compare_digest(incoming_secret, cron_secret):
            # 6. Log when authentication fails:
            logger.warning("[AUTH][JOB] Unauthorized scheduler request")
            return jsonify({"error": "Unauthorized"}), 401

        # 6. Log when authentication succeeds:
        logger.info("[AUTH][JOB] Authorized scheduler request")
