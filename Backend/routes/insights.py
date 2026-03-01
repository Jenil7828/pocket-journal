import time
from utils.logging_utils import log_request, log_response
from flask import request, jsonify


def register(app, deps):
    login_required = deps["login_required"]
    insights_service = deps["insights_service"]
    get_db = deps["get_db"]

    @app.route("/generate_insights", methods=["POST"])
    @login_required
    def generate_insights():
        start_time = time.time()
        log_request()
        data = request.get_json() or {}
        body, status = insights_service.generate_insights(
            request.user,
            data,
            get_db(),
            enable_llm=deps.get("ENABLE_LLM", False),
            enable_insights=deps.get("ENABLE_INSIGHTS", True),
        )
        log_response(status, start_time)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    @app.route("/insights", methods=["GET"])
    @login_required
    def get_insights():
        start_time = time.time()
        log_request()
        uid = request.user["uid"]
        try:
            limit = int(request.args.get("limit", 50))
            offset = int(request.args.get("offset", 0))
        except ValueError:
            log_response(400, start_time)
            return jsonify({"error": "Invalid limit or offset parameter"}), 400
        _db = get_db()
        body, status = insights_service.get_insights(uid, limit, offset, _db)
        log_response(status, start_time)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    @app.route("/insights/<insight_id>", methods=["GET"])
    @login_required
    def get_single_insight(insight_id):
        start_time = time.time()
        log_request()
        uid = request.user["uid"]
        if not insight_id:
            log_response(400, start_time)
            return jsonify({"error": "Insight ID is required"}), 400
        _db = get_db()
        body, status = insights_service.get_single_insight(insight_id, uid, _db)
        log_response(status, start_time)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    @app.route("/insights/<insight_id>", methods=["DELETE"])
    @login_required
    def delete_insight(insight_id):
        start_time = time.time()
        log_request()
        uid = request.user["uid"]
        if not insight_id:
            log_response(400, start_time)
            return jsonify({"error": "Insight ID is required"}), 400
        _db = get_db()
        body, status = insights_service.delete_insight(insight_id, uid, _db)
        log_response(status, start_time)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

