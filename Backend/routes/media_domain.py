"""
Domain-based API routes for Media recommendations.

Domain-specific endpoints (NOT merged):
  GET  /api/v1/movies/recommend     - Get movie recommendations
  GET  /api/v1/songs/recommend      - Get song recommendations
  GET  /api/v1/books/recommend      - Get book recommendations
  GET  /api/v1/podcasts/recommend   - Get podcast recommendations

Search endpoints:
  GET  /api/v1/{media_type}/search  - Search media (movies|songs|books|podcasts)

Interaction endpoints:
  POST /api/v1/media/interaction    - Track user interaction
"""

import time
from flask import request, jsonify
from config_loader import get_config
from utils.logging_utils import log_request, log_response
from services.media_recommender.recommendation import recommend_media
from services.media_recommender.search_service import SearchService
from services.personalization.interaction_service import InteractionService
from services.personalization.taste_vector_service import TasteVectorService

_CFG = get_config()


def register(app, deps):
    """Register domain-based media routes."""
    login_required = deps["login_required"]
    db = deps.get("db")

    # Extract Firestore client from DBManager if needed
    firestore_client = db.db if hasattr(db, 'db') else db

    # Initialize services
    search_service = SearchService(db) if db else None
    interaction_service = InteractionService(firestore_client) if firestore_client else None
    taste_vector_service = TasteVectorService(firestore_client) if firestore_client else None

    # Rate limit configuration
    INTERACTION_RATE_LIMIT_PER_HOUR = 10

    # ==================== RECOMMENDATIONS (Domain-Specific) ====================
    # Keep separate endpoints for each media type (do NOT merge)

    @app.route("/api/v1/movies/recommend", methods=["GET"])
    @login_required
    def recommend_movies():
        """Get movie recommendations based on user taste profile."""
        start_time = time.time()
        log_request()

        try:
            uid = request.user["uid"]
            default_limit = int(_CFG["api"]["default_limit"])
            limit = request.args.get("limit", default_limit, type=int)

            result = recommend_media(
                uid=uid,
                media_type="movies",
                top_k=limit,
            )

            log_response(200, start_time)
            return jsonify(result), 200
        except Exception as e:
            log_response(500, start_time)
            return jsonify({"error": str(e)}), 500

    @app.route("/api/v1/songs/recommend", methods=["GET"])
    @login_required
    def recommend_songs():
        """Get song recommendations based on user taste profile."""
        start_time = time.time()
        log_request()

        try:
            uid = request.user["uid"]
            default_limit = int(_CFG["api"]["default_limit"])
            limit = request.args.get("limit", default_limit, type=int)
            language = request.args.get("language")

            filters = None
            if language:
                filters = {"language": language}

            result = recommend_media(
                uid=uid,
                media_type="songs",
                filters=filters,
                top_k=limit,
            )

            log_response(200, start_time)
            return jsonify(result), 200
        except Exception as e:
            log_response(500, start_time)
            return jsonify({"error": str(e)}), 500

    @app.route("/api/v1/books/recommend", methods=["GET"])
    @login_required
    def recommend_books():
        """Get book recommendations based on user taste profile."""
        start_time = time.time()
        log_request()

        try:
            uid = request.user["uid"]
            default_limit = int(_CFG["api"]["default_limit"])
            limit = request.args.get("limit", default_limit, type=int)

            result = recommend_media(
                uid=uid,
                media_type="books",
                top_k=limit,
            )

            log_response(200, start_time)
            return jsonify(result), 200
        except Exception as e:
            log_response(500, start_time)
            return jsonify({"error": str(e)}), 500

    @app.route("/api/v1/podcasts/recommend", methods=["GET"])
    @login_required
    def recommend_podcasts():
        """Get podcast recommendations based on user taste profile."""
        start_time = time.time()
        log_request()

        try:
            uid = request.user["uid"]
            default_limit = int(_CFG["api"]["default_limit"])
            limit = request.args.get("limit", default_limit, type=int)
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
                top_k=limit,
            )

            log_response(200, start_time)
            return jsonify(result), 200
        except Exception as e:
            log_response(500, start_time)
            return jsonify({"error": str(e)}), 500

    # ==================== SEARCH (Generic by Media Type) ====================

    @app.route("/api/v1/<media_type>/search", methods=["GET"])
    @login_required
    def search_media(media_type):
        """
        Search media by type with hybrid cache-first strategy.

        Path parameter:
        - media_type: songs | movies | books | podcasts

        Query parameters:
        - query: search string (required)
        - language: hindi | english | neutral (optional, for songs/podcasts)
        - limit: int (default=20, max=50)

        Returns: {results: [...], metrics: {...}}
        """
        start_time = time.time()
        log_request()

        try:
            if not search_service:
                log_response(500, start_time)
                return jsonify({"error": "Search service not initialized"}), 500

            # Normalize media_type
            media_type = media_type.strip().lower()
            
            # Get parameters
            query = request.args.get("query", "").strip()
            language = request.args.get("language", "").strip().lower() or None
            limit = request.args.get("limit", 20, type=int)

            # Validate
            if not query:
                log_response(400, start_time)
                return jsonify({"error": "query parameter is required"}), 400

            if media_type not in {"songs", "movies", "books", "podcasts"}:
                log_response(400, start_time)
                return jsonify({"error": f"Invalid media_type: {media_type}. Must be one of: songs, movies, books, podcasts"}), 400

            # Search
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

    # ==================== INTERACTIONS (Phase 4) ====================

    @app.route("/api/v1/media/interaction", methods=["POST"])
    @login_required
    def track_media_interaction():
        """
        Track user interaction with media item (Phase 4).

        Request body:
        {
            "media_type": "songs | movies | books | podcasts",
            "item_id": "string",
            "signal": "click | save | skip",
            "context": "recommendation | search" (optional, default: recommendation)
        }

        Returns:
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
        """
        start_time = time.time()
        log_request()

        try:
            uid = request.user["uid"]

            if not interaction_service:
                log_response(500, start_time)
                return jsonify({"error": "Interaction service not initialized"}), 500

            # Parse request
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

            # Verify item exists in cache
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
                logger = logging.getLogger("pocket_journal.routes.media_domain")
                logger.warning(
                    "cache_validation_failed uid=%s media_type=%s item_id=%s error=%s",
                    uid, media_type, item_id, str(e),
                )
                log_response(500, start_time)
                return jsonify({"error": "Failed to validate item in cache"}), 500

            # Store interaction event
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

            # Check rate limit
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
                import logging
                logger = logging.getLogger("pocket_journal.routes.media_domain")
                logger.warning(
                    "rate_limit_check_failed uid=%s media_type=%s error=%s",
                    uid, media_type, str(e),
                )
                rate_limited = False

            # Update taste vector if not rate limited
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
                    import logging
                    logger = logging.getLogger("pocket_journal.routes.media_domain")
                    logger.warning(
                        "taste_vector_update_failed uid=%s media_type=%s item_id=%s error=%s",
                        uid, media_type, item_id, str(e),
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

