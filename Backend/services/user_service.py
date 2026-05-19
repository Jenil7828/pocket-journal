"""
User service for consolidated user profile management.

Handles:
- User profile (name, email)
- Preferences
- Settings
- Notification settings
- Stats aggregation
"""

import logging
from typing import Dict, Optional, Any
from firebase_admin import firestore

logger = logging.getLogger()


def get_user_profile(uid: str, db) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Fetch complete user profile with all settings and preferences.
    
    Args:
        uid: User ID
        db: DBManager instance
        
    Returns:
        (user_data, error_message)
    """
    try:
        if not hasattr(db, 'db'):
            return None, "Invalid database connection"
        
        user_doc = db.db.collection("users").document(uid).get()
        
        if not user_doc.exists:
            return None, "User not found"
        
        user_data = user_doc.to_dict()
        
        # Ensure all required fields exist
        if not user_data:
            user_data = {}
        
        # Add uid
        user_data["uid"] = uid
        
        # Ensure nested objects exist
        if "preferences" not in user_data:
            from . import preferences_service
            user_data["preferences"] = preferences_service.get_default_preferences()
        
        if "settings" not in user_data:
            from . import settings_service
            user_data["settings"] = settings_service.get_default_settings()
        
        if "notification_settings" not in user_data:
            from . import notification_service
            user_data["notification_settings"] = notification_service.get_default_notification_settings()
        
        return user_data, None
        
    except Exception as e:
        logger.exception("Failed to fetch user profile uid=%s: %s", uid, str(e))
        return None, str(e)


def get_user_stats(uid: str, db) -> Dict[str, Any]:
    """
    Aggregate user statistics (entries count, streak, etc.).
    
    Args:
        uid: User ID
        db: DBManager instance
        
    Returns:
        Stats dictionary
    """
    try:
        if not hasattr(db, 'db'):
            return {"entries_count": 0, "streak": 0, "last_entry_date": None}
        
        # Count journal entries
        entries_query = db.db.collection("journal_entries").where(
            filter=firestore.FieldFilter("uid", "==", uid)
        )
        entries_count = len(entries_query.get())
        
        # Count insights
        insights_query = db.db.collection("insights").where(
            filter=firestore.FieldFilter("uid", "==", uid)
        )
        insights_count = len(insights_query.get())
        
        # Get last entry date
        last_entry_query = db.db.collection("journal_entries").where(
            filter=firestore.FieldFilter("uid", "==", uid)
        ).order_by("created_at", direction="DESCENDING").limit(1)
        
        last_entry_date = None
        for doc in last_entry_query.stream():
            entry_data = doc.to_dict()
            last_entry_date = entry_data.get("created_at")
            break
        
        return {
            "entries_count": entries_count,
            "insights_count": insights_count,
            "last_entry_date": last_entry_date
        }
        
    except Exception as e:
        logger.warning("Failed to compute user stats uid=%s: %s", uid, str(e))
        return {"entries_count": 0, "insights_count": 0, "last_entry_date": None}


def update_user_profile(uid: str, db, updates: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Update user profile fields (name, email, etc).
    
    Args:
        uid: User ID
        db: DBManager instance
        updates: Fields to update (name, email, etc)
        
    Returns:
        (success, error_message)
    """
    try:
        if not hasattr(db, 'db'):
            return False, "Invalid database connection"
        
        allowed_fields = {"name", "email"}
        update_dict = {k: v for k, v in updates.items() if k in allowed_fields and v is not None}
        
        if not update_dict:
            return True, None  # Nothing to update
        
        db.db.collection("users").document(uid).update(update_dict)
        logger.info("Updated user profile uid=%s fields=%s", uid, list(update_dict.keys()))
        return True, None
        
    except Exception as e:
        logger.exception("Failed to update user profile uid=%s: %s", uid, str(e))
        return False, str(e)


def update_preferences(
    uid: str,
    db,
    new_preferences: Dict[str, Any],
    get_embedding_service=None
) -> tuple[bool, Optional[str]]:
    """
    Update user preferences and optionally update embeddings.
    
    Args:
        uid: User ID
        db: DBManager instance
        new_preferences: New preference data
        get_embedding_service: Optional callable to get embedding service
        
    Returns:
        (success, error_message)
    """
    try:
        if not hasattr(db, 'db'):
            return False, "Invalid database connection"
        
        # Normalize preferences
        from . import preferences_service
        
        normalized = preferences_service.normalize_preferences(new_preferences)
        is_valid, error_msg = preferences_service.validate_preferences(normalized)
        if not is_valid:
            return False, error_msg
        
        # Update preferences
        db.db.collection("users").document(uid).update({"preferences": normalized})
        logger.info("Updated user preferences uid=%s", uid)
        
        # Update embeddings if service available
        if get_embedding_service:
            try:
                embedder = get_embedding_service() if callable(get_embedding_service) else None
                if embedder is not None:
                    _update_preference_embeddings(uid, db, normalized, embedder)
            except Exception as e:
                logger.warning("Failed to update preference embeddings uid=%s: %s", uid, str(e))
        
        return True, None
        
    except Exception as e:
        logger.exception("Failed to update preferences uid=%s: %s", uid, str(e))
        return False, str(e)


