from flask import request, jsonify


def register(app, deps):
    login_required = deps["login_required"]
    stats_service = deps["stats_service"]
    get_db = deps["get_db"]

    @app.route("/stats", methods=["GET"])
    @login_required
    def get_user_stats():
        uid = request.user["uid"]
        _db = get_db()
        body, status = stats_service.get_user_stats(uid, _db)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    @app.route("/mood-trends", methods=["GET"])
    @login_required
    def get_mood_trends():
        uid = request.user["uid"]
        try:
            days = int(request.args.get("days", 30))
        except ValueError:
            return jsonify({"error": "Invalid days parameter"}), 400
        _db = get_db()
        body, status = stats_service.get_mood_trends(uid, days, _db)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

