from flask import jsonify


def register(app, deps):
    health_service = deps["health_service"]
    get_db = deps["get_db"]

    @app.route("/health", methods=["GET"])
    def health_check():
        _db = get_db()
        body, status = health_service.health_check(_db)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