def _update_preference_embeddings(uid: str, db, preferences: Dict[str, Any], embedder):
    """Update preference embeddings for recommendation personalization."""
    try:
        domain_map = {
            "movies": ["movies", "favorite_movie_genres"],
            "songs": ["music", "favorite_music_genres", "favorite_songs"],
            "books": ["books", "favorite_book_genres"],
            "podcasts": ["podcasts", "favorite_podcast_topics"],
        }
        
        def build_persona(prefs: dict, keys: list) -> str:
            parts = []
            for k in keys:
                v = prefs.get(k)
                if not v:
                    continue
                if isinstance(v, (list, tuple)):
                    joined = " ".join([str(x) for x in v if x])
                    if joined:
                        parts.append(joined)
                else:
                    sv = str(v).strip()
                    if sv:
                        parts.append(sv)
            return " | ".join(parts)
        
        uv_ref = db.db.collection("user_vectors").document(uid)
        uv_doc = uv_ref.get()
        existing = uv_doc.to_dict() if uv_doc.exists else {}
        
        updates = {}
        for domain, keys in domain_map.items():
            persona = build_persona(preferences.get("genres", {}), keys)
            if not persona:
                continue
            
            try:
                vec = embedder.embed_text(persona)
                updates[f"{domain}_vector"] = vec.tolist() if getattr(vec, "size", 0) else []
                logger.debug(f"[SRV][user] embedded_persona domain={domain} persona_len={len(persona)}")
            except Exception as e:
                logger.warning(f"[SRV][user] embed_persona_failed domain={domain} error={str(e)}")
        
        if updates:
            updates["updated_at"] = firestore.SERVER_TIMESTAMP
            uv_ref.set(updates, merge=True)
            logger.info(f"[SRV][user] persisted_user_vectors domains={list(updates.keys())}")
            
    except Exception as e:
        logger.warning("Preference embeddings update failed uid=%s: %s", uid, str(e))


def update_settings(uid: str, db, new_settings: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Update user settings.
    
    Args:
        uid: User ID
        db: DBManager instance
        new_settings: New settings data
        
    Returns:
        (success, error_message)
    """
    try:
        if not hasattr(db, 'db'):
            return False, "Invalid database connection"
        
        from . import settings_service
        
        # Get existing settings
        user_data = db.db.collection("users").document(uid).get()
        if not user_data.exists:
            return False, "User not found"
        
        existing_settings = settings_service.get_user_settings(user_data.to_dict())
        merged = settings_service.merge_settings(existing_settings, new_settings)
        is_valid, error_msg = settings_service.validate_settings(merged)
        
        if not is_valid:
            return False, error_msg
        
        # Update settings
        db.db.collection("users").document(uid).update({"settings": merged})
        logger.info("Updated user settings uid=%s", uid)
        return True, None
        
    except Exception as e:
        logger.exception("Failed to update settings uid=%s: %s", uid, str(e))
        return False, str(e)


def update_notification_settings(
    uid: str,
    db,
    new_notifications: Dict[str, Any]
) -> tuple[bool, Optional[str]]:
    """
    Update user notification settings.
    
    Args:
        uid: User ID
        db: DBManager instance
        new_notifications: New notification settings data
        
    Returns:
        (success, error_message)
    """
    try:
        if not hasattr(db, 'db'):
            return False, "Invalid database connection"
        
        from . import notification_service
        
        # Get existing notifications
        user_data = db.db.collection("users").document(uid).get()
        if not user_data.exists:
            return False, "User not found"
        
        existing_notif = notification_service.get_user_notification_settings(user_data.to_dict())
        merged = notification_service.merge_notification_settings(existing_notif, new_notifications)
        is_valid, error_msg = notification_service.validate_notification_settings(merged)
        
        if not is_valid:
            return False, error_msg
        
        # Update notification settings
        db.db.collection("users").document(uid).update({"notification_settings": merged})
        logger.info("Updated user notification settings uid=%s", uid)
        return True, None
        
    except Exception as e:
        logger.exception("Failed to update notification settings uid=%s: %s", uid, str(e))
        return False, str(e)





