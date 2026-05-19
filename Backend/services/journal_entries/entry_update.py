from datetime import datetime
import pytz
from firebase_admin import firestore
from utils import extract_dominant_mood
import logging

from config_loader import get_config

logger = logging.getLogger()

_CFG = get_config()


def update_entry(entry_id, uid, data, db, predictor, summarizer):
    if not entry_id:
        return {"error": "Entry ID is required"}, 400
    if not data or "entry_text" not in data:
        return {"error": "Missing entry_text in request body"}, 400

    new_entry_text = data["entry_text"]
    new_title = data.get("title")  # Optional title field
    regenerate_analysis = data.get("regenerate_analysis", True)

    if not new_entry_text.strip():
        return {"error": "Entry text cannot be empty"}, 400

    if regenerate_analysis:
        # Update the entry text and title first (will remove old analyses)
        result = db.update_entry(entry_id, uid, new_entry_text, title=new_title)
        if not result.get("success"):
            return {"error": result.get("error", "Failed to update entry")}, 400

        # Perform analysis deterministically on the NEW text
        try:
            from services.journal_entries.emotional_pipeline import process_entry as run_pipeline
            from services.embeddings import get_embedding_service
            embedder = get_embedding_service()
            interpreted, raw_analysis = run_pipeline(None, new_entry_text, predictor, summarizer, embedder, db=db)
            summary = raw_analysis.get("summary") if isinstance(raw_analysis, dict) else ""
            mood_probs = raw_analysis.get("mood") if isinstance(raw_analysis, dict) else {}
            # attach interpreted response for return
            interpreted_response = interpreted
        except Exception:
            logger.exception("Emotional pipeline failed during update; falling back to legacy summarization/prediction")
            summary = summarizer.summarize(new_entry_text) if summarizer else new_entry_text[:int(_CFG["app"]["summary_fallback_length"])] + "..."
            mood_result = predictor.predict(new_entry_text) if predictor else {}
            mood_probs = mood_result.get("probabilities") if isinstance(mood_result, dict) and "probabilities" in mood_result else mood_result

        logger.debug("update_entry (regenerate): entry_id=%s, analyzed_text_preview=%s", entry_id, new_entry_text[:200])

        flat_analysis = {
            "entry_id": entry_id,
            "mood": mood_probs,
            "summary": summary,
        }

        try:
            entry_doc = db.db.collection("journal_entries").document(entry_id).get()
            if entry_doc.exists:
                entry_dict = entry_doc.to_dict()
                if entry_dict.get("created_at"):
                    flat_analysis["created_at"] = entry_dict.get("created_at")
        except Exception:
            pass

        try:
            if 'interpreted_response' in locals() and isinstance(interpreted_response, dict):
                db.insert_analysis(entry_id, interpreted_response, raw_analysis=raw_analysis)
                analysis_doc_id = None
            else:
                analysis_doc_id = db.insert_analysis(entry_id, summary, mood=mood_probs)
        except Exception as e:
            logger.exception("Failed to insert analysis during update for entry_id=%s: %s", entry_id, str(e))
            return {"error": "Failed to persist updated analysis", "details": str(e)}, 500

        result["updated"]["new_analysis"] = flat_analysis
        if analysis_doc_id:
            result["updated"]["new_analysis"]["analysis_id"] = analysis_doc_id
    else:
        result = db.update_entry(entry_id, uid, new_entry_text, title=new_title)

    logger.debug("update_entry: entry_id=%s, regenerate_analysis=%s", entry_id, regenerate_analysis)

    if result["success"]:
        if regenerate_analysis:
            new_analysis = result["updated"].get("new_analysis")
            if isinstance(new_analysis, dict) and "mood" in new_analysis:
                return new_analysis, 200
        return {"message": "Entry updated successfully", "updated": result["updated"]}, 200
    return {"error": result["error"]}, 400

