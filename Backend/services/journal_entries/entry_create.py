from firebase_admin import firestore
import logging
import numpy as np

from config_loader import get_config

logger = logging.getLogger()

_CFG = get_config()
_COLS = _CFG["firestore"]["collections"]


def process_entry(user, data, db, predictor, summarizer):
    if not data or "entry_text" not in data:
        return {"error": "Missing entry_text"}, 400

    uid = user.get("uid") if isinstance(user, dict) else None
    text = data["entry_text"]
    title = data.get("title")  # Optional title field

    # Insert the entry first (title is optional and backward compatible)
    entry_id = db.insert_entry(uid, text, title=title)

    # Use the new emotional pipeline to produce segment-level analysis and calibrated mood
    try:
        from services.journal_entries.emotional_pipeline import process_entry as run_pipeline
        from services.embeddings import get_embedding_service
        embedder = get_embedding_service()
        interpreted, raw_analysis = run_pipeline(user, text, predictor, summarizer, embedder, db=db)
        # prefer factual_summary as legacy summary field
        summary = raw_analysis.get("summary") if isinstance(raw_analysis, dict) else ""
        mood_probs = raw_analysis.get("mood") if isinstance(raw_analysis, dict) else {}
    except Exception:
        # Fallback to legacy flow if pipeline fails
        logger.exception("Emotional pipeline failed; falling back to legacy summarization/prediction")
        summary = summarizer.summarize(text) if summarizer else text[:int(_CFG["app"]["summary_fallback_length"])] + "..."
        mood_result = predictor.predict(text) if predictor else {}
        mood_probs = mood_result.get("probabilities") if isinstance(mood_result, dict) and "probabilities" in mood_result else mood_result

    # Determine whether mood detection is enabled for the user (default from config)
    mood_enabled = bool(_CFG["app"]["mood_tracking_enabled_default"])
    try:
        if uid:
            fs = getattr(db, "db", None) or None
            if fs is not None:
                user_doc = fs.collection(_COLS["users"]).document(uid).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict() or {}
                    settings = user_data.get("settings", {}) or {}
                    mood_enabled = settings.get("mood_tracking_enabled", mood_enabled)
    except Exception:
        # If anything goes wrong while reading settings, default to config value
        mood_enabled = bool(_CFG["app"]["mood_tracking_enabled_default"])

    # If mood tracking is disabled for the user, clear mood_probs before persisting
    if not mood_enabled:
        mood_probs = {}

    logger.debug("process_entry: entry_id=%s, analyzed_text_preview=%s", entry_id, (text or "")[:200])

    # Build flat analysis (legacy shape) from pipeline outputs
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
        # Prefer new interpreted-response style when available
        if 'interpreted' in locals() and isinstance(interpreted, dict):
            db.insert_analysis(entry_id, interpreted, raw_analysis=raw_analysis)
            analysis_doc_id = None
        else:
            analysis_doc_id = db.insert_analysis(entry_id, summary, mood=mood_probs)
    except Exception as e:
        logger.exception("Failed to insert analysis for entry_id=%s: %s", entry_id, str(e))
        return {"error": "Failed to persist analysis", "details": str(e)}, 500

    if analysis_doc_id:
        flat_analysis["analysis_id"] = analysis_doc_id

    # NEW: Embedding storage and identity update
    try:
        # lazy import to avoid hard dependency at module import time
        from services.embeddings import get_embedding_service
        embedder = get_embedding_service() if callable(get_embedding_service) else None
    except Exception:
        embedder = None

    try:
        fs = getattr(db, "db", None) or None
        # default empty journal_vec so blending code can safely reference it even if embedding fails
        journal_vec = np.array([], dtype=np.float32)
        if fs is not None and embedder is not None:
            # Store journal embedding in journal_embeddings collection
            try:
                journal_vec = embedder.embed_text(summary)
                # Persist as list of floats (or empty list if embedding missing). Use Firestore server timestamp.
                fs.collection(_COLS["journal_embeddings"]).add({
                    "uid": uid,
                    "entry_id": entry_id,
                    "embedding": journal_vec.tolist() if getattr(journal_vec, "size", 0) else [],
                    "created_at": firestore.SERVER_TIMESTAMP,
                })
                # Log concise info that journal embedding was persisted
                logger.info("Stored journal embedding for entry_id=%s uid=%s (embedding_present=%s)", entry_id, uid, getattr(journal_vec, "size", 0) > 0)
            except Exception as e:
                # Log concise warning and keep detailed trace at debug
                logger.warning("Failed to create journal embedding for entry_id=%s: %s", entry_id, str(e))
                logger.debug("%s", __import__('traceback').format_exc())

            # Apply light identity update for each domain if existing
            try:
                uv_ref = fs.collection(_COLS["user_vectors"]).document(uid)
                uv_doc = uv_ref.get()
                if uv_doc.exists:
                    uv = uv_doc.to_dict() or {}
                    # domains to consider
                    domains = ["movies", "songs", "books", "podcasts"]
                    updates = {}
                    for d in domains:
                        key = f"{d}_vector"
                        existing_vec_list = uv.get(key)
                        if not existing_vec_list:
                            # skip if domain vector missing or empty
                            continue
                        try:
                            existing_vec = np.asarray(existing_vec_list, dtype=np.float32)
                            if existing_vec.size == 0 or getattr(journal_vec, "size", 0) == 0:
                                # nothing to blend
                                continue
                            # Blend: configured taste_blend_weight * existing + journal_blend_weight * journal embedding
                            taste_blend_weight = float(_CFG["ml"]["embedding"]["taste_blend_weight"])
                            journal_blend_weight = float(_CFG["ml"]["embedding"]["journal_blend_weight"])
                            blended = existing_vec * taste_blend_weight + journal_vec * journal_blend_weight
                            # Normalize
                            normed = (blended / (np.linalg.norm(blended) + 1e-12)).astype(np.float32)
                            updates[key] = normed.tolist()
                            # Log concise debug about blending
                            logger.debug("Blended identity for uid=%s domain=%s (existing_present=True journal_present=True)", uid, d)
                        except Exception as e:
                            # Log concise warning and keep detailed trace at debug
                            logger.warning("Failed to blend identity for uid=%s domain=%s: %s", uid, d, str(e))
                            logger.debug("%s", __import__('traceback').format_exc())

                    if updates:
                        updates["updated_at"] = firestore.SERVER_TIMESTAMP
                        uv_ref.set(updates, merge=True)
                        logger.info("Updated user_vectors for uid=%s domains=%s", uid, list(updates.keys()))
            except Exception:
                # Do not fail entry save on vector update problems; log concisely
                logger.warning("Failed to update user_vectors for uid=%s", uid)
                logger.debug("%s", __import__('traceback').format_exc())
    except Exception:
        # swallow embedding-related exceptions to avoid failing core flow; log concisely
        logger.warning("Unexpected error in embedding/identity update for entry_id=%s", entry_id)
        logger.debug("%s", __import__('traceback').format_exc())

    return flat_analysis, 200
