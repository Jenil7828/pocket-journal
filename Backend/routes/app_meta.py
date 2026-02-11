# routes/app_meta.py
from flask import jsonify


def register(app, deps: dict):
    @app.route("/app/about", methods=["GET"])
    def app_about():
        return jsonify({"app": "Pocket Journal", "version": "1.0", "description": "Pocket Journal backend API"}), 200

    @app.route("/app/terms", methods=["GET"])
    def app_terms():
        return jsonify({"terms": "Use responsibly. Privacy policy applies."}), 200

