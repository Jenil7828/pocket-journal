"""
Advanced Ranking Engine - Phase 5

Implements sophisticated ranking with:
- MMR (Maximal Marginal Relevance) for diversity
- Temporal decay for time-sensitive scoring
- Context-aware boosting
- Hybrid scoring combining multiple factors
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional

import numpy as np

from config_loader import get_config

logger = logging.getLogger("pocket_journal.ranking.advanced")

_CFG = get_config()


# ============================================================================
# TEMPORAL DECAY
# ============================================================================

def compute_temporal_decay(
    interaction_timestamp: str,
    current_time: Optional[datetime] = None,
    decay_rate: Optional[float] = None,
) -> float:
    """Apply exponential decay to interaction weights based on age.
    
    Formula:
        weight = exp(-decay_rate * time_diff_days)
    
    Args:
        interaction_timestamp: ISO timestamp of interaction (e.g., "2026-03-20T10:30:00")
        current_time: Reference time (defaults to now)
        decay_rate: Decay coefficient (default from config: 0.15 per day, or None to use config)
    
    Returns:
        Decay multiplier in [0, 1] (1.0 for recent, <1.0 for older)
    """
    try:
        # Use config default if not provided
        if decay_rate is None:
            decay_rate = float(_CFG.get("recommendation", {}).get("ranking", {}).get("temporal_decay_rate", 0.15))
        
        if current_time is None:
            current_time = datetime.now()
        
        # Parse interaction timestamp
        if isinstance(interaction_timestamp, str):
            # Try ISO format
            try:
                interaction_dt = datetime.fromisoformat(interaction_timestamp.replace('Z', '+00:00'))
            except:
                try:
                    interaction_dt = datetime.fromisoformat(interaction_timestamp)
                except:
                    logger.warning("Failed to parse timestamp: %s", interaction_timestamp)
                    return 1.0
        else:
            interaction_dt = interaction_timestamp
        
        # Make both naive or aware for comparison
        if interaction_dt.tzinfo is not None:
            current_time = current_time.replace(tzinfo=interaction_dt.tzinfo)
        
        # Calculate time difference in days
        time_diff = (current_time - interaction_dt).total_seconds() / (24 * 3600)
        time_diff = max(0, time_diff)  # Clamp to non-negative
        
        # Apply exponential decay
        decay_multiplier = float(np.exp(-decay_rate * time_diff))
        
        logger.debug(
            "pocket_journal.ranking.temporal_decay: timestamp=%s time_diff_days=%.2f decay_multiplier=%.4f",
            interaction_timestamp,
            time_diff,
            decay_multiplier,
        )
        
        return decay_multiplier
        
    except Exception as e:
        logger.error("Error computing temporal decay: %s", str(e))
        return 1.0


# ============================================================================
# CONTEXT-AWARE BOOSTING
# ============================================================================

def get_time_of_day_context() -> Tuple[str, float]:
    """Determine time of day and return context type with multiplier.
    
    Returns:
        (context_name, multiplier)
    """
    hour = datetime.now().hour
    
    if 6 <= hour < 12:
        return "morning", 1.0
    elif 12 <= hour < 18:
        return "afternoon", 1.0
    elif 18 <= hour < 22:
        return "evening", 1.05  # Slightly boost evening recommendations
    else:
        return "night", 1.1  # Boost calm content at night


def get_mood_context_boosting(
    mood: Optional[str],
    item_metadata: Dict[str, Any],
) -> float:
    """Apply mood-based content boosting.
    
    Examples:
    - Sad mood → boost uplifting/happy content
    - Excited mood → boost energetic content
    - Relaxed mood → boost calm/chill content
    
    Args:
        mood: User's mood (e.g., "happy", "sad", "excited")
        item_metadata: Item metadata (title, genre, etc.)
    
    Returns:
        Mood context multiplier (>= 1.0)
    """
    if not mood:
        return 1.0
    
    mood = mood.lower().strip()
    
    # Extract genre/mood from metadata
    genres = []
    if isinstance(item_metadata, dict):
        genres = item_metadata.get("genres", [])
        if isinstance(genres, str):
            genres = [genres]
    
    genre_str = " ".join(str(g).lower() for g in genres)
    
    # Mood-based boosting rules
    boost_rules = {
        "sad": {
            "keywords": ["happy", "uplifting", "energetic", "pop", "dance"],
            "boost": 1.15,
        },
        "happy": {
            "keywords": ["happy", "uplifting", "pop", "dance", "upbeat"],
            "boost": 1.10,
        },
        "excited": {
            "keywords": ["energetic", "rock", "hip-hop", "electronic", "dance"],
            "boost": 1.12,
        },
        "relaxed": {
            "keywords": ["calm", "chill", "ambient", "jazz", "instrumental", "lo-fi"],
            "boost": 1.10,
        },
        "angry": {
            "keywords": ["rock", "metal", "hip-hop", "intense"],
            "boost": 1.10,
        },
        "thoughtful": {
            "keywords": ["jazz", "classical", "ambient", "indie", "alternative"],
            "boost": 1.08,
        },
    }
    
    rules = boost_rules.get(mood, {})
    if not rules:
        return 1.0
    
    keywords = rules.get("keywords", [])
    boost = rules.get("boost", 1.0)
    
    # Check if any keyword matches
    for keyword in keywords:
        if keyword.lower() in genre_str:
            logger.debug(
                "pocket_journal.ranking.mood_boost: mood=%s keyword=%s boost=%.2f",
                mood,
                keyword,
                boost,
            )
            return boost
    
    return 1.0


def compute_recency_score(
    interaction_timestamp: Optional[str],
    max_age_days: int = 30,
) -> float:
    """Score based on recency of interaction.
    
    Linear scoring: recent items score higher.
    
    Args:
        interaction_timestamp: ISO timestamp
        max_age_days: Age at which score becomes 0
    
    Returns:
        Recency score in [0, 1]
    """
    if not interaction_timestamp:
        return 0.5  # Default mid-range score
    
    try:
        decay_mult = compute_temporal_decay(interaction_timestamp)
        # Map decay (0-1) to recency score (0-1)
        recency_score = decay_mult ** (1 / max_age_days)
        return min(1.0, max(0.0, recency_score))
    except Exception as e:
        logger.error("Error computing recency score: %s", str(e))
        return 0.5


# ============================================================================
# MMR (MAXIMAL MARGINAL RELEVANCE)
# ============================================================================

def apply_mmr_diversification(
    candidates: List[Dict[str, Any]],
    intent_vector: np.ndarray,
    lambda_param: Optional[float] = None,
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """Apply Maximal Marginal Relevance for diversity.
    
    Iteratively selects items that maximize:
        score = λ * similarity(user, item) - (1-λ) * max_similarity(item, selected)
    
    This balances relevance with diversity.
    
    Args:
        candidates: List of candidate items with '_embedding' field
        intent_vector: User intent vector (normalized)
        lambda_param: Relevance weight (0-1, default from config 0.7)
        top_k: Number of items to select
    
    Returns:
        Top-k diverse items in MMR order
    """
    if not candidates or not len(candidates):
        return []
    
    try:
        # Use config default if not provided
        if lambda_param is None:
            lambda_param = float(_CFG.get("recommendation", {}).get("ranking", {}).get("mmr_lambda", 0.7))
        
        intent_vec = np.asarray(intent_vector, dtype=np.float32).reshape(-1)
        
        # Compute all similarities with user vector
        similarities = {}
        for i, item in enumerate(candidates):
            emb = item.get("_embedding")
            if emb is None:
                similarities[i] = 0.0
                continue
            
            emb = np.asarray(emb, dtype=np.float32).reshape(-1)
            try:
                sim = float(np.dot(intent_vec, emb) / (np.linalg.norm(intent_vec) * np.linalg.norm(emb) + 1e-8))
            except:
                sim = 0.0
            similarities[i] = sim
        
        # MMR selection
        selected_indices = []
        remaining_indices = set(range(len(candidates)))
        
        for _ in range(min(top_k, len(candidates))):
            if not remaining_indices:
                break
            
            best_idx = None
            best_score = -float('inf')
            
            for idx in remaining_indices:
                relevance = similarities.get(idx, 0.0)
                
                # Compute max diversity penalty
                diversity_penalty = 0.0
                if selected_indices:
                    selected_embeddings = [
                        np.asarray(candidates[sel_idx].get("_embedding"), dtype=np.float32).reshape(-1)
                        for sel_idx in selected_indices
                    ]
                    item_emb = np.asarray(candidates[idx].get("_embedding"), dtype=np.float32).reshape(-1)
                    
                    max_sim_with_selected = 0.0
                    for sel_emb in selected_embeddings:
                        try:
                            sim = float(np.dot(item_emb, sel_emb) / (np.linalg.norm(item_emb) * np.linalg.norm(sel_emb) + 1e-8))
                        except:
                            sim = 0.0
                        max_sim_with_selected = max(max_sim_with_selected, sim)
                    
                    diversity_penalty = max_sim_with_selected
                
                # MMR score
                mmr_score = lambda_param * relevance - (1 - lambda_param) * diversity_penalty
                
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx
            
            if best_idx is not None:
                selected_indices.append(best_idx)
                remaining_indices.remove(best_idx)
        
        # Return selected items in order
        result = [candidates[idx] for idx in selected_indices]
        
        logger.info(
            "pocket_journal.ranking.mmr: selected=%d lambda=%.2f diversity_applied=True",
            len(result),
            lambda_param,
        )
        
        return result
        
    except Exception as e:
        logger.error("Error applying MMR: %s", str(e))
        return candidates[:top_k]


# ============================================================================
# HYBRID SCORING
# ============================================================================

def compute_hybrid_score(
    base_similarity: float,
    interaction_frequency: float = 0.0,
    popularity_score: float = 0.0,
    recency_score: float = 0.5,
    mood: Optional[str] = None,
    item_metadata: Optional[Dict[str, Any]] = None,
    last_interaction_timestamp: Optional[str] = None,
    weights: Optional[Dict[str, float]] = None,
) -> Tuple[float, Dict[str, float]]:
    """Compute final hybrid score combining multiple factors.
    
    Weights (default):
    - Similarity: 0.5
    - Interaction frequency: 0.2
    - Popularity: 0.2
    - Recency: 0.1
    
    Plus mood and time-based context multipliers.
    
    Args:
        base_similarity: Cosine similarity with user vector
        interaction_frequency: Normalized frequency (0-1)
        popularity_score: Normalized popularity (0-1)
        recency_score: Recency score (0-1)
        mood: User mood for context boosting
        item_metadata: Item metadata for mood/content matching
        last_interaction_timestamp: For temporal decay
        weights: Custom component weights
    
    Returns:
        (final_score, component_scores_dict)
    """
    if weights is None:
        weights = {
            "similarity": 0.5,
            "interaction_frequency": 0.2,
            "popularity": 0.2,
            "recency": 0.1,
        }
    
    # Ensure weights sum to 1.0
    weight_sum = sum(weights.values())
    if weight_sum > 0:
        weights = {k: v / weight_sum for k, v in weights.items()}
    
    # Compute base hybrid score
    hybrid_base = (
        weights.get("similarity", 0.5) * float(base_similarity) +
        weights.get("interaction_frequency", 0.2) * float(interaction_frequency) +
        weights.get("popularity", 0.2) * float(popularity_score) +
        weights.get("recency", 0.1) * float(recency_score)
    )
    
    # Apply context multipliers
    time_context, time_multiplier = get_time_of_day_context()
    mood_multiplier = get_mood_context_boosting(mood, item_metadata or {})
    
    # Apply temporal decay if timestamp available
    temporal_decay = 1.0
    if last_interaction_timestamp:
        temporal_decay = compute_temporal_decay(last_interaction_timestamp)
    
    # Final score
    final_score = hybrid_base * time_multiplier * mood_multiplier * temporal_decay
    
    # Component breakdown
    components = {
        "base_similarity": float(base_similarity),
        "interaction_frequency": float(interaction_frequency),
        "popularity": float(popularity_score),
        "recency": float(recency_score),
        "hybrid_base": float(hybrid_base),
        "time_context": time_context,
        "time_multiplier": float(time_multiplier),
        "mood_multiplier": float(mood_multiplier),
        "temporal_decay": float(temporal_decay),
        "final_score": float(final_score),
    }
    
    return float(final_score), components



