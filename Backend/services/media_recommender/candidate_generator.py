import logging
from typing import Any, Dict, List

import numpy as np

from services.embedding_service import get_embedding_service
from .providers.base_provider import MediaProvider, STANDARD_MEDIA_ITEM

logger = logging.getLogger("pocket_journal.media.candidates")


RefinedCandidate = Dict[str, Any]


def generate_refined_pool(
    intent_vector: np.ndarray,
    provider: MediaProvider,
    fetch_limit: int = 150,
    refine_top: int = 100,
) -> List[RefinedCandidate]:
    """Generate a refined candidate pool for a given media provider.

    Steps:
    - Fetch a broad, neutral pool of candidates from the provider
    - Build `content_text = title + ". " + description`
    - Batch embed all candidates (no per-item embedding calls)
    - Compute similarity via vectorized NumPy dot product
    - Select top `refine_top` and attach similarity scores
    - Return the refined list
    """
    if intent_vector is None or intent_vector.size == 0:
        raise ValueError("Intent vector must be a non-empty numpy array")

    # Ensure we are working with a float32, 1D normalized vector.
    intent_vec = np.asarray(intent_vector, dtype=np.float32).reshape(-1)

    # Provider fetch (already responsible for retries / fallbacks)
    raw_candidates: List[STANDARD_MEDIA_ITEM] = provider.fetch_candidates(fetch_limit)
    if not raw_candidates:
        raise RuntimeError("Provider returned no candidates")

    texts: List[str] = []
    for c in raw_candidates:
        title = (c.get("title") or "").strip()
        desc = (c.get("description") or "").strip()
        content = f"{title}. {desc}".strip(". ")
        texts.append(content)

    embedder = get_embedding_service()
    # Batch embedding only – single call for the full candidate set
    embeddings_list = embedder.embed_texts(texts)
    if not embeddings_list or len(embeddings_list) != len(raw_candidates):
        raise RuntimeError(
            f"Embedding service returned {len(embeddings_list)} embeddings for {len(raw_candidates)} candidates"
        )

    # Convert to matrix for efficient similarity computation.
    # The embedding service already returns L2-normalized vectors; we avoid
    # redundant normalization here per performance rules.
    emb_matrix = np.vstack(embeddings_list).astype(np.float32)

    if emb_matrix.shape[1] != intent_vec.shape[0]:
        raise ValueError(
            f"Dimension mismatch between intent ({intent_vec.shape[0]}) and candidate embeddings ({emb_matrix.shape[1]})"
        )

    # Fully vectorized similarity via dot product
    sims = emb_matrix @ intent_vec  # shape: (N,)

    # Select the top `refine_top` indices
    n = emb_matrix.shape[0]
    k = min(refine_top, n)
    top_indices = np.argsort(-sims)[:k]

    refined: List[RefinedCandidate] = []
    for idx in top_indices:
        base = dict(raw_candidates[int(idx)])
        base["similarity"] = float(sims[int(idx)])
        # Keep embedding for downstream ranking to avoid re-embedding
        base["_embedding"] = emb_matrix[int(idx)]
        refined.append(base)

    logger.info(
        "Generated refined candidate pool size=%d (from %d raw)", len(refined), len(raw_candidates)
    )

    return refined


