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

    @app.route("/me", methods=["GET"])
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

    @app.route("/me/preferences", methods=["PUT"])
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
            fs.collection("users").document(uid).update({"preferences": new_prefs})
            return jsonify({"uid": uid, "preferences": new_prefs}), 200
        except Exception as e:
            logger.exception("Failed to update preferences for uid=%s: %s", uid, str(e))
            return jsonify({"error": "failed_to_update_preferences", "details": str(e)}), 500

    @app.route("/me/settings", methods=["PUT"])
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

