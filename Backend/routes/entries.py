import time
from utils.logging_utils import log_request, log_response
from flask import request, jsonify


def register(app, deps):
    login_required = deps["login_required"]
    journal_entries = deps["journal_entries"]
    get_db = deps["get_db"]
    get_predictor = deps["get_predictor"]
    get_summarizer = deps["get_summarizer"]
    PREDICTOR = deps.get("PREDICTOR")
    SUMMARIZER = deps.get("SUMMARIZER")

    @app.route("/api/v1/entries/<entry_id>", methods=["DELETE"])
    @login_required
    def delete_entry(entry_id):
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

    @app.route("/api/v1/entries/batch", methods=["DELETE"])
    @login_required
    def delete_entries_batch():
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

    @app.route("/api/v1/entries/<entry_id>", methods=["PUT"])
    @login_required
    def update_entry(entry_id):
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

    @app.route("/api/v1/entries/<entry_id>/reanalyze", methods=["POST"])
    @login_required
    def reanalyze_entry(entry_id):
        start_time = time.time()
        log_request()
        uid = request.user["uid"]
        _db = get_db()
        predictor = PREDICTOR or get_predictor()
        summarizer = SUMMARIZER or get_summarizer()
        body, status = journal_entries.reanalyze_entry(entry_id, uid, _db, predictor, summarizer)
        log_response(status, start_time)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    @app.route("/api/v1/entries/<entry_id>", methods=["GET"])
    @login_required
    def get_single_entry(entry_id):
        start_time = time.time()
        log_request()
        uid = request.user["uid"]
        _db = get_db()
        body, status = journal_entries.get_single_entry(entry_id, uid, _db)
        log_response(status, start_time)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    @app.route("/api/v1/entries/<entry_id>/analysis", methods=["GET"])
    @login_required
    def get_entry_analysis(entry_id):
        start_time = time.time()
        log_request()
        uid = request.user["uid"]
        _db = get_db()
        body, status = journal_entries.get_entry_analysis(entry_id, uid, _db)
        log_response(status, start_time)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    @app.route("/api/v1/entries", methods=["GET"])
    @login_required
    def get_entries_filtered():
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
