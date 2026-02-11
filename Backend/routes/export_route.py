from flask import request, jsonify


def register(app, deps):
    login_required = deps["login_required"]
    export_service = deps["export_service"]
    get_db = deps["get_db"]

    @app.route("/export", methods=["GET"])
    @login_required
    def export_data():
        uid = request.user["uid"]
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        export_format = request.args.get("format", "json").lower()

        _db = get_db()
        result = export_service.export_data(uid, start_date, end_date, export_format, _db)
        if isinstance(result, tuple) and len(result) == 3:
            return result
        body, status = result
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

