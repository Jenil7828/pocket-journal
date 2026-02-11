from flask import request, jsonify


def register(app, deps):
    login_required = deps["login_required"]
    media_recommendations = deps["media_recommendations"]
    get_db = deps["get_db"]

    @app.route("/api/recommend", methods=["GET"])
    @login_required
    def api_recommend():
        mood = request.args.get("mood")
        _db = get_db()
        body, status = media_recommendations.recommend_movies_for_mood(mood)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    @app.route("/movie/recommend", methods=["GET"])
    @login_required
    def movie_recommend():
        uid = request.user["uid"]
        _db = get_db()
        body, status = media_recommendations.recommend_movies_for_user(uid, _db)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    @app.route("/song/recommend", methods=["GET"])
    @login_required
    def song_recommend():
        uid = request.user["uid"]
        try:
            limit = int(request.args.get("limit", 10))
        except ValueError:
            return jsonify({"error": "Invalid limit"}), 400
        language = request.args.get("language", "both")
        _db = get_db()
        body, status = media_recommendations.recommend_songs_for_user(uid, limit, language, _db)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    @app.route("/book/recommend", methods=["GET"])
    @login_required
    def book_recommend():
        uid = request.user["uid"]
        _db = get_db()
        body, status = media_recommendations.recommend_books_for_user(uid, _db)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    @app.route("/api/search", methods=["GET"])
    @login_required
    def api_search():
        q = request.args.get("movie")
        _db = get_db()
        body, status = media_recommendations.search_movies(q)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    @app.route("/api/songs", methods=["GET"])
    @login_required
    def get_songs():
        mood = request.args.get("mood", "happy").lower()
        language = request.args.get("language", "both").lower()
        try:
            limit = int(request.args.get("limit", 10))
        except ValueError:
            return jsonify({"error": "Invalid limit"}), 400
        body, status = media_recommendations.get_songs(mood, language, limit)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    @app.route("/api/search_song", methods=["GET"])
    @login_required
    def api_search_song():
        query = request.args.get("q")
        search_type = (request.args.get("type") or "track").lower()
        try:
            limit = int(request.args.get("limit", 10))
        except ValueError:
            return jsonify({"error": "Invalid limit"}), 400
        body, status = media_recommendations.search_songs(query, search_type, limit)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    @app.route("/api/books", methods=["GET"])
    @login_required
    def get_books_by_emotion():
        emotion = request.args.get("emotion", "happy").lower()
        try:
            limit = int(request.args.get("limit", 5))
        except ValueError:
            return jsonify({"error": "Invalid limit"}), 400
        body, status = media_recommendations.books_by_emotion(emotion, limit)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

    @app.route("/api/search_books", methods=["GET"])
    @login_required
    def api_search_books():
        query = request.args.get("query")
        search_type = (request.args.get("type") or "both").lower()
        try:
            max_results = int(request.args.get("limit", 10))
        except ValueError:
            return jsonify({"error": "Invalid limit"}), 400
        body, status = media_recommendations.search_books(query, search_type, max_results)
        return (jsonify(body), status) if isinstance(body, dict) else (body, status)

