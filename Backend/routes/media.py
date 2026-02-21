from flask import jsonify, request

from services.media_recommender.recommendation import recommend_media


def register(app, deps):
    login_required = deps["login_required"]

    @app.route("/api/media/recommend", methods=["GET"])
    @login_required
    def api_media_recommend():
        """Unified media recommendation endpoint.

        Query params:
        - media_type: one of [movies, songs, books, podcasts]
        - top_k (optional): override number of results (default 10)
        - Optional filters (language, genre, year_from, year_to)
        """
        uid = request.user["uid"]
        media_type = (request.args.get("media_type") or "").strip().lower()
        if not media_type:
            return jsonify({"error": "Missing media_type parameter"}), 400
        try:
            top_k = int(request.args.get("top_k", 10))
        except ValueError:
            return jsonify({"error": "Invalid top_k"}), 400

        # Parse request-scoped filters
        filters = {}
        language = request.args.get("language")
        if language:
            filters["language"] = language.strip()
        genre = request.args.get("genre")
        if genre:
            filters["genre"] = genre.strip()
        year_from = request.args.get("year_from")
        if year_from:
            try:
                filters["year_from"] = int(year_from)
            except ValueError:
                return jsonify({"error": "Invalid year_from"}), 400
        year_to = request.args.get("year_to")
        if year_to:
            try:
                filters["year_to"] = int(year_to)
            except ValueError:
                return jsonify({"error": "Invalid year_to"}), 400

        try:
            result = recommend_media(
                uid=uid, media_type=media_type, filters=filters or None, top_k=top_k
            )
        except ValueError as ve:
            return jsonify({"error": str(ve)}), 400
        except Exception as exc:
            return jsonify(
                {"error": "Failed to generate recommendations", "details": str(exc)}
            ), 500

        return jsonify(result), 200

    @app.route("/movie/recommend", methods=["GET"])
    @login_required
    def movie_recommend():
        """Backward compatible movie endpoint backed by unified engine."""
        uid = request.user["uid"]
        try:
            top_k = int(request.args.get("limit", 10))
        except ValueError:
            return jsonify({"error": "Invalid limit"}), 400
        try:
            result = recommend_media(uid=uid, media_type="movies", top_k=top_k)
        except ValueError as ve:
            return jsonify({"error": str(ve)}), 400
        except Exception as exc:
            return jsonify(
                {"error": "Failed to generate movie recommendations", "details": str(exc)}
            ), 500
        return jsonify(result), 200

    @app.route("/song/recommend", methods=["GET"])
    @login_required
    def song_recommend():
        """Backward compatible song endpoint backed by unified engine.

        Existing `limit` param is treated as the desired top_k.
        Language parameter is forwarded as a request-scoped filter.
        """
        uid = request.user["uid"]
        try:
            top_k = int(request.args.get("limit", 10))
        except ValueError:
            return jsonify({"error": "Invalid limit"}), 400
        language = (request.args.get("language") or "").strip().lower()
        filters = {}
        if language:
            filters["language"] = language

        try:
            result = recommend_media(
                uid=uid, media_type="songs", filters=filters or None, top_k=top_k
            )
        except ValueError as ve:
            return jsonify({"error": str(ve)}), 400
        except Exception as exc:
            return jsonify(
                {"error": "Failed to generate song recommendations", "details": str(exc)}
            ), 500
        return jsonify(result), 200

    @app.route("/book/recommend", methods=["GET"])
    @login_required
    def book_recommend():
        """Backward compatible book endpoint backed by unified engine."""
        uid = request.user["uid"]
        try:
            top_k = int(request.args.get("limit", 10))
        except ValueError:
            return jsonify({"error": "Invalid limit"}), 400
        try:
            result = recommend_media(uid=uid, media_type="books", top_k=top_k)
        except ValueError as ve:
            return jsonify({"error": str(ve)}), 400
        except Exception as exc:
            return jsonify(
                {"error": "Failed to generate book recommendations", "details": str(exc)}
            ), 500
        return jsonify(result), 200

