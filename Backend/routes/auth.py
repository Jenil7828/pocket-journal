import time
from utils.logging_utils import log_request, log_response
# routes/auth.py
from flask import request, jsonify
import os
import requests
import logging
from firebase_admin import auth as firebase_auth
from firebase_admin import firestore as fa_firestore
from google.cloud import firestore as gc_firestore

logger = logging.getLogger()


def register(app, deps: dict):
    """Register auth-related routes.

    Expects deps to contain:
      - get_db: callable returning DBManager
      - login_required: decorator
    """
    get_db = deps.get("get_db")
    login_required = deps.get("login_required")

    @app.route("/api/v1/auth/create-user", methods=["POST"])
    def create_user():
        start_time = time.time()
        log_request()
        payload = request.get_json(force=True, silent=True) or {}
        email = (payload.get("email") or "").strip()
        password = payload.get("password")
        name = (payload.get("name") or "").strip()
        # Identity-aware log for user creation
        logger.info(f"[REQ][auth] action=create_user email={email} name={name}")

        if not email or not password or not name:
            log_response(400, start_time)
            return jsonify({"error": "email, password and name are required"}), 400

        # Create Firebase Auth user
        try:
            user = firebase_auth.create_user(email=email, password=password, display_name=name)
        except Exception as e:
            logger.error(f"[ERR][auth] failed_firebase_create error={str(e)}")
            log_response(500, start_time)
            return jsonify({"error": "failed_to_create_user", "details": str(e)}), 500

        uid = user.uid

        # Create Firestore user document (do NOT store password)
        try:
            dbmgr = get_db() if get_db else None
            if dbmgr is None:
                logger.warning("[ERR][auth] db_manager_unavailable")
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
            logger.error(f"[ERR][auth] failed_firestore_create uid={uid} error={str(e)}")
            # Try to roll back created auth user to avoid orphaned auth accounts
            try:
                firebase_auth.delete_user(uid)
            except Exception:
                logger.error(f"[ERR][auth] failed_delete_auth_rollback uid={uid}")
            log_response(500, start_time)
            return jsonify({"error": "failed_to_create_user_profile", "details": str(e)}), 500

        log_response(201, start_time)
        return jsonify({"uid": uid, "email": email, "name": name, "message": "user_created"}), 201

    @app.route("/api/v1/auth/login", methods=["POST"])
    def login():
        start_time = time.time()
        log_request()
        payload = request.get_json(force=True, silent=True) or {}
        email = (payload.get("email") or "").strip()
        password = payload.get("password")
        # Identity-aware log for login
        logger.info(f"[REQ][auth] action=login email={email}")

        if not email or not password:
            log_response(400, start_time)
            return jsonify({"error": "email and password are required"}), 400

        # Use Firebase Identity Toolkit REST API to verify password and get tokens
        try:
            api_key = os.environ["FIREBASE_WEB_API_KEY"]
        except KeyError:
            log_response(500, start_time)
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
            log_response(200, start_time)
            return jsonify(result), 200
        except requests.exceptions.HTTPError as he:
            # Try to extract json from response if available
            resp_obj = getattr(he, 'response', None)
            try:
                err = resp_obj.json() if resp_obj is not None else {"error": str(he)}
            except Exception:
                err = {"error": str(he)}
            log_response(401, start_time)
            return jsonify({"error": "invalid_credentials", "details": err}), 401
        except Exception as e:
            logger.error(f"[ERR][auth] firebase_api_error error={str(e)}")
            log_response(500, start_time)
            return jsonify({"error": "login_failed", "details": str(e)}), 500

    @app.route("/api/v1/auth/change-password", methods=["POST"])
    @login_required
    def change_password():
        start_time = time.time()
        log_request()
        payload = request.get_json(force=True, silent=True) or {}
        current_password = payload.get("current_password")
        new_password = payload.get("new_password")

        if not current_password or not new_password:
            log_response(400, start_time)
            return jsonify({"error": "current_password and new_password are required"}), 400

        user = getattr(request, "user", None) or {}
        uid = user.get("uid")
        email = user.get("email")
        # Identity-aware log for password change
        logger.info(f"[REQ][auth] action=change_password")

        if not uid or not email:
            log_response(401, start_time)
            return jsonify({"error": "invalid_user"}), 401

        try:
            api_key = os.environ["FIREBASE_WEB_API_KEY"]
        except KeyError:
            log_response(500, start_time)
            return jsonify({"error": "server_misconfigured", "details": "FIREBASE_WEB_API_KEY not set"}), 500

        # Verify the current password by calling Firebase REST signInWithPassword
        verify_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
        verify_body = {"email": email, "password": current_password, "returnSecureToken": True}

        try:
            resp = requests.post(verify_url, json=verify_body, timeout=10)
            resp.raise_for_status()
        except requests.exceptions.HTTPError as he:
            # Wrong current password or other auth error
            resp_obj = getattr(he, 'response', None)
            try:
                err = resp_obj.json() if resp_obj is not None else {"error": str(he)}
            except Exception:
                err = {"error": str(he)}
            log_response(401, start_time)
            return jsonify({"error": "invalid_current_password", "details": err}), 401
        except Exception as e:
            logger.exception("Error verifying current password for uid=%s: %s", uid, str(e))
            log_response(500, start_time)
            return jsonify({"error": "verification_failed", "details": str(e)}), 500

        # If verification succeeded, update user's password via Admin SDK
        try:
            firebase_auth.update_user(uid, password=new_password)
            log_response(200, start_time)
            return jsonify({"message": "password_changed"}), 200
        except Exception as e:
            logger.exception("Failed to update password for uid=%s: %s", uid, str(e))
            log_response(500, start_time)
            return jsonify({"error": "failed_to_change_password", "details": str(e)}), 500
