from flask import jsonify, request
import time
from .logging_utils import log_request, log_response

from services.media_recommender.recommendation import recommend_media


def register(app, deps):
    login_required = deps["login_required"]

    
    @app.route("/api/media/debug_verify", methods=["GET"])
    @login_required
    def api_media_debug_verify():
        start_time = time.time()
        log_request()
        """Temporary debug endpoint to verify image fields in recommendations."""
        uid = request.user["uid"]
        results = {}
        types = ["movies", "songs", "books"]
        fields = {
            "movies": "poster_url",
            "songs": "album_image_url",
            "books": "thumbnail_url",
        }
        for media_type in types:
            try:
                rec = recommend_media(uid=uid, media_type=media_type, top_k=10)
                items = rec.get("results") or rec.get("items") or []
                field = fields[media_type]
                non_null = [item for item in items if item.get(field)]
                percent = (len(non_null) / max(1, len(items))) * 100
                results[media_type] = {
                    "total": len(items),
                    "non_null_count": len(non_null),
                    "percent_non_null": percent,
                    "first_result": items[0] if items else None,
                }
                # Log first result at INFO level
                if items:
                    import logging
                    logger = logging.getLogger("pocket_journal.media.debug_verify")
                    logger.info(f"{media_type} first result: %s", items[0])
            except Exception as exc:
                results[media_type] = {"error": str(exc)}
        # Assert at least 80% non-null for each type
        assertions = {mt: (res.get("percent_non_null", 0) >= 80) for mt, res in results.items() if "percent_non_null" in res}
        results["assertions"] = assertions
        log_response(200, start_time)
        return jsonify(results), 200
    
    @app.route("/api/media/recommend", methods=["GET"])
    @login_required
    def api_media_recommend():
        start_time = time.time()
        log_request()
        """
        Unified media recommendation endpoint.

        Query params:
        - media_type: one of [movies, songs, books, podcasts]
        - top_k (optional): override number of results (default 10)
        - Optional filters (language, genre, year_from, year_to)
        """
        uid = request.user["uid"]
        media_type = (request.args.get("media_type") or "").strip().lower()
        if not media_type:
            log_response(400, start_time)
            return jsonify({"error": "Missing media_type parameter"}), 400
        try:
            top_k = int(request.args.get("top_k", 10))
        except ValueError:
            log_response(400, start_time)
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
                log_response(400, start_time)
                return jsonify({"error": "Invalid year_from"}), 400
        year_to = request.args.get("year_to")
        if year_to:
            try:
                filters["year_to"] = int(year_to)
            except ValueError:
                log_response(400, start_time)
                return jsonify({"error": "Invalid year_to"}), 400

        try:
            result = recommend_media(
                uid=uid, media_type=media_type, filters=filters or None, top_k=top_k
            )
        except ValueError as ve:
            log_response(400, start_time)
            return jsonify({"error": str(ve)}), 400
        except Exception as exc:
            log_response(500, start_time)
            return jsonify(
                {"error": "Failed to generate recommendations", "details": str(exc)}
            ), 500

        log_response(200, start_time)
        return jsonify(result), 200

    @app.route("/movie/recommend", methods=["GET"])
    @login_required
    def movie_recommend():
        start_time = time.time()
        log_request()
        """Backward compatible movie endpoint backed by unified engine."""
        uid = request.user["uid"]
        try:
            top_k = int(request.args.get("limit", 10))
        except ValueError:
            log_response(400, start_time)
            return jsonify({"error": "Invalid limit"}), 400
        try:
            result = recommend_media(uid=uid, media_type="movies", top_k=top_k)
        except ValueError as ve:
            log_response(400, start_time)
            return jsonify({"error": str(ve)}), 400
        except Exception as exc:
            log_response(500, start_time)
            return jsonify(
                {"error": "Failed to generate movie recommendations", "details": str(exc)}
            ), 500
        log_response(200, start_time)
        return jsonify(result), 200

    @app.route("/song/recommend", methods=["GET"])
    @login_required
    def song_recommend():
        start_time = time.time()
        log_request()
        """Backward compatible song endpoint backed by unified engine.

        Existing `limit` param is treated as the desired top_k.
        Language parameter is forwarded as a request-scoped filter.
        """
        uid = request.user["uid"]
        try:
            top_k = int(request.args.get("limit", 10))
        except ValueError:
            log_response(400, start_time)
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
            log_response(400, start_time)
            return jsonify({"error": str(ve)}), 400
        except Exception as exc:
            log_response(500, start_time)
            return jsonify(
                {"error": "Failed to generate song recommendations", "details": str(exc)}
            ), 500
        log_response(200, start_time)
        return jsonify(result), 200

    @app.route("/book/recommend", methods=["GET"])
    @login_required
    def book_recommend():
        start_time = time.time()
        log_request()
        """Backward compatible book endpoint backed by unified engine."""
        uid = request.user["uid"]
        try:
            top_k = int(request.args.get("limit", 10))
        except ValueError:
            log_response(400, start_time)
            return jsonify({"error": "Invalid limit"}), 400
        try:
            result = recommend_media(uid=uid, media_type="books", top_k=top_k)
        except ValueError as ve:
            log_response(400, start_time)
            return jsonify({"error": str(ve)}), 400
        except Exception as exc:
            log_response(500, start_time)
            return jsonify(
                {"error": "Failed to generate book recommendations", "details": str(exc)}
            ), 500
        log_response(200, start_time)
        return jsonify(result), 200

