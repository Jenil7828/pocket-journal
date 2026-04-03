from datetime import datetime
import pytz
from firebase_admin import firestore
from utils import extract_dominant_mood
import logging

from config_loader import get_config

logger = logging.getLogger()

_CFG = get_config()
_COLS = _CFG["firestore"]["collections"]


# Helper function to generate title from entry text
def _generate_title(text: str) -> str:
    """Auto-generate a title from entry text (first 50 chars or first sentence)."""
    if not text:
        return "Untitled"
    # Extract first sentence (up to period, newline, or 50 chars)
    text = text.strip()
    for i, char in enumerate(text):
        if char in '.!?\n' and i > 0:
            return text[:i].strip()[:50]
    return text[:50].strip() if text else "Untitled"


def reanalyze_entry(entry_id, uid, db, predictor, summarizer):
    entry_doc = db.db.collection(_COLS["journal_entries"]).document(entry_id).get()
    if not entry_doc.exists:
        return {"error": "Entry not found"}, 404

    entry_data = entry_doc.to_dict()
    if entry_data.get("uid") != uid:
        return {"error": "Unauthorized: Entry does not belong to user"}, 403

    entry_text = entry_data["entry_text"]

    analysis_query = db.db.collection(_COLS["entry_analysis"]).where(filter=firestore.FieldFilter("entry_id", "==", entry_id)).get()
    old_analysis_ids = []
    for analysis_doc in analysis_query:
        analysis_doc.reference.delete()
        old_analysis_ids.append(analysis_doc.id)

    summary = summarizer.summarize(entry_text) if summarizer else entry_text[:int(_CFG["app"]["summary_fallback_length"])] + "..."

    # Check user's mood tracking setting; default True
    mood_enabled = bool(_CFG["app"]["mood_tracking_enabled_default"])
    try:
        user_doc = db.db.collection(_COLS["users"]).document(uid).get()
        if user_doc.exists:
            user_data = user_doc.to_dict() or {}
            settings = user_data.get("settings", {}) or {}
            mood_enabled = settings.get("mood_tracking_enabled", True)
    except Exception:
        mood_enabled = bool(_CFG["app"]["mood_tracking_enabled_default"])

    if mood_enabled:
        mood_result = predictor.predict(entry_text) if predictor else {}
        mood_probs = mood_result.get("probabilities") if isinstance(mood_result, dict) and "probabilities" in mood_result else mood_result
    else:
        mood_probs = {}

    logger.debug("reanalyze_entry: entry_id=%s", entry_id)

    flat_analysis = {
        "entry_id": entry_id,
        "mood": mood_probs,
        "summary": summary,
    }

    try:
        if entry_data.get("created_at"):
            flat_analysis["created_at"] = entry_data.get("created_at")
    except Exception:
        pass

    try:
        analysis_doc_id = db.insert_analysis(entry_id, summary, mood=mood_probs)
    except Exception as e:
        logger.exception("Failed to insert analysis during reanalyze for entry_id=%s: %s", entry_id, str(e))
        return {"error": "Failed to persist reanalysis", "details": str(e)}, 500

    if analysis_doc_id:
        flat_analysis["analysis_id"] = analysis_doc_id

    return {
        "message": "Entry reanalyzed successfully",
        "entry_id": entry_id,
        "old_analysis_deleted": len(old_analysis_ids),
        "old_analysis_ids": old_analysis_ids,
        "new_analysis": flat_analysis,
    }, 200


def get_single_entry(entry_id, uid, db):
    entry_doc = db.db.collection(_COLS["journal_entries"]).document(entry_id).get()
    if not entry_doc.exists:
        return {"error": "Entry not found"}, 404

    entry_data = entry_doc.to_dict()
    if entry_data.get("uid") != uid:
        return {"error": "Unauthorized: Entry does not belong to user"}, 403

    # Auto-generate title if missing (for backward compatibility)
    title = entry_data.get("title") or _generate_title(entry_data.get("entry_text", ""))

    analysis_query = db.db.collection(_COLS["entry_analysis"]).where(filter=firestore.FieldFilter("entry_id", "==", entry_id)).get()
    analysis_data = None
    for analysis_doc in analysis_query:
        analysis_data = analysis_doc.to_dict()
        analysis_data["analysis_id"] = analysis_doc.id
        break

    return {
        "entry_id": entry_id,
        "title": title,
        "entry_text": entry_data["entry_text"],
        "created_at": entry_data["created_at"],
        "updated_at": entry_data.get("updated_at"),
        "analysis": analysis_data,
    }, 200


