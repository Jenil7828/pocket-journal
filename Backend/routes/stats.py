import time
from utils.logging_utils import log_request, log_response
from flask import request, jsonify
from datetime import datetime, timedelta
import pytz

TZ = pytz.timezone("Asia/Kolkata")


def register(app, deps):
    login_required = deps["login_required"]
    stats_service = deps["stats_service"]
    get_db = deps["get_db"]

    @app.route("/api/v1/stats", methods=["GET"])
    @login_required
    def get_user_stats():
        start_time = time.time()
        log_request()
        uid = request.user["uid"]
        _db = get_db()
        body, status = stats_service.get_user_stats(uid, _db)
        log_response(status, start_time)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    @app.route("/api/v1/mood-trends", methods=["GET"])
    @login_required
    def get_mood_trends():
        start_time = time.time()
        log_request()
        uid = request.user["uid"]
        try:
            days = int(request.args.get("days", 30))
        except ValueError:
            log_response(400, start_time)
            return jsonify({"error": "Invalid days parameter"}), 400
        _db = get_db()
        body, status = stats_service.get_mood_trends(uid, days, _db)
        log_response(status, start_time)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    @app.route("/api/v1/stats/weekly", methods=["GET"])
    @login_required
    def get_weekly_stats():
        """Get stats for the last 7 days."""
        start_time = time.time()
        log_request()
        uid = request.user["uid"]
        _db = get_db()
        
        # Use timezone-aware datetime
        today = datetime.now(TZ)
        start_date = (today - timedelta(days=7)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end_date = today
        
        body, status = stats_service.get_stats_by_date_range(
            uid, start_date.isoformat(), end_date.isoformat(), _db
        )
        log_response(status, start_time)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    @app.route("/api/v1/stats/monthly", methods=["GET"])
    @login_required
    def get_monthly_stats():
        """Get stats for the current month (from first day to today)."""
        start_time = time.time()
        log_request()
        uid = request.user["uid"]
        _db = get_db()
        
        # Use timezone-aware datetime
        today = datetime.now(TZ)
        start_date = today.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        end_date = today
        
        body, status = stats_service.get_stats_by_date_range(
            uid, start_date.isoformat(), end_date.isoformat(), _db
        )
        log_response(status, start_time)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

