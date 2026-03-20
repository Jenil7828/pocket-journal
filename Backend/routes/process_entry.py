from flask import request, jsonify


def register(app, deps):
    login_required = deps["login_required"]
    journal_entries = deps["journal_entries"]
    get_db = deps["get_db"]
    PREDICTOR = deps.get("PREDICTOR")
    SUMMARIZER = deps.get("SUMMARIZER")

    @app.route("/api/v1/process_entry", methods=["POST"])
    @login_required
    def process_entry_route():
        data = request.get_json()
        body, status = journal_entries.process_entry(
            request.user,
            data,
            get_db(),
            PREDICTOR or deps["get_predictor"](),
            SUMMARIZER or deps["get_summarizer"](),
        )
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)