def get_entry_analysis(entry_id, uid, db):
    entry_doc = db.db.collection(_COLS["journal_entries"]).document(entry_id).get()
    if not entry_doc.exists:
        return {"error": "Entry not found"}, 404

    entry_data = entry_doc.to_dict()
    if entry_data.get("uid") != uid:
        return {"error": "Unauthorized: Entry does not belong to user"}, 403

    analysis_query = db.db.collection(_COLS["entry_analysis"]).where(filter=firestore.FieldFilter("entry_id", "==", entry_id)).get()
    analysis_data = None
    for analysis_doc in analysis_query:
        analysis_data = analysis_doc.to_dict()
        analysis_data["analysis_id"] = analysis_doc.id
        break

    return {"entry_id": entry_id, "analysis": analysis_data}, 200


def get_entries_filtered(uid, params, db):
    start_date = params.get("start_date")
    end_date = params.get("end_date")
    mood_filter = params.get("mood")
    search_term = params.get("search")

    try:
        limit = int(params.get("limit", 50))
        offset = int(params.get("offset", 0))
    except ValueError:
        return {"error": "Invalid limit or offset parameter"}, 400

    if limit < 1 or limit > int(_CFG["api"]["max_limit"]):
        return {"error": "Limit must be between 1 and 100"}, 400
    if offset < 0:
        return {"error": "Offset must be non-negative"}, 400

    query = db.db.collection(_COLS["journal_entries"]).where(filter=firestore.FieldFilter("uid", "==", uid))

    if start_date and start_date.strip():
        try:
            start_date_str = str(start_date).strip()
            start_datetime_naive = datetime.strptime(start_date_str, "%Y-%m-%d")
            IST = pytz.timezone(_CFG["app"]["timezone"])
            start_datetime = IST.localize(start_datetime_naive)
            query = query.where(filter=firestore.FieldFilter("created_at", ">=", start_datetime))
        except ValueError:
            return {"error": "Invalid start_date format. Use YYYY-MM-DD"}, 400

    if end_date and end_date.strip():
        try:
            end_date_str = str(end_date).strip()
            end_datetime_naive = datetime.strptime(end_date_str, "%Y-%m-%d")
            IST = pytz.timezone(_CFG["app"]["timezone"])
            end_datetime = IST.localize(end_datetime_naive.replace(hour=23, minute=59, second=59))
            query = query.where(filter=firestore.FieldFilter("created_at", "<=", end_datetime))
        except ValueError:
            return {"error": "Invalid end_date format. Use YYYY-MM-DD"}, 400

    query = query.order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)

    entries = []
    all_entries = []
    for entry_doc in query.stream():
        entry_data = entry_doc.to_dict()
        entry_data["entry_id"] = entry_doc.id
        all_entries.append(entry_data)

    for entry_data in all_entries:
        try:
            if search_term and search_term.lower() not in entry_data["entry_text"].lower():
                continue

            if mood_filter:
                try:
                    analysis_query = db.db.collection(_COLS["entry_analysis"]).where(filter=firestore.FieldFilter("entry_id", "==", entry_data["entry_id"])).get()
                    has_matching_mood = False
                    for analysis_doc in analysis_query:
                        analysis_data = analysis_doc.to_dict()
                        mood_probs = analysis_data.get("mood", {})
                        if mood_probs:
                            dominant_mood = extract_dominant_mood(mood_probs)
                            if dominant_mood and dominant_mood == mood_filter.lower():
                                has_matching_mood = True
                                break
                    if not has_matching_mood:
                        continue
                except Exception:
                    pass

            # Auto-generate title if missing (backward compatibility)
            if "title" not in entry_data:
                entry_data["title"] = _generate_title(entry_data.get("entry_text", ""))

            entries.append(entry_data)
        except Exception:
            continue

    total_count = len(entries)
    entries = entries[offset:offset + limit]

    return {
        "entries": entries,
        "count": len(entries),
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
        "filters": {
            "start_date": start_date,
            "end_date": end_date,
            "mood": mood_filter,
            "search": search_term,
        },
    }, 200
