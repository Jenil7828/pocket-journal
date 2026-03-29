import logging
import math
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional, Tuple

import numpy as np
from firebase_admin import firestore

from config_loader import get_config
from services.embeddings import get_embedding_service

logger = logging.getLogger("pocket_journal.media.intent")

_CFG = get_config()
_COLS = _CFG["firestore"]["collections"]
_CONC = _CFG["recommendation"]["concurrency"]

MediaIntent = Tuple[np.ndarray, float, float]


_MEDIA_KEY_MAP: Dict[str, str] = {
    "movie": "movies_vector",
    "movies": "movies_vector",
    "tmdb": "movies_vector",
    "song": "songs_vector",
    "songs": "songs_vector",
    "spotify": "songs_vector",
    "book": "books_vector",
    "books": "books_vector",
    "google_books": "books_vector",
    "podcast": "podcasts_vector",
    "podcasts": "podcasts_vector",
}


def _normalize(vec: Optional[np.ndarray]) -> Optional[np.ndarray]:
    if vec is None:
        return None
    if vec.size == 0:
        return None
    return get_embedding_service().normalize(vec)


def _fetch_taste_vector(uid: str, media_type: str) -> Optional[np.ndarray]:
    """Load the domain-specific taste vector from Firestore."""
    fs = firestore.client()
    doc = fs.collection("user_vectors").document(uid).get()
    if not doc.exists:
        return None
    data = doc.to_dict() or {}
    # media_type may carry an optional suffix like "songs:en"; use only the base key.
    base_type = media_type.split(":", 1)[0].lower()
    key = _MEDIA_KEY_MAP.get(base_type)
    if not key:
        raise ValueError(f"Unsupported media_type for taste vector: {media_type}")
    raw = data.get(key)
    if not raw:
        return None
    try:
        arr = np.asarray(raw, dtype=np.float32)
    except Exception as exc:
        logger.warning("Failed to convert taste vector for uid=%s key=%s: %s", uid, key, str(exc))
        return None
    return arr


def _fetch_latest_journal_embedding(uid: str) -> Optional[np.ndarray]:
    """Load the latest journal embedding for the user from Firestore."""
    fs = firestore.client()
    coll = fs.collection("journal_embeddings")
    # Order by Firestore timestamp descending and take the most recent
    query = (
        coll.where(filter=firestore.FieldFilter("uid", "==", uid))
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(1)
    )
    docs = list(query.stream())
    if not docs:
        return None
    data = docs[0].to_dict() or {}
    raw = data.get("embedding") or []
    if not raw:
        return None
    try:
        arr = np.asarray(raw, dtype=np.float32)
    except Exception as exc:
        logger.warning("Failed to convert journal embedding for uid=%s: %s", uid, str(exc))
        return None
    return arr


def _fetch_latest_emotional_state(uid: str) -> Dict[str, float]:
    """Best-effort fetch of latest emotional state (valence, arousal) from analysis documents.

    This is intentionally tolerant: if no structured emotional_state is present,
    valence and arousal default to 0, which yields the minimum blend weight.
    """
    fs = firestore.client()

    # Find the latest journal entry for this user
    entries_q = (
        fs.collection("journal_entries")
        .where(filter=firestore.FieldFilter("uid", "==", uid))
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(1)
    )
    entry_docs = list(entries_q.stream())
    if not entry_docs:
        return {"valence": 0.0, "arousal": 0.0}

    entry_id = entry_docs[0].id
    analysis_q = (
        fs.collection("entry_analysis")
        .where(filter=firestore.FieldFilter("entry_id", "==", entry_id))
        .limit(1)
    )
    analysis_docs = list(analysis_q.stream())
    if not analysis_docs:
        return {"valence": 0.0, "arousal": 0.0}

    analysis = analysis_docs[0].to_dict() or {}
    emotional_state = analysis.get("emotional_state") or {}
    try:
        valence = float(emotional_state.get("valence", 0.0) or 0.0)
        arousal = float(emotional_state.get("arousal", 0.0) or 0.0)
    except Exception:
        valence, arousal = 0.0, 0.0

    return {"valence": valence, "arousal": arousal}


