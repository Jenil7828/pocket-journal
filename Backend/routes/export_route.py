import time
from utils.logging_utils import log_request, log_response
from flask import request, jsonify


def register(app, deps):
    login_required = deps["login_required"]
    export_service = deps["export_service"]
    get_db = deps["get_db"]

    @app.route("/api/v1/export", methods=["POST"])
    @login_required
    def export_data():
        start_time = time.time()
        log_request()
        uid = request.user["uid"]
        
        # Accept data from JSON body or query args
        data = request.get_json() or {}
        start_date = data.get("start_date") or request.args.get("start_date")
        end_date = data.get("end_date") or request.args.get("end_date")
        export_format = (data.get("format") or request.args.get("format", "json")).lower()

        _db = get_db()
        result = export_service.export_data(uid, start_date, end_date, export_format, _db)
        if isinstance(result, tuple) and len(result) == 3:
            log_response(result[1] if len(result) > 1 else 200, start_time)
            return result
        body, status = result
        log_response(status, start_time)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)
