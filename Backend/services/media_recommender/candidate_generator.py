import logging
from typing import Any, Dict, List, Optional

import numpy as np

from config_loader import get_config
from services.embedding_service import get_embedding_service
from .providers.base_provider import MediaProvider, STANDARD_MEDIA_ITEM

logger = logging.getLogger("pocket_journal.media.candidates")

_CFG = get_config()

RefinedCandidate = Dict[str, Any]


def generate_candidates(
    provider: MediaProvider,
    query: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
    fetch_limit: int = 200,
) -> List[STANDARD_MEDIA_ITEM]:
    """Generate a cleaned candidate pool from a provider using query + filters.

    - Calls provider.fetch_candidates(query, filters, limit)
    - Applies aggressive cleaning: remove empty titles, title == 'Music', very short titles,
      duplicates, and low-popularity items when popularity is available.
    - Returns a list of STANDARD_MEDIA_ITEM (no embeddings attached).
    """
    raw_candidates: List[STANDARD_MEDIA_ITEM] = provider.fetch_candidates(query, filters, fetch_limit)
    before_count = len(raw_candidates)

    if not raw_candidates:
        logger.info("pocket_journal.media.filters: candidates before_clean=%d after_clean=0", before_count)
        return []

    cleaned: List[STANDARD_MEDIA_ITEM] = []
    seen_ids = set()
    min_title_length = int(_CFG["recommendation"]["candidate"]["min_title_length"])
    min_popularity_threshold = float(_CFG["recommendation"]["candidate"]["min_popularity"])

    for item in raw_candidates:
        try:
            mid = item.get("id")
            title = (item.get("title") or "").strip()
            desc = (item.get("description") or "").strip()
            if not mid or not title or not desc:
                continue
            if len(title) < min_title_length:
                continue
            # Low popularity filter (if provider gives a popularity score 0-100)
            pop = item.get("popularity")
            if pop is not None:
                try:
                    if float(pop) < min_popularity_threshold:
                        # Skip extremely low popularity items
                        continue
                except Exception:
                    pass

            if mid in seen_ids:
                continue
            seen_ids.add(mid)
            cleaned.append(item)
        except Exception:
            continue

    after_count = len(cleaned)
    logger.info(
        "pocket_journal.media.filters: semantic_query_cleaning before=%d after=%d",
        before_count,
        after_count,
    )

    return cleaned


def refine_candidates(
    intent_vector: np.ndarray, raw_candidates: List[STANDARD_MEDIA_ITEM], refine_top: int = 100
) -> List[RefinedCandidate]:
    """Embed raw candidates and select top `refine_top` by similarity.

    - Batch embed all cleaned candidates
    - Vectorized dot product similarity
    - Keep top `refine_top` (default 100)
    - Attach similarity and _embedding
    - Log refined pool size and top-3 similarities
    """
    if intent_vector is None or intent_vector.size == 0:
        raise ValueError("Intent vector must be a non-empty numpy array")

    if not raw_candidates:
        return []

    texts: List[str] = []
    for c in raw_candidates:
        title = (c.get("title") or "").strip()
        desc = (c.get("description") or "").strip()
        content = f"{title}. {desc}".strip(". ")
        texts.append(content)

    embedder = get_embedding_service()
    embeddings_list = embedder.embed_texts(texts)
    if not embeddings_list or len(embeddings_list) != len(raw_candidates):
        raise RuntimeError(
            f"Embedding service returned {len(embeddings_list)} embeddings for {len(raw_candidates)} candidates"
        )

    emb_matrix = np.vstack(embeddings_list).astype(np.float32)
    intent_vec = np.asarray(intent_vector, dtype=np.float32).reshape(-1)

    if emb_matrix.shape[1] != intent_vec.shape[0]:
        raise ValueError(
            f"Dimension mismatch between intent ({intent_vec.shape[0]}) and candidate embeddings ({emb_matrix.shape[1]})"
        )

    sims = emb_matrix @ intent_vec  # shape: (N,)

    n = emb_matrix.shape[0]
    k = min(refine_top, n)
    top_indices = np.argsort(-sims)[:k]

    refined: List[RefinedCandidate] = []
    top_sims = []
    for idx in top_indices:
        base = dict(raw_candidates[int(idx)])
        sim = float(sims[int(idx)])
        base["similarity"] = sim
        base["_embedding"] = emb_matrix[int(idx)]
        refined.append(base)
        top_sims.append(sim)

    # Log refined stats
    logger.info(
        "pocket_journal.media.candidates: refined_pool_size=%d from_raw=%d top_k=%d",
        len(refined),
        len(raw_candidates),
        k,
    )

    # Log top 3 similarity scores for observability
    top3 = top_sims[:3]
    logger.info("pocket_journal.media.candidates: top3_similarities=%s", top3)

    return refined

