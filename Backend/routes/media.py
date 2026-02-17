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
        """
        uid = request.user["uid"]
        media_type = (request.args.get("media_type") or "").strip().lower()
        if not media_type:
            return jsonify({"error": "Missing media_type parameter"}), 400
        try:
            top_k = int(request.args.get("top_k", 10))
        except ValueError:
            return jsonify({"error": "Invalid top_k"}), 400

        try:
            result = recommend_media(uid=uid, media_type=media_type, top_k=top_k)
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
        Language parameter is ignored in Phase 2 per embedding-first design.
        """
        uid = request.user["uid"]
        try:
            top_k = int(request.args.get("limit", 10))
        except ValueError:
            return jsonify({"error": "Invalid limit"}), 400
        language = (request.args.get("language", "both") or "both").strip().lower()
        # Encode language into media_type so the Spotify provider can bias by market
        media_key = "songs"
        if language and language not in ("both", "all"):
            media_key = f"{media_key}:{language}"

        try:
            result = recommend_media(uid=uid, media_type=media_key, top_k=top_k)
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

