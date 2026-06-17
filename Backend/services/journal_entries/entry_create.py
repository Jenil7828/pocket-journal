import logging
import time

from config_loader import get_config
from services.journal_entries.background_tasks import submit_embedding_and_vector_update
from services.journal_entries.model_runtime import run_summary_and_mood_concurrently
from services.journal_entries.performance import JournalPerfLogger

logger = logging.getLogger()

_CFG = get_config()
_COLS = _CFG["firestore"]["collections"]


def process_entry(user, data, db, predictor, summarizer):
    uid = user.get("uid") if isinstance(user, dict) else None
    perf = JournalPerfLogger(uid=uid or "")
    perf.event("request_start")

    if not data or "entry_text" not in data:
        perf.finish("total_request")
        return {"error": "Missing entry_text"}, 400

    text = data["entry_text"]
    title = data.get("title")
    perf.event("request_payload", input_chars=len(text or ""))

    with perf.stage("entry_insert"):
        entry_id = db.insert_entry(uid, text, title=title)
    perf.entry_id = entry_id

    try:
        from services.journal_entries.emotional_pipeline import process_entry as run_pipeline
        with perf.stage("emotional_pipeline"):
            interpreted, raw_analysis = run_pipeline(user, text, predictor, summarizer, perf=perf)
        summary = raw_analysis.get("summary") if isinstance(raw_analysis, dict) else ""
        mood_probs = raw_analysis.get("mood") if isinstance(raw_analysis, dict) else {}
    except Exception:
        logger.exception("Emotional pipeline failed; falling back to legacy summarization/prediction")
        with perf.stage("fallback_parallel_analysis"):
            summary, mood_probs = run_summary_and_mood_concurrently(
                predictor=predictor,
                summarizer=summarizer,
                text=text,
                fallback_length=int(_CFG["app"]["summary_fallback_length"]),
                perf=perf,
            )

    mood_enabled = bool(_CFG["app"]["mood_tracking_enabled_default"])
    try:
        with perf.stage("mood_settings_read"):
            if uid:
                fs = getattr(db, "db", None) or None
                if fs is not None:
                    user_doc = fs.collection(_COLS["users"]).document(uid).get()
                    if user_doc.exists:
                        user_data = user_doc.to_dict() or {}
                        settings = user_data.get("settings", {}) or {}
                        mood_enabled = settings.get("mood_tracking_enabled", mood_enabled)
    except Exception:
        mood_enabled = bool(_CFG["app"]["mood_tracking_enabled_default"])

    if not mood_enabled:
        mood_probs = {}

    flat_analysis = {
        "entry_id": entry_id,
        "mood": mood_probs,
        "summary": summary,
    }

    with perf.stage("entry_metadata_read"):
        try:
            entry_doc = db.db.collection("journal_entries").document(entry_id).get()
            if entry_doc.exists:
                entry_dict = entry_doc.to_dict()
                if entry_dict.get("created_at"):
                    flat_analysis["created_at"] = entry_dict.get("created_at")
        except Exception:
            pass

    try:
        with perf.stage("analysis_persistence"):
            if "interpreted" in locals() and isinstance(interpreted, dict):
                db.insert_analysis(entry_id, interpreted, raw_analysis=raw_analysis)
                analysis_doc_id = None
            else:
                analysis_doc_id = db.insert_analysis(entry_id, summary, mood=mood_probs)
    except Exception as e:
        logger.exception("Failed to insert analysis for entry_id=%s: %s", entry_id, str(e))
        perf.finish("total_request")
        return {"error": "Failed to persist analysis", "details": str(e)}, 500

    if analysis_doc_id:
        flat_analysis["analysis_id"] = analysis_doc_id

    with perf.stage("background_schedule"):
        try:
            submit_embedding_and_vector_update(db=db, uid=uid, entry_id=entry_id, summary=summary)
        except Exception:
            logger.exception("Failed to schedule background vector maintenance for entry_id=%s", entry_id)

    with perf.stage("response_preparation"):
        response_body = flat_analysis
        status_code = 200

    perf.finish("total_request")
    return response_body, status_code
