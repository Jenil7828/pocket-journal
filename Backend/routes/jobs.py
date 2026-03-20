# Authentication intentionally omitted — add bearer token or IP allowlist before production deployment

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict

from flask import jsonify

from config_loader import get_config

logger = logging.getLogger("pocket_journal.routes.jobs")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _valid_media_types() -> set[str]:
    cfg = get_config()
    return set(cfg["cache"]["supported_media_types"])


def register(app, deps: dict):
    cache_store = deps.get("cache_store")
    if cache_store is None:
        logger.warning("jobs.py registered without deps['cache_store']")

    valid_types = _valid_media_types()

    @app.route("/job/v1/cache/refresh", methods=["POST"])
    def cache_refresh_all():
        """Synchronously refresh all media cache."""
        triggered_at = _utc_now_iso()
        job = "cache_refresh_all"
        start_time = time.time()

        logger.info("Job started: job=%s triggered_at=%s", job, triggered_at)

        try:
            from scripts.cache_media import refresh_all
            refresh_all(force=False)

            duration_ms = int((time.time() - start_time) * 1000)
            logger.info("Job completed: job=%s duration_ms=%d", job, duration_ms)

            return (
                jsonify(
                    {
                        "status": "completed",
                        "job": "cache_refresh_all",
                        "message": "Cache refresh completed successfully",
                        "completed_at": _utc_now_iso(),
                    }
                ),
                200,
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error("Job failed: job=%s error=%s duration_ms=%d", job, str(e), duration_ms)

            return (
                jsonify(
                    {
                        "status": "failed",
                        "job": "cache_refresh_all",
                        "error": str(e),
                    }
                ),
                500,
            )

    @app.route("/job/v1/cache/refresh/<media_type>", methods=["POST"])
    def cache_refresh_one(media_type: str):
        """Synchronously refresh a single media type cache."""
        mt = (media_type or "").strip().lower()
        if mt not in valid_types:
            return jsonify({"error": "Invalid media_type"}), 400

        triggered_at = _utc_now_iso()
        job = "cache_refresh"
        start_time = time.time()

        logger.info("Job started: job=%s triggered_at=%s", job, triggered_at)

        try:
            from scripts.cache_media import refresh_cache
            refresh_cache(mt, force=False)

            duration_ms = int((time.time() - start_time) * 1000)
            logger.info("Job completed: job=%s duration_ms=%d", job, duration_ms)

            return (
                jsonify(
                    {
                        "status": "completed",
                        "job": "cache_refresh",
                        "media_type": mt,
                        "message": f"Cache refresh for {mt} completed successfully",
                        "completed_at": _utc_now_iso(),
                    }
                ),
                200,
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error("Job failed: job=%s error=%s duration_ms=%d", job, str(e), duration_ms)

            return (
                jsonify(
                    {
                        "status": "failed",
                        "job": "cache_refresh",
                        "media_type": mt,
                        "error": str(e),
                    }
                ),
                500,
            )

    @app.route("/job/v1/cache/status", methods=["GET"])
    def cache_status_all():
        """Get cache status for all media types."""
        types_in_order = ["movies", "songs", "books", "podcasts"]
        out: Dict[str, Any] = {}
        for mt in types_in_order:
            out[mt] = cache_store.get_cache_stats(mt) if cache_store is not None else {}
        return jsonify(out), 200

    @app.route("/job/v1/cache/status/<media_type>", methods=["GET"])
    def cache_status_one(media_type: str):
        """Get cache status for a specific media type."""
        mt = (media_type or "").strip().lower()
        if mt not in valid_types:
            return jsonify({"error": "Invalid media_type"}), 400

        data = cache_store.get_cache_stats(mt) if cache_store is not None else {}
        return jsonify(data), 200


