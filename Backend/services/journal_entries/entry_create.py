from datetime import datetime
import pytz
from firebase_admin import firestore
from utils import extract_dominant_mood
import logging

logger = logging.getLogger("pocket_journal.journal_entries")


def process_entry(user, data, db, predictor, summarizer):
    if not data or "entry_text" not in data:
        return {"error": "Missing entry_text"}, 400

    uid = user.get("uid") if isinstance(user, dict) else None
    text = data["entry_text"]

    # Insert the entry first
    entry_id = db.insert_entry(uid, text)

    # Summarize (optional)
    summary = summarizer.summarize(text) if summarizer else text[:200] + "..."

    # Determine whether mood detection is enabled for the user (default: True)
    mood_enabled = True
    try:
        if uid:
            fs = getattr(db, "db", None) or None
            if fs is not None:
                user_doc = fs.collection("users").document(uid).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict() or {}
                    settings = user_data.get("settings", {}) or {}
                    mood_enabled = settings.get("mood_tracking_enabled", True)
    except Exception:
        # If anything goes wrong while reading settings, default to enabled
        mood_enabled = True

    # Use original entry text for mood detection per design
    if mood_enabled:
        mood_result = predictor.predict(text, threshold=0.25) if predictor else {}
        mood_probs = mood_result.get("probabilities") if isinstance(mood_result, dict) and "probabilities" in mood_result else mood_result
    else:
        # Mood tracking disabled: do not call predictor; keep mood empty
        mood_probs = {}

    logger.debug("process_entry: entry_id=%s, analyzed_text_preview=%s", entry_id, (text or "")[:200])

    # Build flat analysis (legacy shape)
    flat_analysis = {
        "entry_id": entry_id,
        "mood": mood_probs,
        "summary": summary,
    }

    # Try to attach created_at if available
    try:
        entry_doc = db.db.collection("journal_entries").document(entry_id).get()
        if entry_doc.exists:
            entry_dict = entry_doc.to_dict()
            if entry_dict.get("created_at"):
                flat_analysis["created_at"] = entry_dict.get("created_at")
    except Exception:
        pass

    # Persist the flat analysis using legacy DB signature
    try:
        analysis_doc_id = db.insert_analysis(entry_id, summary, mood=mood_probs)
    except Exception as e:
        logger.exception("Failed to insert analysis for entry_id=%s: %s", entry_id, str(e))
        return {"error": "Failed to persist analysis", "details": str(e)}, 500

    if analysis_doc_id:
        flat_analysis["analysis_id"] = analysis_doc_id

    return flat_analysis, 200
