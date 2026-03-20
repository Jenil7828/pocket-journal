# routes/user.py
from flask import request, jsonify
import logging
from firebase_admin import firestore as fa_firestore

logger = logging.getLogger("pocket_journal.routes.user")


def register(app, deps: dict):
    """Register user profile related routes.

    Expects deps to contain:
      - get_db: callable returning DBManager
      - login_required: decorator
    """
    get_db = deps.get("get_db")
    login_required = deps.get("login_required")
    # embedding service dependency (optional; embedder will be created lazily in app if available)
    get_embedding_service = deps.get("get_embedding_service")

    @app.route("/api/v1/me", methods=["GET"])
    @login_required
    def get_profile():
        user = getattr(request, "user", None) or {}
        uid = user.get("uid")
        if not uid:
            return jsonify({"error": "invalid_user"}), 401

        dbmgr = get_db() if get_db else None
        fs = dbmgr.db if dbmgr else fa_firestore.client()

        try:
            doc = fs.collection("users").document(uid).get()
            if not doc.exists:
                return jsonify({"error": "user_not_found"}), 404
            data = doc.to_dict()
            return jsonify({
                "uid": data.get("uid"),
                "name": data.get("name"),
                "email": data.get("email"),
                "createdAt": data.get("createdAt"),
                "preferences": data.get("preferences"),
                "settings": data.get("settings"),
            }), 200
        except Exception as e:
            logger.exception("Failed to fetch user profile uid=%s: %s", uid, str(e))
            return jsonify({"error": "failed_to_fetch_profile", "details": str(e)}), 500

    @app.route("/api/v1/me/preferences", methods=["PUT"])
    @login_required
    def update_preferences():
        user = getattr(request, "user", None) or {}
        uid = user.get("uid")
        if not uid:
            return jsonify({"error": "invalid_user"}), 401

        new_prefs = request.get_json(force=True, silent=True)
        if new_prefs is None or not isinstance(new_prefs, dict):
            return jsonify({"error": "preferences must be a JSON object"}), 400

        dbmgr = get_db() if get_db else None
        fs = dbmgr.db if dbmgr else fa_firestore.client()

        try:
            # Update main user preferences
            fs.collection("users").document(uid).update({"preferences": new_prefs})

            # Build domain-specific persona texts and store embeddings in user_vectors
            try:
                embedder = get_embedding_service() if callable(get_embedding_service) else None
            except Exception:
                embedder = None

            # Helper to build persona text from preferences for a domain using the
            # user's existing preference fields (movies, music, books, podcasts).
            # Keep backward compatibility with older keys (favorite_*).
            def build_persona_for_domain(prefs: dict, pref_keys: list) -> str:
                if not prefs or not isinstance(prefs, dict):
                    return ""
                parts = []
                for k in pref_keys:
                    v = prefs.get(k)
                    if not v:
                        continue
                    # If value is list, join; otherwise stringify
                    if isinstance(v, (list, tuple)):
                        joined = " ".join([str(x) for x in v if x])
                        if joined:
                            parts.append(joined)
                    else:
                        sv = str(v).strip()
                        if sv:
                            parts.append(sv)
                return " | ".join(parts)

            # Map canonical domain -> list of preference keys to consider (new keys first)
            domain_map = {
                # use 'movies' preference if present; fallback to legacy keys
                "movies": ["movies", "favorite_movie_genres", "favorite_movies", "movie_directors", "movie_actors"],
                # map songs domain to the 'music' preference field used by the client
                "songs": ["music", "favorite_music_genres", "favorite_songs", "favorite_artists"],
                "books": ["books", "favorite_book_genres", "favorite_books", "favorite_authors"],
                "podcasts": ["podcasts", "favorite_podcast_topics", "favorite_podcasts", "favorite_hosts"],
            }

            if embedder is not None:
                # Fetch or create user_vectors doc
                uv_ref = fs.collection("user_vectors").document(uid)
                uv_doc = uv_ref.get()
                existing = uv_doc.to_dict() if uv_doc.exists else {}

                updates = {}
                for domain, keys in domain_map.items():
                    persona = build_persona_for_domain(new_prefs, keys)
                    if not persona:
                        # skip empty persona (do not overwrite existing domain vector)
                        continue
                    try:
                        vec = embedder.embed_text(persona)
                        # Ensure we have a numpy vector; store as list of floats
                        updates[f"{domain}_vector"] = vec.tolist() if getattr(vec, "size", 0) else []
                        # Log embedding creation concisely
                        logger.debug("Embedded persona for uid=%s domain=%s (persona_len=%d)", uid, domain, len(persona))
                    except Exception as e:
                        # Log concise warning and keep stacktrace at debug level
                        logger.warning("Failed to embed persona for uid=%s domain=%s: %s", uid, domain, str(e))
                        logger.debug("%s", __import__('traceback').format_exc())

                # Write updates preserving other domains
                if updates:
                    updates["updated_at"] = fa_firestore.SERVER_TIMESTAMP
                    # Use set with merge to overwrite only provided fields
                    uv_ref.set(updates, merge=True)
                    # Log an info per domain vector written (exclude updated_at)
                    written_domains = [k for k in updates.keys() if k.endswith("_vector")]
                    for d in written_domains:
                        logger.info("Persisted user_vectors for uid=%s domain=%s", uid, d)

            return jsonify({"uid": uid, "preferences": new_prefs}), 200
        except Exception as e:
            logger.exception("Failed to update preferences for uid=%s: %s", uid, str(e))
            return jsonify({"error": "failed_to_update_preferences", "details": str(e)}), 500

    @app.route("/api/v1/me/settings", methods=["PUT"])
    @login_required
    def update_settings():
        user = getattr(request, "user", None) or {}
        uid = user.get("uid")
        if not uid:
            return jsonify({"error": "invalid_user"}), 401

        new_settings = request.get_json(force=True, silent=True)
        if new_settings is None or not isinstance(new_settings, dict):
            return jsonify({"error": "settings must be a JSON object"}), 400

        dbmgr = get_db() if get_db else None
        fs = dbmgr.db if dbmgr else fa_firestore.client()

        try:
            fs.collection("users").document(uid).update({"settings": new_settings})
            return jsonify({"uid": uid, "settings": new_settings}), 200
        except Exception as e:
            logger.exception("Failed to update settings for uid=%s: %s", uid, str(e))
            return jsonify({"error": "failed_to_update_settings", "details": str(e)}), 500

