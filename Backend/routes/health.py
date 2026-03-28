import time
from utils.logging_utils import log_request, log_response
from flask import jsonify


def register(app, deps):
    health_service = deps["health_service"]
    get_db = deps["get_db"]

    @app.route("/api/v1/health", methods=["GET"])
    def health_check():
        start_time = time.time()
        log_request()
        _db = get_db()
        body, status = health_service.health_check(_db)
        log_response(status, start_time)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)
