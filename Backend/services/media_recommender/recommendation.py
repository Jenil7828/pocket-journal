import logging
from typing import Dict, Optional, Any

import numpy as np

from .candidate_generator import generate_candidates, refine_candidates
from .intent_builder import build_intent_vector, build_semantic_query
from .providers.books_provider import GoogleBooksProvider
from .providers.podcast_provider import PodcastAPIProvider
from .providers.spotify_provider import SpotifyProvider
from .providers.tmdb_provider import TMDbProvider
from .ranking_engine import rank_candidates

logger = logging.getLogger("pocket_journal.media.recommendation")

_PROVIDER_CACHE: Dict[str, object] = {}


def _get_provider(media_type: str):
    key = media_type.lower()
    if key in _PROVIDER_CACHE:
        return _PROVIDER_CACHE[key]

    if key in ("movie", "movies", "tmdb"):
        provider = TMDbProvider()
    elif key in ("song", "songs", "spotify"):
        provider = SpotifyProvider()
    elif key in ("book", "books", "google_books"):
        provider = GoogleBooksProvider()
    elif key in ("podcast", "podcasts"):
        provider = PodcastAPIProvider()
    else:
        raise ValueError(f"Unsupported media_type: {media_type}")

    _PROVIDER_CACHE[key] = provider
    return provider


def recommend_media(
    uid: str,
    media_type: str,
    *,
    filters: Optional[Dict[str, Any]] = None,
    fetch_limit: int = 200,
    refine_top: int = 100,
    top_k: int = 10,
) -> Dict[str, object]:
    """Unified entry point for Phase 2 media recommendations (frozen).

    - Intent building (taste + journal + adaptive beta) is unchanged.
    - Retrieval uses provider.fetch_candidates(query, filters, limit=200).
    - Cleaning removes empty/junk/duplicates.
    - Refinement embeds cleaned pool once and keeps top 100 by similarity.
    - Ranking remains unchanged.
    """
    # Build intent vector (unchanged)
    intent_vec, emotional_intensity, beta = build_intent_vector(uid, media_type)
    intent_vec = np.asarray(intent_vec, dtype=np.float32).reshape(-1)

    # Log intent observability
    logger.info(
        "pocket_journal.media.intent: uid=%s media_type=%s beta=%.4f emotional_intensity=%.4f",
        uid,
        media_type,
        float(beta),
        float(emotional_intensity),
    )

    # Build a lightweight semantic query (from journal or fallback)
    semantic_query = build_semantic_query(uid, media_type)
    logger.info("pocket_journal.media.filters: semantic_query=%s filters=%s", semantic_query, filters)

    provider = _get_provider(media_type.split(":", 1)[0])

    # Candidate generation (hard constraints via filters) - Phase2 fixed limit
    raw_candidates = generate_candidates(provider=provider, query=semantic_query, filters=filters, fetch_limit=fetch_limit)
    if not raw_candidates:
        logger.warning("No candidates returned for uid=%s media_type=%s filters=%s query=%s", uid, media_type, filters, semantic_query)
        return {
            "uid": uid,
            "media_type": media_type,
            "results": [],
            "warning": "No candidates available",
        }

    # Embedding refinement (unchanged design) - keep top `refine_top`
    refined_pool = refine_candidates(intent_vector=intent_vec, raw_candidates=raw_candidates, refine_top=refine_top)

    # Log refined pool size (reduce duplication; refine_candidates logs top3 sims)
    logger.info(
        "pocket_journal.media.recommendation: uid=%s media_type=%s raw_candidates=%d refined_pool=%d",
        uid,
        media_type,
        len(raw_candidates),
        len(refined_pool),
    )

    results = rank_candidates(
        intent_vector=intent_vec,
        refined_candidates=refined_pool,
        top_k=top_k,
    )

    response: Dict[str, object] = {
        "uid": uid,
        "media_type": media_type,
        "emotional_intensity": float(emotional_intensity),
        "journal_weight": float(beta),
        "candidate_count": len(refined_pool),
        "results": results,
    }

    logger.info(
        "pocket_journal.media.recommendation: uid=%s media_type=%s semantic_query=%s filters=%s raw_candidates=%d refined_pool=%d top_k=%d",
        uid,
        media_type,
        semantic_query,
        filters,
        len(raw_candidates),
        len(refined_pool),
        len(results),
    )

    return response

