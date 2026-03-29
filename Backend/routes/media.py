import time
from flask import request, jsonify
from config_loader import get_config
from utils.logging_utils import log_request, log_response
from services.media_recommender.recommendation import recommend_media
from services.search_service import SearchService
from services.interaction_service import InteractionService
from services.taste_vector_service import TasteVectorService

_CFG = get_config()


def register(app, deps):
    login_required = deps["login_required"]
    db = deps.get("db")

    # Extract Firestore client from DBManager if needed
    firestore_client = db.db if hasattr(db, 'db') else db

    # Initialize search service
    search_service = SearchService(db) if db else None
    
    # Initialize Phase 4 services (pass Firestore client directly)
    interaction_service = InteractionService(firestore_client) if firestore_client else None
    taste_vector_service = TasteVectorService(firestore_client) if firestore_client else None

    # Rate limit configuration
    INTERACTION_RATE_LIMIT_PER_HOUR = 10

    @app.route("/api/v1/media/interaction", methods=["POST"])
    @login_required
    def api_interaction():
        """
        Phase 4: Record user interaction with media item.

        Request body:
        {
            "media_type": "songs | movies | books | podcasts",
            "item_id": "string",
            "signal": "click | save | skip",
            "context": "recommendation | search" (optional, default: recommendation)
        }

        Response:
        {
            "status": "ok",
            "updated": true | false,
            "event_id": "string",
            "media_type": "string",
            "item_id": "string",
            "signal": "string",
            "weight": float,
            "context": "string"
        }

        Error cases:
        - Invalid media_type → 400
        - Invalid signal → 400
        - Missing required fields → 400
        - Rate limited → 200 (updated=false)
        - Service error → 500
        """
        start_time = time.time()
        log_request()

        try:
            uid = request.user["uid"]

            if not interaction_service:
                log_response(500, start_time)
                return jsonify({"error": "Interaction service not initialized"}), 500

            # Parse request body
            body = request.get_json(force=True, silent=True)
            if not body or not isinstance(body, dict):
                log_response(400, start_time)
                return jsonify({"error": "Request body must be JSON object"}), 400

            # Extract parameters
            media_type = body.get("media_type", "").strip()
            item_id = body.get("item_id", "").strip()
            signal = body.get("signal", "").strip()
            context = body.get("context", "recommendation").strip()

            # Validate
            is_valid, error_msg = interaction_service.validate_interaction(
                media_type=media_type,
                item_id=item_id,
                signal=signal,
                context=context,
            )

            if not is_valid:
                log_response(400, start_time)
                return jsonify({"error": error_msg}), 400

            # Step 0: Validate that item exists in cache (BEFORE storing event)
            if not taste_vector_service:
                log_response(500, start_time)
                return jsonify({"error": "Taste vector service not initialized"}), 500

            try:
                item_exists = taste_vector_service.item_exists_in_cache(media_type, item_id)
                if not item_exists:
                    log_response(400, start_time)
                    return jsonify({
                        "error": f"Media item '{item_id}' not found in {media_type} cache. Cannot track interaction for non-existent item."
                    }), 400
            except Exception as e:
                import logging
                logger = logging.getLogger("pocket_journal.routes.media")
                logger.warning(
                    "pocket_journal.routes.media: cache_validation_failed uid=%s media_type=%s item_id=%s error=%s",
                    uid,
                    media_type,
                    item_id,
                    str(e),
                )
                log_response(500, start_time)
                return jsonify({"error": "Failed to validate item in cache"}), 500

            # Step 1: Store interaction event
            try:
                event_data = interaction_service.store_interaction(
                    uid=uid,
                    media_type=media_type,
                    item_id=item_id,
                    signal=signal,
                    context=context,
                )
            except Exception as e:
                log_response(500, start_time)
                return jsonify({"error": f"Failed to store interaction: {str(e)}"}), 500

            # Step 2: Check rate limit
            try:
                event_count = interaction_service.count_interactions_in_period(
                    uid=uid,
                    media_type=media_type,
                    hours=1,
                )

                rate_limited = event_count > INTERACTION_RATE_LIMIT_PER_HOUR

                if rate_limited:
                    log_response(200, start_time)
                    return jsonify({
                        "status": "ok",
                        "updated": False,
                        "reason": "rate_limited",
                        "event_count": event_count,
                        "limit": INTERACTION_RATE_LIMIT_PER_HOUR,
                        **event_data,
                    }), 200

            except Exception as e:
                # Log but don't fail the request
                import logging
                logger = logging.getLogger("pocket_journal.routes.media")
                logger.warning(
                    "pocket_journal.routes.media: rate_limit_check_failed uid=%s media_type=%s error=%s",
                    uid,
                    media_type,
                    str(e),
                )
                rate_limited = False

            # Step 3: If not rate limited, update taste vector
            updated = False
            if not rate_limited and taste_vector_service:
                try:
                    weight = event_data.get("weight", 0)
                    update_result = taste_vector_service.update_taste_vector(
                        uid=uid,
                        media_type=media_type,
                        item_id=item_id,
                        weight=weight,
                    )
                    updated = update_result.get("updated", False)
                except Exception as e:
                    # Log but don't fail the request
                    import logging
                    logger = logging.getLogger("pocket_journal.routes.media")
                    logger.warning(
                        "pocket_journal.routes.media: taste_vector_update_failed uid=%s media_type=%s item_id=%s error=%s",
                        uid,
                        media_type,
                        item_id,
                        str(e),
                    )

            log_response(200, start_time)
            return jsonify({
                "status": "ok",
                "updated": updated,
                **event_data,
            }), 200

        except Exception as e:
            log_response(500, start_time)
            return jsonify({"error": str(e)}), 500

    @app.route("/api/v1/<media_type>/search", methods=["GET"])
    @login_required
    def api_search(media_type):
        """
        Unified media search endpoint with hybrid cache-first strategy.

        Path parameter:
        - media_type: songs | movies | books | podcasts

        Query parameters:
        - query: search string (required)
        - language: hindi | english | neutral (optional, for songs/podcasts only)
        - limit: int (default=20, max=50)

        Returns:
        {
            "results": [media_item1, media_item2, ...],
            "metrics": {
                "cache_hit_count": int,
                "fallback_triggered": bool,
                "cache_latency_ms": float,
                "provider_latency_ms": float,
                "final_result_count": int,
                "deduplication_count": int
            }
        }
        """
        start_time = time.time()
        log_request()

        try:
            if not search_service:
                log_response(500, start_time)
                return jsonify({"error": "Search service not initialized"}), 500

            # Normalize media_type from path
            media_type = media_type.strip().lower()
            
            # Get query parameters
            query = request.args.get("query", "").strip()
            language = request.args.get("language", "").strip().lower() or None
            limit = request.args.get("limit", 20, type=int)

            # Validate required parameters
            if not query:
                log_response(400, start_time)
                return jsonify({"error": "query parameter is required"}), 400

            if media_type not in {"songs", "movies", "books", "podcasts"}:
                log_response(400, start_time)
                return jsonify({"error": f"Invalid media_type: {media_type}. Must be one of: songs, movies, books, podcasts"}), 400

            # Perform search
            result = search_service.search(
                media_type=media_type,
                query=query,
                language=language,
                limit=limit,
            )

            log_response(200, start_time)
            return jsonify(result), 200

        except ValueError as e:
            log_response(400, start_time)
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            log_response(500, start_time)
            return jsonify({"error": str(e)}), 500

    @app.route("/api/v1/media/debug_verify", methods=["GET"])
    @login_required
    def media_debug_verify():
        """Test cache hit rates across media types."""
        start_time = time.time()
        log_request()

        try:
            uid = request.user["uid"]
            stats = {}

            for media_type in ["movies", "songs", "books"]:
                try:
                    result = recommend_media(uid=uid, media_type=media_type, top_k=5)
                    results = result.get("results", [])
                    non_null_count = len([r for r in results if r])
                    stats[media_type] = {
                        "total": len(results),
                        "non_null": non_null_count,
                        "percentage": (non_null_count / len(results) * 100) if results else 0,
                        "source": result.get("source", "unknown"),
                    }
                except Exception as e:
                    stats[media_type] = {"error": str(e)}

            log_response(200, start_time)
            return jsonify({"status": "ok", "stats": stats}), 200
        except Exception as e:
            log_response(500, start_time)
            return jsonify({"error": str(e)}), 500

    @app.route("/api/v1/media/recommend", methods=["GET"])
    @login_required
    def api_recommend():
        """Unified media recommendation endpoint."""
        start_time = time.time()
        log_request()

        try:
            uid = request.user["uid"]
            media_type = request.args.get("media_type", "movies")
            default_top_k = int(_CFG["recommendation"]["top_k"])
            top_k = request.args.get("top_k", default_top_k, type=int)
            language = request.args.get("language")
            genre = request.args.get("genre")
            year_from = request.args.get("year_from")
            year_to = request.args.get("year_to")

            filters = {}
            if language:
                filters["language"] = language
            if genre:
                filters["genre"] = genre
            if year_from:
                filters["year_from"] = year_from
            if year_to:
                filters["year_to"] = year_to

            result = recommend_media(
                uid=uid,
                media_type=media_type,
                filters=filters or None,
                top_k=top_k,
            )

            log_response(200, start_time)
            return jsonify(result), 200
        except Exception as e:
            log_response(500, start_time)
            return jsonify({"error": str(e)}), 500

    @app.route("/api/v1/movie/recommend", methods=["GET"])
    @login_required
    def movie_recommend():
        """Movie recommendation endpoint."""
        start_time = time.time()
        log_request()

        try:
            uid = request.user["uid"]
            default_limit = int(_CFG["api"]["default_limit"])
            top_k = request.args.get("limit", default_limit, type=int)

            result = recommend_media(
                uid=uid,
                media_type="movies",
                top_k=top_k,
            )

            log_response(200, start_time)
            return jsonify(result), 200
        except Exception as e:
            log_response(500, start_time)
            return jsonify({"error": str(e)}), 500

    @app.route("/api/v1/song/recommend", methods=["GET"])
    @login_required
    def song_recommend():
        """Song recommendation endpoint."""
        start_time = time.time()
        log_request()

        try:
            uid = request.user["uid"]
            default_limit = int(_CFG["api"]["default_limit"])
            top_k = request.args.get("limit", default_limit, type=int)
            language = request.args.get("language")

            filters = None
            if language:
                filters = {"language": language}

            result = recommend_media(
                uid=uid,
                media_type="songs",
                filters=filters,
                top_k=top_k,
            )

            log_response(200, start_time)
            return jsonify(result), 200
        except Exception as e:
            log_response(500, start_time)
            return jsonify({"error": str(e)}), 500

    @app.route("/api/v1/podcast/recommend", methods=["GET"])
    @login_required
    def podcast_recommend():
        """Podcast recommendation endpoint."""
        start_time = time.time()
        log_request()

        try:
            uid = request.user["uid"]
            default_limit = int(_CFG["api"]["default_limit"])
            top_k = request.args.get("limit", default_limit, type=int)
            language = request.args.get("language")
            genre = request.args.get("genre")

            filters = {}
            if language:
                filters["language"] = language
            if genre:
                filters["genre"] = genre

            result = recommend_media(
                uid=uid,
                media_type="podcasts",
                filters=filters or None,
                top_k=top_k,
            )

            log_response(200, start_time)
            return jsonify(result), 200
        except Exception as e:
            log_response(500, start_time)
            return jsonify({"error": str(e)}), 500

    @app.route("/api/v1/book/recommend", methods=["GET"])
    @login_required
    def book_recommend():
        """Book recommendation endpoint."""
        start_time = time.time()
        log_request()

        try:
            uid = request.user["uid"]
            default_limit = int(_CFG["api"]["default_limit"])
            top_k = request.args.get("limit", default_limit, type=int)

            result = recommend_media(
                uid=uid,
                media_type="books",
                top_k=top_k,
            )

            log_response(200, start_time)
            return jsonify(result), 200
        except Exception as e:
            log_response(500, start_time)
            return jsonify({"error": str(e)}), 500


