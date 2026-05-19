import logging
from typing import Any, Dict, List

import numpy as np

from config_loader import get_config

logger = logging.getLogger()

_CFG = get_config()

RankedCandidate = Dict[str, Any]


def rank_candidates(
    intent_vector: np.ndarray,
    refined_candidates: List[Dict[str, Any]],
    top_k: int = 10,
) -> List[RankedCandidate]:
    """Rank candidates against the intent vector using matrix multiplication.

    - Uses a single matrix multiplication for all candidates
    - Combines similarity (0.9) with normalized popularity (0.1)
    - Computes basic score statistics and logs them
    - Warns if score std dev is very low (< 0.03)
    """
    if not refined_candidates:
        return []

    intent_vec = np.asarray(intent_vector, dtype=np.float32).reshape(-1)

    embeddings = []
    pops = []
    for c in refined_candidates:
        emb = c.get("_embedding")
        if emb is None:
            raise ValueError("Refined candidates must include '_embedding' vectors")
        embeddings.append(np.asarray(emb, dtype=np.float32).reshape(-1))
        # Extract popularity if present (top-level or inside metadata)
        pop = c.get("popularity")
        if pop is None:
            pop = None
            meta = c.get("metadata") or {}
            # metadata may be nested (providers sometimes embed original metadata)
            if isinstance(meta, dict):
                pop = meta.get("popularity") or meta.get("popularity_score")
        try:
            pops.append(float(pop) if pop is not None else 0.0)
        except Exception:
            pops.append(0.0)

    cand_matrix = np.vstack(embeddings)  # shape: (N, D)

    if cand_matrix.shape[1] != intent_vec.shape[0]:
        raise ValueError(
            f"Dimension mismatch between intent ({intent_vec.shape[0]}) and candidates ({cand_matrix.shape[1]})"
        )

    # Vectorized similarity via matrix multiplication
    sims = cand_matrix @ intent_vec  # shape: (N,)

    # Normalize popularity to [0,1]
    pop_arr = np.asarray(pops, dtype=np.float32)
    max_pop = float(pop_arr.max()) if pop_arr.size > 0 else 0.0
    if max_pop > 0.0:
        pop_norm = pop_arr / max_pop
    else:
        pop_norm = np.zeros_like(pop_arr)

    # Final score: configured similarity_weight * similarity + popularity_weight * normalized_popularity
    similarity_weight = float(_CFG["recommendation"]["ranking"]["similarity_weight"])
    popularity_weight = float(_CFG["recommendation"]["ranking"]["popularity_weight"])
    scores = similarity_weight * sims + popularity_weight * pop_norm

    # Stats for observability
    min_score = float(scores.min())
    max_score = float(scores.max())
    mean_score = float(scores.mean())
    std_score = float(scores.std())

    logger.info(
        "[SRV][ranking] ranking_stats min=%.4f max=%.4f mean=%.4f std=%.4f count=%d",
        min_score,
        max_score,
        mean_score,
        std_score,
        scores.shape[0],
    )

    low_std_threshold = float(_CFG["recommendation"]["ranking"]["low_std_threshold"])
    if std_score < low_std_threshold:
        logger.warning("[SRV][ranking] low_std_deviation detected std=%.4f", std_score)

    # Select top_k
    n = scores.shape[0]
    k = min(top_k, n)
    top_indices = np.argsort(-scores)[:k]

    ranked: List[RankedCandidate] = []
    for idx in top_indices:
        base = dict(refined_candidates[int(idx)])
        base["score"] = float(scores[int(idx)])
        # Remove internal-only fields from output to keep JSON clean
        base.pop("_embedding", None)
        ranked.append(base)

    return ranked

