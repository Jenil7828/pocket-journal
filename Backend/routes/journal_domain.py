"""
Domain-based API routes for Journal entries.

Unified endpoints:
  POST   /api/v1/journal           - Create entry
  GET    /api/v1/journal           - List entries
  GET    /api/v1/journal/search    - Search entries
  GET    /api/v1/journal/{id}      - Get single entry
  PUT    /api/v1/journal/{id}      - Update entry
  DELETE /api/v1/journal/{id}      - Delete entry
"""

import time
from flask import request, jsonify
from utils.logging_utils import log_request, log_response


def register(app, deps):
    """Register domain-based journal routes."""
    login_required = deps["login_required"]
    journal_entries = deps["journal_entries"]
    get_db = deps["get_db"]
    get_predictor = deps["get_predictor"]
    get_summarizer = deps["get_summarizer"]
    PREDICTOR = deps.get("PREDICTOR")
    SUMMARIZER = deps.get("SUMMARIZER")

    # ==================== CREATE ====================

    @app.route("/api/v1/journal", methods=["POST"])
    @login_required
    def create_journal_entry():
        """Create a new journal entry."""
        start_time = time.time()
        log_request()
        data = request.get_json()
        body, status = journal_entries.process_entry(
            request.user,
            data,
            get_db(),
            PREDICTOR or get_predictor(),
            SUMMARIZER or get_summarizer(),
        )
        log_response(status, start_time)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    # ==================== READ ====================

    @app.route("/api/v1/journal", methods=["GET"])
    @login_required
    def list_journal_entries():
        """List all journal entries with optional filtering."""
        start_time = time.time()
        log_request()
        uid = request.user["uid"]
        params = {
            "start_date": request.args.get("start_date"),
            "end_date": request.args.get("end_date"),
            "mood": request.args.get("mood"),
            "search": request.args.get("search"),
            "limit": request.args.get("limit", 50),
            "offset": request.args.get("offset", 0),
        }
        _db = get_db()
        body, status = journal_entries.get_entries_filtered(uid, params, _db)
        log_response(status, start_time)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    @app.route("/api/v1/journal/search", methods=["GET"])
    @login_required
    def search_journal_entries():
        """Search journal entries with fuzzy matching."""
        start_time = time.time()
        log_request()
        uid = request.user["uid"]
        query = request.args.get("query", "").strip()
        start_date = request.args.get("start_date", "").strip()
        end_date = request.args.get("end_date", "").strip()
        try:
            limit = int(request.args.get("limit", 20))
        except ValueError:
            log_response(400, start_time)
            return jsonify({"error": "Invalid limit parameter"}), 400
        
        if limit < 1 or limit > 50:
            log_response(400, start_time)
            return jsonify({"error": "Limit must be between 1 and 50"}), 400
        
        # Inline search implementation
        from datetime import datetime
        import pytz
        from firebase_admin import firestore
        
        def search_entries(uid, query, start_date, end_date, limit, db):
            """Search journal entries by text and date filters."""
            try:
                _db = db.db if hasattr(db, 'db') else db
                _COLS = db.config["firestore"]["collections"] if hasattr(db, 'config') else {"journal_entries": "journal_entries"}
                
                # Build base query
                q = _db.collection(_COLS.get("journal_entries", "journal_entries")).where(
                    filter=firestore.FieldFilter("uid", "==", uid)
                )
                
                # Add date filters
                if start_date:
                    try:
                        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                        IST = pytz.timezone("Asia/Kolkata")
                        start_dt = IST.localize(start_dt.replace(hour=0, minute=0, second=0))
                        q = q.where(filter=firestore.FieldFilter("created_at", ">=", start_dt))
                    except ValueError:
                        return [], 0, "Invalid start_date format. Use YYYY-MM-DD"
                
                if end_date:
                    try:
                        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                        IST = pytz.timezone("Asia/Kolkata")
                        end_dt = IST.localize(end_dt.replace(hour=23, minute=59, second=59))
                        q = q.where(filter=firestore.FieldFilter("created_at", "<=", end_dt))
                    except ValueError:
                        return [], 0, "Invalid end_date format. Use YYYY-MM-DD"
                
                # Get all entries
                docs = q.order_by("created_at", direction=firestore.Query.DESCENDING).stream()
                
                results = []
                for doc in docs:
                    entry = doc.to_dict()
                    entry["entry_id"] = doc.id
                    
                    # Filter by query text if provided
                    if query:
                        text = entry.get("entry_text", "").lower()
                        summary = entry.get("summary", "").lower()
                        title = entry.get("title", "").lower()
                        search_term = query.lower()
                        
                        # Simple text matching (can be enhanced with fuzzy matching)
                        if search_term not in text and search_term not in summary and search_term not in title:
                            continue
                    
                    results.append(entry)
                
                total_count = len(results)
                results = results[:limit]
                
                return results, total_count, None
            except Exception as e:
                return [], 0, str(e)
        
        _db = get_db()
        results, total_count, error_msg = search_entries(
            uid=uid,
            query=query if query else None,
            start_date=start_date if start_date else None,
            end_date=end_date if end_date else None,
            limit=limit,
            db=_db
        )
        
        if error_msg:
            log_response(500, start_time)
            return jsonify({"error": error_msg}), 500
        
        response = {
            "results": results,
            "count": len(results),
            "total_count": total_count,
            "filters": {
                "query": query if query else None,
                "start_date": start_date if start_date else None,
                "end_date": end_date if end_date else None,
                "limit": limit
            }
        }
        
        log_response(200, start_time)
        return jsonify(response), 200

    @app.route("/api/v1/journal/<entry_id>", methods=["GET"])
    @login_required
    def get_journal_entry(entry_id):
        """Get a single journal entry."""
        start_time = time.time()
        log_request()
        uid = request.user["uid"]
        _db = get_db()
        body, status = journal_entries.get_single_entry(entry_id, uid, _db)
        log_response(status, start_time)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    @app.route("/api/v1/journal/all", methods=["GET"])
    @login_required
    def list_all_journal_entries():
        """Get ALL journal entries for user (no filters, sorted by date DESC)."""
        start_time = time.time()
        log_request()
        uid = request.user["uid"]
        _db = get_db()
        body, status = journal_entries.get_all_entries(uid, _db)
        log_response(status, start_time)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    @app.route("/api/v1/journal/<entry_id>/analysis", methods=["GET"])
    @login_required
    def get_journal_entry_analysis(entry_id):
        """Get analysis for a journal entry."""
        start_time = time.time()
        log_request()
        uid = request.user["uid"]
        _db = get_db()
        body, status = journal_entries.get_entry_analysis(entry_id, uid, _db)
        log_response(status, start_time)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    # ==================== UPDATE ====================

    @app.route("/api/v1/journal/<entry_id>", methods=["PUT"])
    @login_required
    def update_journal_entry(entry_id):
        """Update an existing journal entry (full update with analysis)."""
        start_time = time.time()
        log_request()
        uid = request.user["uid"]
        data = request.get_json()
        _db = get_db()
        predictor = PREDICTOR or get_predictor()
        summarizer = SUMMARIZER or get_summarizer()
        body, status = journal_entries.update_entry(entry_id, uid, data, _db, predictor, summarizer)
        log_response(status, start_time)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    @app.route("/api/v1/journal/<entry_id>/content", methods=["PUT"])
    @login_required
    def update_journal_entry_content_only(entry_id):
        """Update entry_text and/or title WITHOUT triggering analysis."""
        start_time = time.time()
        log_request()
        uid = request.user["uid"]
        data = request.get_json()
        if not data or (not data.get("entry_text") and not data.get("title")):
            log_response(400, start_time)
            return jsonify({"error": "Must provide entry_text and/or title"}), 400
        
        _db = get_db()
        body, status = journal_entries.update_entry_content_only(entry_id, uid, data, _db)
        log_response(status, start_time)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    @app.route("/api/v1/journal/<entry_id>/reanalyze", methods=["POST"])
    @login_required
    def reanalyze_journal_entry(entry_id):
        """Reanalyze a journal entry."""
        start_time = time.time()
        log_request()
        uid = request.user["uid"]
        _db = get_db()
        predictor = PREDICTOR or get_predictor()
        summarizer = SUMMARIZER or get_summarizer()
        body, status = journal_entries.reanalyze_entry(entry_id, uid, _db, predictor, summarizer)
        log_response(status, start_time)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    # ==================== DELETE ====================

    @app.route("/api/v1/journal/<entry_id>", methods=["DELETE"])
    @login_required
    def delete_journal_entry(entry_id):
        """Delete a journal entry."""
        start_time = time.time()
        log_request()
        uid = request.user["uid"]
        if not entry_id:
            log_response(400, start_time)
            return jsonify({"error": "Entry ID is required"}), 400
        _db = get_db()
        body, status = journal_entries.delete_entry(entry_id, uid, _db)
        log_response(status, start_time)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    @app.route("/api/v1/journal/batch", methods=["DELETE"])
    @login_required
    def delete_journal_entries_batch():
        """Delete multiple journal entries."""
        start_time = time.time()
        log_request()
        uid = request.user["uid"]
        data = request.get_json()
        if not data or "entry_ids" not in data:
            log_response(400, start_time)
            return jsonify({"error": "Missing entry_ids in request body"}), 400
        entry_ids = data["entry_ids"]
        if not isinstance(entry_ids, list) or len(entry_ids) == 0:
            log_response(400, start_time)
            return jsonify({"error": "entry_ids must be a non-empty array"}), 400
        _db = get_db()
        body, status = journal_entries.delete_entries_batch(entry_ids, uid, _db)
        log_response(status, start_time)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    # ==================== STREAK ====================

    @app.route("/api/v1/streak", methods=["GET"])
    @login_required
    def get_user_streak():
        """Get user's writing streak metrics."""
        start_time = time.time()
        log_request()
        uid = request.user["uid"]
        _db = get_db()
        
        from services.analytics.streak_service import calculate_streak
        body, status = calculate_streak(uid, _db)
        
        log_response(status, start_time)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)



