# routes/user.py
from flask import request, jsonify
import logging
import time
from firebase_admin import firestore as fa_firestore
from utils.logging_utils import log_request, log_response
from services import user_service
from services import preferences_service
from services import settings_service
from services import notification_service

logger = logging.getLogger()


def register(app, deps: dict):
    """Register user profile related routes.

    Expects deps to contain:
      - get_db: callable returning DBManager
      - login_required: decorator
      - get_embedding_service: optional embedding service callable
    """
    get_db = deps.get("get_db")
    login_required = deps.get("login_required")
    get_embedding_service = deps.get("get_embedding_service")

    @app.route("/api/v1/me", methods=["GET"])
    @login_required
    def get_profile():
        """Get complete user profile with preferences, settings, and stats."""
        start_time = time.time()
        log_request()
        
        user = getattr(request, "user", None) or {}
        uid = user.get("uid")
        if not uid:
            log_response(401, start_time)
            return jsonify({"error": "invalid_user"}), 401

        dbmgr = get_db()
        
        try:
            # Get user profile with all settings
            user_data, error = user_service.get_user_profile(uid, dbmgr)
            if error:
                log_response(404 if error == "User not found" else 500, start_time)
                return jsonify({"error": error}), 404 if error == "User not found" else 500
            
            # Get user stats
            stats = user_service.get_user_stats(uid, dbmgr)
            
            response = {
                "uid": uid,
                "name": user_data.get("name"),
                "email": user_data.get("email"),
                "createdAt": user_data.get("createdAt"),
                "preferences": user_data.get("preferences"),
                "settings": user_data.get("settings"),
                "notification_settings": user_data.get("notification_settings"),
                "stats": stats
            }
            
            log_response(200, start_time)
            return jsonify(response), 200
        except Exception as e:
            logger.exception("Failed to fetch user profile uid=%s: %s", uid, str(e))
            log_response(500, start_time)
            return jsonify({"error": "failed_to_fetch_profile", "details": str(e)}), 500

    @app.route("/api/v1/me/profile", methods=["PUT"])
    @login_required
    def update_profile():
        """Update user profile (name, email)."""
        start_time = time.time()
        log_request()
        
        user = getattr(request, "user", None) or {}
        uid = user.get("uid")
        if not uid:
            log_response(401, start_time)
            return jsonify({"error": "invalid_user"}), 401

        data = request.get_json(force=True, silent=True)
        if data is None or not isinstance(data, dict):
            log_response(400, start_time)
            return jsonify({"error": "Request body must be JSON object"}), 400

        dbmgr = get_db()
        
        try:
            success, error = user_service.update_user_profile(uid, dbmgr, data)
            if not success:
                log_response(400, start_time)
                return jsonify({"error": error}), 400
            
            # Return updated profile
            user_data, error = user_service.get_user_profile(uid, dbmgr)
            if error:
                log_response(500, start_time)
                return jsonify({"error": error}), 500
            
            log_response(200, start_time)
            return jsonify({
                "uid": uid,
                "name": user_data.get("name"),
                "email": user_data.get("email")
            }), 200
        except Exception as e:
            logger.exception("Failed to update user profile uid=%s: %s", uid, str(e))
            log_response(500, start_time)
            return jsonify({"error": "failed_to_update_profile", "details": str(e)}), 500
    @app.route("/api/v1/me/preferences", methods=["GET"])
    @login_required
    def get_preferences():
        """Get user preferences."""
        start_time = time.time()
        log_request()
        
        user = getattr(request, "user", None) or {}
        uid = user.get("uid")
        if not uid:
            log_response(401, start_time)
            return jsonify({"error": "invalid_user"}), 401

        dbmgr = get_db()
        
        try:
            user_data, error = user_service.get_user_profile(uid, dbmgr)
            if error:
                log_response(404 if error == "User not found" else 500, start_time)
                return jsonify({"error": error}), 404 if error == "User not found" else 500
            
            log_response(200, start_time)
            return jsonify(user_data.get("preferences", preferences_service.get_default_preferences())), 200
        except Exception as e:
            logger.exception("Failed to fetch preferences uid=%s: %s", uid, str(e))
            log_response(500, start_time)
            return jsonify({"error": "failed_to_fetch_preferences", "details": str(e)}), 500

    @app.route("/api/v1/me/preferences", methods=["PUT"])
    @login_required
    def update_preferences():
        """Update user preferences (supports legacy and new formats)."""
        start_time = time.time()
        log_request()
        
        user = getattr(request, "user", None) or {}
        uid = user.get("uid")
        if not uid:
            log_response(401, start_time)
            return jsonify({"error": "invalid_user"}), 401

        new_prefs = request.get_json(force=True, silent=True)
        if new_prefs is None or not isinstance(new_prefs, dict):
            log_response(400, start_time)
            return jsonify({"error": "preferences must be a JSON object"}), 400

        dbmgr = get_db()
        
        try:
            success, error = user_service.update_preferences(
                uid,
                dbmgr,
                new_prefs,
                get_embedding_service
            )
            
            if not success:
                log_response(400, start_time)
                return jsonify({"error": error}), 400
            
            log_response(200, start_time)
            return jsonify({"uid": uid, "preferences": preferences_service.normalize_preferences(new_prefs)}), 200
        except Exception as e:
            logger.error(f"[ERR][user] failed_update_preferences error={str(e)}")
            log_response(500, start_time)
            return jsonify({"error": "failed_to_update_preferences", "details": str(e)}), 500

    @app.route("/api/v1/me/settings", methods=["GET"])
    @login_required
    def get_settings():
        """Get user settings."""
        start_time = time.time()
        log_request()
        
        user = getattr(request, "user", None) or {}
        uid = user.get("uid")
        if not uid:
            log_response(401, start_time)
            return jsonify({"error": "invalid_user"}), 401

        dbmgr = get_db()
        
        try:
            user_data, error = user_service.get_user_profile(uid, dbmgr)
            if error:
                log_response(404 if error == "User not found" else 500, start_time)
                return jsonify({"error": error}), 404 if error == "User not found" else 500
            
            log_response(200, start_time)
            return jsonify(user_data.get("settings", settings_service.get_default_settings())), 200
        except Exception as e:
            logger.exception("Failed to fetch settings uid=%s: %s", uid, str(e))
            log_response(500, start_time)
            return jsonify({"error": "failed_to_fetch_settings", "details": str(e)}), 500

    @app.route("/api/v1/me/settings", methods=["PUT"])
    @login_required
    def update_settings():
        """Update user settings (mood_tracking_enabled, weekly_insights_enabled)."""
        start_time = time.time()
        log_request()
        
        user = getattr(request, "user", None) or {}
        uid = user.get("uid")
        if not uid:
            log_response(401, start_time)
            return jsonify({"error": "invalid_user"}), 401

        new_settings = request.get_json(force=True, silent=True)
        if new_settings is None or not isinstance(new_settings, dict):
            log_response(400, start_time)
            return jsonify({"error": "settings must be a JSON object"}), 400

        dbmgr = get_db()
        
        try:
            success, error = user_service.update_settings(uid, dbmgr, new_settings)
            if not success:
                log_response(400, start_time)
                return jsonify({"error": error}), 400
            
            # Return updated settings
            user_data, error = user_service.get_user_profile(uid, dbmgr)
            if error:
                log_response(500, start_time)
                return jsonify({"error": error}), 500
            
            log_response(200, start_time)
            return jsonify({"uid": uid, "settings": user_data.get("settings")}), 200
        except Exception as e:
            logger.exception("Failed to update settings for uid=%s: %s", uid, str(e))
            log_response(500, start_time)
            return jsonify({"error": "failed_to_update_settings", "details": str(e)}), 500

    @app.route("/api/v1/me/notifications", methods=["GET"])
    @login_required
    def get_notifications():
        """Get user notification settings."""
        start_time = time.time()
        log_request()
        
        user = getattr(request, "user", None) or {}
        uid = user.get("uid")
        if not uid:
            log_response(401, start_time)
            return jsonify({"error": "invalid_user"}), 401

        dbmgr = get_db()
        
        try:
            user_data, error = user_service.get_user_profile(uid, dbmgr)
            if error:
                log_response(404 if error == "User not found" else 500, start_time)
                return jsonify({"error": error}), 404 if error == "User not found" else 500
            
            log_response(200, start_time)
            return jsonify(user_data.get("notification_settings", notification_service.get_default_notification_settings())), 200
        except Exception as e:
            logger.exception("Failed to fetch notifications uid=%s: %s", uid, str(e))
            log_response(500, start_time)
            return jsonify({"error": "failed_to_fetch_notifications", "details": str(e)}), 500

    @app.route("/api/v1/me/notifications", methods=["PUT"])
    @login_required
    def update_notifications():
        """Update user notification settings."""
        start_time = time.time()
        log_request()
        
        user = getattr(request, "user", None) or {}
        uid = user.get("uid")
        if not uid:
            log_response(401, start_time)
            return jsonify({"error": "invalid_user"}), 401

        new_notifications = request.get_json(force=True, silent=True)
        if new_notifications is None or not isinstance(new_notifications, dict):
            log_response(400, start_time)
            return jsonify({"error": "notification settings must be a JSON object"}), 400

        dbmgr = get_db()
        
        try:
            success, error = user_service.update_notification_settings(uid, dbmgr, new_notifications)
            if not success:
                log_response(400, start_time)
                return jsonify({"error": error}), 400
            
            # Return updated notifications
            user_data, error = user_service.get_user_profile(uid, dbmgr)
            if error:
                log_response(500, start_time)
                return jsonify({"error": error}), 500
            
            log_response(200, start_time)
            return jsonify({"uid": uid, "notification_settings": user_data.get("notification_settings")}), 200
        except Exception as e:
            logger.exception("Failed to update notifications for uid=%s: %s", uid, str(e))
            log_response(500, start_time)
            return jsonify({"error": "failed_to_update_notifications", "details": str(e)}), 500

