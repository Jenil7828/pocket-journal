from flask import request, jsonify


def register(app, deps):
    login_required = deps["login_required"]
    insights_service = deps["insights_service"]
    get_db = deps["get_db"]

    @app.route("/generate_insights", methods=["POST"])
    @login_required
    def generate_insights():
        data = request.get_json() or {}
        body, status = insights_service.generate_insights(
            request.user,
            data,
            get_db(),
            enable_llm=deps.get("ENABLE_LLM", False),
            enable_insights=deps.get("ENABLE_INSIGHTS", True),
        )
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    @app.route("/insights", methods=["GET"])
    @login_required
    def get_insights():
        uid = request.user["uid"]
        try:
            limit = int(request.args.get("limit", 50))
            offset = int(request.args.get("offset", 0))
        except ValueError:
            return jsonify({"error": "Invalid limit or offset parameter"}), 400
        _db = get_db()
        body, status = insights_service.get_insights(uid, limit, offset, _db)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    @app.route("/insights/<insight_id>", methods=["GET"])
    @login_required
    def get_single_insight(insight_id):
        uid = request.user["uid"]
        if not insight_id:
            return jsonify({"error": "Insight ID is required"}), 400
        _db = get_db()
        body, status = insights_service.get_single_insight(insight_id, uid, _db)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    @app.route("/insights/<insight_id>", methods=["DELETE"])
    @login_required
    def delete_insight(insight_id):
        uid = request.user["uid"]
        if not insight_id:
            return jsonify({"error": "Insight ID is required"}), 400
        _db = get_db()
        body, status = insights_service.delete_insight(insight_id, uid, _db)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

