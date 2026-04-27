"""
Dashboard Routes - 3 Production Endpoints

Endpoints:
1. GET /api/v1/dashboard   → Home screen (greeting, summary, motivation)
2. GET /api/v1/journey     → Journey screen (AI insights, goals, moods)
3. GET /api/v1/activity    → Recent activity (journal + media merged)

AI Cache System:
- Firestore: dashboard_cache/{uid}
- Generated daily at 2 AM (scheduled job, NOT in APIs)
- 24-hour validity window
- Fallback to rule-based synthesis if AI fails

Hard Constraints:
- No fabricated data
- No fake goals
- Only real aggregation
- Strict goal extraction from insight.goals[]
"""

import time
import logging
from flask import request, jsonify
from utils.logging_utils import log_request, log_response

logger = logging.getLogger()


def register(app, deps: dict):
    """Register all dashboard routes."""
    login_required = deps["login_required"]
    get_db = deps["get_db"]
    
    # ========================
    # ENDPOINT 1: HOME SCREEN
    # ========================
    @app.route("/api/v1/dashboard", methods=["GET"])
    @login_required
    def dashboard():
        """
        GET /api/v1/dashboard
        
        Home screen: greeting, insight preview, summary, motivation
        """
        start_time = time.time()
        log_request()
        
        try:
            uid = request.user["uid"]
            _db = get_db()
            
            from services.dashboard_service import get_dashboard
            body, status = get_dashboard(uid, _db)
            
            log_response(status, start_time)
            return jsonify(body), status
        
        except Exception as e:
            logger.exception("Dashboard error: %s", str(e))
            log_response(500, start_time)
            return jsonify({"error": str(e)}), 500
    
    # ========================
    # ENDPOINT 2: JOURNEY SCREEN
    # ========================
    @app.route("/api/v1/journey", methods=["GET"])
    @login_required
    def journey():
        """
        GET /api/v1/journey?period=7d|30d
        
        Journey screen: AI insights, goals, moods, behavioral patterns
        """
        start_time = time.time()
        log_request()
        
        try:
            uid = request.user["uid"]
            _db = get_db()
            
            period = request.args.get("period", "7d")
            if period not in ["7d", "30d"]:
                period = "7d"
            
            from services.dashboard_service import get_journey
            body, status = get_journey(uid, _db, period)
            
            log_response(status, start_time)
            return jsonify(body), status
        
        except Exception as e:
            logger.exception("Journey error: %s", str(e))
            log_response(500, start_time)
            return jsonify({"error": str(e)}), 500
    
    # ========================
    # ENDPOINT 3: RECENT ACTIVITY
    # ========================
    @app.route("/api/v1/activity", methods=["GET"])
    @login_required
    def activity():
        """
        GET /api/v1/activity
        
        Recent activity: merged journal entries + media interactions (limit 10)
        """
        start_time = time.time()
        log_request()
        
        try:
            uid = request.user["uid"]
            _db = get_db()
            
            limit = request.args.get("limit", 10, type=int)
            if limit > 50:
                limit = 50
            if limit < 1:
                limit = 10
            
            from services.dashboard_service import get_activity
            body, status = get_activity(uid, _db, limit)
            
            log_response(status, start_time)
            return jsonify(body), status
        
        except Exception as e:
            logger.exception("Activity error: %s", str(e))
            log_response(500, start_time)
            return jsonify({"error": str(e)}), 500




