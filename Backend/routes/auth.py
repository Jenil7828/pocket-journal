# routes/auth.py
from flask import request, jsonify
import os
import requests
import logging
from firebase_admin import auth as firebase_auth
from firebase_admin import firestore as fa_firestore
from google.cloud import firestore as gc_firestore

logger = logging.getLogger("pocket_journal.routes.auth")


def register(app, deps: dict):
    """Register auth-related routes.

    Expects deps to contain:
      - get_db: callable returning DBManager
      - login_required: decorator
    """
    get_db = deps.get("get_db")
    login_required = deps.get("login_required")

    @app.route("/auth/create-user", methods=["POST"])
    def create_user():
        payload = request.get_json(force=True, silent=True) or {}
        email = (payload.get("email") or "").strip()
        password = payload.get("password")
        name = (payload.get("name") or "").strip()

        if not email or not password or not name:
            return jsonify({"error": "email, password and name are required"}), 400

        # Create Firebase Auth user
        try:
            user = firebase_auth.create_user(email=email, password=password, display_name=name)
        except Exception as e:
            logger.exception("Failed to create firebase user: %s", str(e))
            return jsonify({"error": "failed_to_create_user", "details": str(e)}), 500

        uid = user.uid

        # Create Firestore user document (do NOT store password)
        try:
            dbmgr = get_db() if get_db else None
            if dbmgr is None:
                logger.warning("DB manager not available via deps.get('get_db')")
                # Attempt to use firebase_admin firestore client directly
                fs = fa_firestore.client()
            else:
                fs = dbmgr.db

            user_doc = {
                "uid": uid,
                "name": name,
                "email": email,
                "createdAt": gc_firestore.SERVER_TIMESTAMP,
                "preferences": {
                    "preferred_media_type": "both",
                    "languages": [],
                    "music": [],
                    "movies": [],
                    "books": [],
                    "podcasts": [],
                    "content_intensity": "Balanced",
                },
                "settings": {
                    "mood_tracking_enabled": True,
                    "daily_journal_reminders": True,
                },
            }

            fs.collection("users").document(uid).set(user_doc)

        except Exception as e:
            logger.exception("Failed to create firestore user doc for uid=%s: %s", uid, str(e))
            # Try to roll back created auth user to avoid orphaned auth accounts
            try:
                firebase_auth.delete_user(uid)
            except Exception:
                logger.exception("Failed to delete auth user after firestore failure: %s", uid)
            return jsonify({"error": "failed_to_create_user_profile", "details": str(e)}), 500

        return jsonify({"uid": uid, "email": email, "name": name, "message": "user_created"}), 201

    @app.route("/auth/login", methods=["POST"])
    def login():
        payload = request.get_json(force=True, silent=True) or {}
        email = (payload.get("email") or "").strip()
        password = payload.get("password")

        if not email or not password:
            return jsonify({"error": "email and password are required"}), 400

        # Use Firebase Identity Toolkit REST API to verify password and get tokens
        api_key = os.getenv("FIREBASE_WEB_API_KEY")
        if not api_key:
            return jsonify({"error": "server_misconfigured", "details": "FIREBASE_WEB_API_KEY not set"}), 500

        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
        body = {
            "email": email,
            "password": password,
            "returnSecureToken": True,
        }

        try:
            resp = requests.post(url, json=body, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            # data contains idToken, refreshToken, expiresIn, localId
            result = {
                "id_token": data.get("idToken"),
                "refresh_token": data.get("refreshToken"),
                "expires_in": data.get("expiresIn"),
            }
            return jsonify(result), 200
        except requests.exceptions.HTTPError as he:
            # Try to extract json from response if available
            resp_obj = getattr(he, 'response', None)
            try:
                err = resp_obj.json() if resp_obj is not None else {"error": str(he)}
            except Exception:
                err = {"error": str(he)}
            return jsonify({"error": "invalid_credentials", "details": err}), 401
        except Exception as e:
            logger.exception("Error calling Firebase REST API: %s", str(e))
            return jsonify({"error": "login_failed", "details": str(e)}), 500

