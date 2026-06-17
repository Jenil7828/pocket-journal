import logging
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from firebase_admin import firestore

from config_loader import get_config
from services.journal_entries.performance import JournalPerfLogger

logger = logging.getLogger()
_CFG = get_config()
_COLS = _CFG["firestore"]["collections"]

_BACKGROUND_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="journal-bg")


def submit_embedding_and_vector_update(db, uid: str, entry_id: str, summary: str) -> None:
    """Schedule post-response embedding persistence and vector maintenance."""
    if not db or not uid or not entry_id:
        return
    _BACKGROUND_EXECUTOR.submit(_embedding_and_vector_worker, db, uid, entry_id, summary or "")


def _embedding_and_vector_worker(db, uid: str, entry_id: str, summary: str) -> None:
    """Persist journal embedding and blend user vectors in background."""
    perf = JournalPerfLogger(entry_id=entry_id, uid=uid)
    perf.event("background_start", summary_chars=len(summary or ""))

    try:
        from services.embeddings import get_embedding_service
        embedder = get_embedding_service() if callable(get_embedding_service) else None
    except Exception:
        embedder = None

    try:
        fs = getattr(db, "db", None) or None
        journal_vec = np.array([], dtype=np.float32)
        if fs is None or embedder is None:
            perf.finish("background_total")
            return

        try:
            with perf.stage("background_embedding_generation"):
                journal_vec = embedder.embed_text(summary)
        except Exception as e:
            logger.warning("Failed to create journal embedding for entry_id=%s: %s", entry_id, str(e))
            perf.finish("background_total")
            return

        try:
            with perf.stage("journal_embedding_persistence"):
                fs.collection(_COLS["journal_embeddings"]).add({
                    "uid": uid,
                    "entry_id": entry_id,
                    "embedding": journal_vec.tolist() if getattr(journal_vec, "size", 0) else [],
                    "created_at": firestore.SERVER_TIMESTAMP,
                })
            logger.info(
                "Stored journal embedding for entry_id=%s uid=%s (embedding_present=%s)",
                entry_id,
                uid,
                getattr(journal_vec, "size", 0) > 0,
            )
        except Exception as e:
            logger.warning("Failed to persist journal embedding for entry_id=%s: %s", entry_id, str(e))

        try:
            with perf.stage("user_vector_updates"):
                uv_ref = fs.collection(_COLS["user_vectors"]).document(uid)
                uv_doc = uv_ref.get()
                if not uv_doc.exists:
                    perf.finish("background_total")
                    return

                uv = uv_doc.to_dict() or {}
                domains = ["movies", "songs", "books", "podcasts"]
                updates = {}
                for domain in domains:
                    key = f"{domain}_vector"
                    existing_vec_list = uv.get(key)
                    if not existing_vec_list:
                        continue
                    try:
                        existing_vec = np.asarray(existing_vec_list, dtype=np.float32)
                        if existing_vec.size == 0 or getattr(journal_vec, "size", 0) == 0:
                            continue
                        taste_blend_weight = float(_CFG["ml"]["embedding"]["taste_blend_weight"])
                        journal_blend_weight = float(_CFG["ml"]["embedding"]["journal_blend_weight"])
                        blended = existing_vec * taste_blend_weight + journal_vec * journal_blend_weight
                        normed = (blended / (np.linalg.norm(blended) + 1e-12)).astype(np.float32)
                        updates[key] = normed.tolist()
                    except Exception as e:
                        logger.warning("Failed to blend identity for uid=%s domain=%s: %s", uid, domain, str(e))

                if updates:
                    updates["updated_at"] = firestore.SERVER_TIMESTAMP
                    uv_ref.set(updates, merge=True)
                    logger.info("Updated user_vectors for uid=%s domains=%s", uid, list(updates.keys()))
        except Exception:
            logger.warning("Failed to update user_vectors for uid=%s", uid)
    except Exception:
        logger.exception("Unexpected background error for journal vector maintenance entry_id=%s", entry_id)
    finally:
        perf.finish("background_total")
