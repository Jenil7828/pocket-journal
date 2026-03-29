"""
Domain-based API routes for Insights.

Unified endpoints:
  POST   /api/v1/insights/generate   - Generate insights
  GET    /api/v1/insights            - List insights
  GET    /api/v1/insights/{id}       - Get single insight
  DELETE /api/v1/insights/{id}       - Delete insight
"""

import time
from flask import request, jsonify
from utils.logging_utils import log_request, log_response


def register(app, deps):
    """Register domain-based insights routes."""
    login_required = deps["login_required"]
    insights_service = deps["insights_service"]
    get_db = deps["get_db"]

    # ==================== CREATE ====================

    @app.route("/api/v1/insights/generate", methods=["POST"])
    @login_required
    def generate_insights():
        """Generate insights from journal entries."""
        start_time = time.time()
        log_request()
        data = request.get_json() or {}
        body, status = insights_service.generate_insights(
            request.user,
            data,
            get_db(),
            enable_llm=deps.get("ENABLE_LLM", False),
            enable_insights=deps.get("ENABLE_INSIGHTS", True),
            insights_predictor=deps.get("INSIGHTS_PREDICTOR"),
        )
        log_response(status, start_time)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    # ==================== READ ====================

    @app.route("/api/v1/insights", methods=["GET"])
    @login_required
    def list_insights():
        """List all insights for the user."""
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

    @app.route("/api/v1/insights/<insight_id>", methods=["GET"])
    @login_required
    def get_insight(insight_id):
        """Get a single insight."""
        start_time = time.time()
        log_request()
        uid = request.user["uid"]
        _db = get_db()
        body, status = insights_service.get_insight(insight_id, uid, _db)
        log_response(status, start_time)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    @app.route("/api/v1/insights/date-range", methods=["GET"])
    @login_required
    def get_insights_by_date_range():
        """Get insights for a specific date range."""
        start_time = time.time()
        log_request()
        uid = request.user["uid"]
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        
        if not start_date or not end_date:
            log_response(400, start_time)
            return jsonify({"error": "start_date and end_date are required"}), 400
        
        _db = get_db()
        body, status = insights_service.get_insights_by_date_range(uid, start_date, end_date, _db)
        log_response(status, start_time)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    # ==================== DELETE ====================

    @app.route("/api/v1/insights/<insight_id>", methods=["DELETE"])
    @login_required
    def delete_insight(insight_id):
        """Delete an insight."""
        start_time = time.time()
        log_request()
        uid = request.user["uid"]
        _db = get_db()
        body, status = insights_service.delete_insight(insight_id, uid, _db)
        log_response(status, start_time)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)
