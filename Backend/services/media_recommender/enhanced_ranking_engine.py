"""
Enhanced Ranking Engine - Phase 5

Upgrades the ranking pipeline to use advanced ranking strategies while
maintaining backward compatibility with Phase 4.

New features:
- MMR diversification
- Temporal decay
- Context-aware boosting
- Hybrid scoring
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from config_loader import get_config
from services.media_recommender.advanced_ranking import (
    apply_mmr_diversification,
    compute_hybrid_score,
    compute_temporal_decay,
)

logger = logging.getLogger("pocket_journal.ranking.enhanced")

_CFG = get_config()

RankedCandidate = Dict[str, Any]


def rank_candidates_phase5(
    intent_vector: np.ndarray,
    candidates: List[Dict[str, Any]],
    uid: Optional[str] = None,
    user_mood: Optional[str] = None,
    use_mmr: bool = True,
    use_hybrid: bool = True,
    use_temporal_decay: bool = True,
    top_k: int = 10,
    mmr_lambda: float = 0.7,
) -> List[RankedCandidate]:
    """Rank candidates using Phase 5 advanced strategies.
    
    Pipeline:
    1. Validate and normalize inputs
    2. Compute base similarities
    3. Apply temporal decay to interaction scores
    4. Compute hybrid scores
    5. Apply MMR diversification
    6. Return top-k results
    
    Args:
        intent_vector: User intent vector (normalized)
        candidates: Candidate items with '_embedding' field
        uid: User ID (for logging)
        user_mood: User's mood (for context boosting)
        use_mmr: Whether to apply MMR diversification (default True)
        use_hybrid: Whether to use hybrid scoring (default True)
        use_temporal_decay: Whether to apply temporal decay (default True)
        top_k: Number of results to return
        mmr_lambda: MMR relevance weight (0-1, default 0.7)
    
    Returns:
        List of top-k ranked candidates with phase5_ranking_info
    """
    if not candidates:
        return []
    
    logger.info(
        "pocket_journal.ranking.phase5: start uid=%s num_candidates=%d use_mmr=%s use_hybrid=%s",
        uid or "unknown",
        len(candidates),
        use_mmr,
        use_hybrid,
    )
    
    try:
        intent_vec = np.asarray(intent_vector, dtype=np.float32).reshape(-1)
        
        # ====== Step 1: Compute base similarities ======
        similarities = []
        embeddings_for_mmr = []
        
        for item in candidates:
            emb = item.get("_embedding")
            if emb is None:
                logger.debug("Candidate missing _embedding field, skipping")
                similarities.append(0.0)
                item["_embedding"] = np.zeros_like(intent_vec)
                embeddings_for_mmr.append(np.zeros_like(intent_vec))
                continue
            
            emb = np.asarray(emb, dtype=np.float32).reshape(-1)
            embeddings_for_mmr.append(emb)
            
            try:
                sim = float(np.dot(intent_vec, emb) / (np.linalg.norm(intent_vec) * np.linalg.norm(emb) + 1e-8))
            except:
                sim = 0.0
            similarities.append(sim)
        
        # ====== Step 2: Prepare scores for each candidate ======
        scores_info = []  # List of (score, components_dict, item_idx)
        
        for idx, item in enumerate(candidates):
            base_sim = similarities[idx]
            
            # Extract interaction data
            interaction_freq = 0.0
            if "interaction_count" in item:
                interaction_freq = min(1.0, float(item.get("interaction_count", 0)) / 10.0)
            
            popularity = 0.0
            if "popularity" in item:
                try:
                    popularity = float(item["popularity"])
                    # Normalize popularity to [0, 1]
                    popularity = min(1.0, max(0.0, popularity / 100.0))
                except:
                    popularity = 0.0
            
            # Get recency/last interaction
            last_interaction = None
            if "last_interaction_timestamp" in item:
                last_interaction = item["last_interaction_timestamp"]
            
            # Apply temporal decay if enabled
            temporal_multiplier = 1.0
            if use_temporal_decay and last_interaction:
                temporal_multiplier = compute_temporal_decay(last_interaction)
            
            recency_score = 0.5  # Default mid-range
            if last_interaction:
                from services.media_recommender.advanced_ranking import compute_recency_score
                recency_score = compute_recency_score(last_interaction)
            
            # Compute hybrid or simple score
            if use_hybrid:
                final_score, components = compute_hybrid_score(
                    base_similarity=base_sim,
                    interaction_frequency=interaction_freq,
                    popularity_score=popularity,
                    recency_score=recency_score,
                    mood=user_mood,
                    item_metadata=item.get("metadata") or {},
                    last_interaction_timestamp=last_interaction,
                )
            else:
                # Fall back to simple similarity + popularity
                final_score = 0.8 * base_sim + 0.2 * popularity
                components = {
                    "base_similarity": float(base_sim),
                    "popularity": float(popularity),
                    "final_score": float(final_score),
                }
            
            scores_info.append((final_score, components, idx))
        
        # ====== Step 3: Apply MMR diversification ======
        if use_mmr and len(candidates) > 1:
            # Prepare candidates for MMR
            candidates_for_mmr = []
            for idx in range(len(candidates)):
                item_copy = dict(candidates[idx])
                item_copy["_embedding"] = embeddings_for_mmr[idx]
                candidates_for_mmr.append(item_copy)
            
            # Apply MMR
            diverse_items = apply_mmr_diversification(
                candidates=candidates_for_mmr,
                intent_vector=intent_vec,
                lambda_param=mmr_lambda,
                top_k=top_k,
            )
            
            # Map back to original indices for score lookup
            mmr_indices = []
            for diverse_item in diverse_items:
                for orig_idx, orig_item in enumerate(candidates):
                    if orig_item.get("id") == diverse_item.get("id"):
                        mmr_indices.append(orig_idx)
                        break
            
            # Reorder scores_info by MMR order
            scores_info_reordered = []
            for mmr_idx in mmr_indices:
                for score_tuple in scores_info:
                    if score_tuple[2] == mmr_idx:
                        scores_info_reordered.append(score_tuple)
                        break
            scores_info = scores_info_reordered
        
        # ====== Step 4: Select top-k and format output ======
        ranked: List[RankedCandidate] = []
        
        # Sort by score (should already be sorted from MMR)
        if not use_mmr:
            scores_info.sort(key=lambda x: x[0], reverse=True)
        
        for i, (score, components, orig_idx) in enumerate(scores_info[:top_k]):
            item = dict(candidates[orig_idx])
            item.pop("_embedding", None)  # Remove internal field
            item["score"] = float(score)
            item["ranking_info"] = {
                "phase": 5,
                "rank": i + 1,
                "components": components,
                "mmr_used": use_mmr,
                "hybrid_used": use_hybrid,
            }
            ranked.append(item)
        
        # ====== Logging ======
        if ranked:
            avg_similarity = np.mean([r["ranking_info"]["components"].get("base_similarity", 0) for r in ranked])
            avg_diversity = np.mean([r["ranking_info"]["components"].get("mood_multiplier", 1.0) for r in ranked])
            
            logger.info(
                "pocket_journal.ranking.phase5: complete uid=%s results=%d avg_similarity=%.4f diversity_score=%.4f",
                uid or "unknown",
                len(ranked),
                avg_similarity,
                avg_diversity,
            )
        
        return ranked
        
    except Exception as e:
        logger.error("Error in phase5 ranking: %s", str(e))
        # Fallback to simple ranking
        return _fallback_rank_candidates(intent_vector, candidates, top_k)


def _fallback_rank_candidates(
    intent_vector: np.ndarray,
    candidates: List[Dict[str, Any]],
    top_k: int = 10,
) -> List[RankedCandidate]:
    """Fallback to simple Phase 4 ranking on error."""
    from services.media_recommender.ranking_engine import rank_candidates
    
    logger.warning("Using fallback ranking (Phase 4 mode)")
    return rank_candidates(
        intent_vector=intent_vector,
        refined_candidates=candidates,
        top_k=top_k,
    )

