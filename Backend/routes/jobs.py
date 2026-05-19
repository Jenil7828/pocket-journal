# Authentication intentionally omitted — add bearer token or IP allowlist before production deployment

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict

from flask import jsonify, request

from config_loader import get_config

logger = logging.getLogger()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _valid_media_types() -> set[str]:
    cfg = get_config()
    return set(cfg["cache"]["supported_media_types"])


def _request_force_flag() -> bool:
    raw = (
        request.args.get("force")
        or (request.get_json(silent=True) or {}).get("force")
    )
    if raw is None:
        return False
    return str(raw).strip().lower() in {"1", "true", "yes", "y", "on"}


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
        force = _request_force_flag()

        logger.info(f"[REQ][jobs] started job={job} triggered_at={triggered_at} force={force}")

        try:
            from scripts.cache_media import refresh_all
            refresh_all(force=force)

            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(f"[RES][jobs] completed job={job} duration_ms={duration_ms}")

            return (
                jsonify(
                    {
                        "status": "completed",
                        "job": "cache_refresh_all",
                        "force": force,
                        "message": "Cache refresh completed successfully",
                        "completed_at": _utc_now_iso(),
                    }
                ),
                200,
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[ERR][jobs] failed job={job} error={str(e)} duration_ms={duration_ms}")

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
        force = _request_force_flag()

        logger.info(f"[REQ][jobs] started job={job} media_type={mt} triggered_at={triggered_at} force={force}")

        try:
            from scripts.cache_media import refresh_cache
            refresh_cache(mt, force=force)

            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(f"[RES][jobs] completed job={job} media_type={mt} duration_ms={duration_ms}")

            return (
                jsonify(
                    {
                        "status": "completed",
                        "job": "cache_refresh",
                        "media_type": mt,
                        "force": force,
                        "message": f"Cache refresh for {mt} completed successfully",
                        "completed_at": _utc_now_iso(),
                    }
                ),
                200,
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[ERR][jobs] failed job={job} media_type={mt} error={str(e)} duration_ms={duration_ms}")

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

    @app.route("/job/v1/dashboard/cache/generate", methods=["POST"])
    def dashboard_cache_generate():
        """Generate AI cache for all eligible users."""
        triggered_at = _utc_now_iso()
        job = "dashboard_cache_generate"
        start_time = time.time()
        
        # Get optional limit from query params
        limit = 500
        try:
            limit_param = request.args.get("limit") or (request.get_json(silent=True) or {}).get("limit")
            if limit_param:
                limit = int(limit_param)
                if limit < 1 or limit > 2000:
                    limit = 500
        except (ValueError, TypeError):
            pass
        
        logger.info(f"[REQ][jobs] started job={job} limit={limit} triggered_at={triggered_at}")
        
        try:
            from services.dashboard_cache_job import generate_ai_cache_for_all_users
            
            _db = deps.get("get_db")()
            stats = generate_ai_cache_for_all_users(_db, limit=limit)
            
            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(f"[RES][jobs] completed job={job} duration_ms={duration_ms} stats={stats}")
            
            return (
                jsonify(
                    {
                        "status": "completed",
                        "job": "dashboard_cache_generate",
                        "message": "Dashboard AI cache generated",
                        "limit": limit,
                        "processed": stats.get("processed", 0),
                        "failed": stats.get("failed", 0),
                        "completed_at": _utc_now_iso(),
                    }
                ),
                200,
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[ERR][jobs] failed job={job} error={str(e)} duration_ms={duration_ms}")
            
            return (
                jsonify(
                    {
                        "status": "failed",
                        "job": "dashboard_cache_generate",
                        "error": str(e),
                    }
                ),
                500,
            )