def build_intent_vector(uid: str, media_type: str) -> MediaIntent:
    """Build the unified intent vector for a user and media domain.

    Steps (per spec):
    - Load domain-specific taste vector from Firestore (user_vectors.{media_type}_vector)
    - Load latest journal embedding (journal_embeddings)
    - Compute emotional intensity: sqrt(valence^2 + arousal^2)
    - Compute blend weights:
        beta = min(0.15 + 0.35 * intensity, 0.4)
        alpha = 1 - beta
    - If both taste and journal exist:
        intent = normalize(alpha * taste + beta * journal)
      If one is missing, return the other (normalized).
    - Raise error if vector dimensions mismatch.
    - Return (intent_vector, emotional_intensity, beta)
    """
    # media_type may include a language hint like "songs:en"; strip suffix for intent logic.
    media_key = media_type.split(":", 1)[0].lower()
    if media_key not in _MEDIA_KEY_MAP:
        raise ValueError(f"Unsupported media_type: {media_type}")

    with ThreadPoolExecutor(max_workers=3) as executor:
        f_taste   = executor.submit(_fetch_taste_vector, uid, media_key)
        f_journal = executor.submit(_fetch_latest_journal_embedding, uid)
        f_emotion = executor.submit(_fetch_latest_emotional_state, uid)

    taste_vec   = f_taste.result()
    journal_vec = f_journal.result()
    emo         = f_emotion.result()

    if taste_vec is None and journal_vec is None:
        raise ValueError(f"No vectors available for uid={uid} media_type={media_type}")

    # Dimension checks if both are present
    if taste_vec is not None and journal_vec is not None:
        if taste_vec.shape != journal_vec.shape:
            raise ValueError(
                f"Dimension mismatch between taste ({taste_vec.shape}) and journal ({journal_vec.shape})"
            )

    valence = emo.get("valence", 0.0) or 0.0
    arousal = emo.get("arousal", 0.0) or 0.0
    try:
        intensity = float(math.sqrt(valence * valence + arousal * arousal))
    except Exception:
        intensity = 0.0

    beta_min = float(_CFG["recommendation"]["intent"]["beta_min"])
    beta_boost = float(_CFG["recommendation"]["intent"]["beta_boost"])
    beta_max = float(_CFG["recommendation"]["intent"]["beta_max"])

    beta = min(beta_min + beta_boost * intensity, beta_max)
    beta = float(max(0.0, min(beta, beta_max)))  # defensive clamp
    alpha = 1.0 - beta

    taste_n = _normalize(taste_vec) if taste_vec is not None else None
    journal_n = _normalize(journal_vec) if journal_vec is not None else None

    if taste_n is not None and journal_n is not None:
        intent_raw = alpha * taste_n + beta * journal_n
        intent = _normalize(intent_raw)
    elif taste_n is not None:
        intent = taste_n
        beta = 0.0  # no journal component
    else:
        intent = journal_n
        # If we only have journal, its effective weight is 1.0
        beta = 1.0

    if intent is None or intent.size == 0:
        raise ValueError(f"Failed to build intent vector for uid={uid} media_type={media_type}")

    logger.info(
        "Built intent vector for uid=%s media_type=%s (dim=%s, intensity=%.4f, beta=%.4f)",
        uid,
        media_type,
        intent.shape[-1],
        intensity,
        beta,
    )

    return intent, float(intensity), float(beta)


# New helper: build a short semantic query string from latest journal summary or language hint
def build_semantic_query(uid: str, media_type: str) -> Optional[str]:
    """Attempt to build a short semantic query from the user's latest journal summary.

    Logic:
    - Try to fetch the most recent journal entry and look for a 'summary' or short 'text' field.
    - If present and reasonably sized, return a short cleaned string (2-6 words).
    - Otherwise, fallback to language hint extracted from media_type (e.g., 'songs:hi' -> 'hindi songs') or a small default.

    This function is intentionally lightweight and does not depend on external LLMs.
    """
    fs = firestore.client()
    try:
        entries_q = (
            fs.collection("journal_entries")
            .where(filter=firestore.FieldFilter("uid", "==", uid))
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(1)
        )
        docs = list(entries_q.stream())
        if docs:
            doc = docs[0].to_dict() or {}
            # Common fields to inspect
            for key in ("summary", "short_summary", "excerpt", "text", "content"):
                txt = doc.get(key)
                if txt and isinstance(txt, str) and len(txt.strip()) >= 10:
                    # Build a tiny semantic query by taking the first 6 meaningful words
                    words = [w for w in txt.strip().split() if len(w) > 2]
                    if not words:
                        continue
                    snippet = " ".join(words[:6])
                    return snippet
    except Exception:
        # Be tolerant: any failure here should not stop recommendation flow
        pass

    # Fallback: use language hint in media_type
    base = media_type.split(":", 1)[0].lower()
    lang = None
    if ":" in media_type:
        _, l = media_type.split(":", 1)
        lang = (l or "").strip().lower()

    if base in ("song", "songs", "spotify"):
        if lang in ("hi", "hindi"):
            return "hindi songs"
        if lang in ("en", "english"):
            return "english songs"
        return "top hits"
    if base in ("movie", "movies", "tmdb"):
        return "popular movies"
    if base in ("book", "books", "google_books"):
        return "bestselling books"
    if base in ("podcast", "podcasts"):
        return "popular podcasts"

    return None
