import time
from utils.logging_utils import log_request, log_response
from flask import request, jsonify


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
