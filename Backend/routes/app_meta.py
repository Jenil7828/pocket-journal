import time
from utils.logging_utils import log_request, log_response
# routes/app_meta.py
from flask import jsonify


def register(app, deps: dict):
    @app.route("/app/about", methods=["GET"])
    def app_about():
        start_time = time.time()
        log_request()
        log_response(200, start_time)
        return jsonify({"app": "Pocket Journal", "version": "1.0", "description": "Pocket Journal backend API"}), 200

    @app.route("/app/terms", methods=["GET"])
    def app_terms():
        start_time = time.time()
        log_request()
        log_response(200, start_time)
        return jsonify({"terms": "Use responsibly. Privacy policy applies."}), 200

