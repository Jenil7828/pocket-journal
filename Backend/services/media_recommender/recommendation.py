import logging
from typing import Dict, Tuple

import numpy as np

from .candidate_generator import generate_refined_pool
from .intent_builder import build_intent_vector
from .providers.books_provider import GoogleBooksProvider
from .providers.podcast_provider import PodcastAPIProvider
from .providers.spotify_provider import SpotifyProvider
from .providers.tmdb_provider import TMDbProvider
from .ranking_engine import rank_candidates

logger = logging.getLogger("pocket_journal.media.recommendation")


_PROVIDER_CACHE: Dict[str, object] = {}


def _get_provider(media_type: str, *, language: str | None = None):
    key = media_type.lower()
    if key in _PROVIDER_CACHE:
        return _PROVIDER_CACHE[key]

    if key in ("movie", "movies", "tmdb"):
        provider = TMDbProvider()
    elif key in ("song", "songs", "spotify"):
        # Language preference only affects Spotify market; no mood/genre filtering.
        provider = SpotifyProvider(language=language)
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
    fetch_limit: int = 150,
    refine_top: int = 100,
    top_k: int = 10,
) -> Dict[str, object]:
    """Unified entry point for media recommendations.

    Pipeline:
    - intent_data = build_intent_vector(uid, media_type)
    - provider = provider_map[media_type]
    - refined_pool = generate_refined_pool(intent_vector, provider, fetch_limit, refine_top)
    - results = rank_candidates(intent_vector, refined_pool, top_k)
    """
    intent_vec, emotional_intensity, beta = build_intent_vector(uid, media_type)
    intent_vec = np.asarray(intent_vec, dtype=np.float32).reshape(-1)

    # For songs, allow an optional language hint forwarded via media_type extensions
    provider_language: str | None = None
    if media_type.lower() in ("song", "songs", "spotify"):
        # In Phase 2, language may be encoded as 'songs:en' etc.
        # This function supports both plain 'songs' and 'songs:<lang>' transparently.
        if ":" in media_type:
            _, lang = media_type.split(":", 1)
            provider_language = lang.strip() or None
        else:
            provider_language = None

    provider = _get_provider(media_type.split(":", 1)[0], language=provider_language)

    refined_pool = generate_refined_pool(
        intent_vector=intent_vec,
        provider=provider,
        fetch_limit=fetch_limit,
        refine_top=refine_top,
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
        "recommend_media completed uid=%s media_type=%s candidates=%d top_k=%d",
        uid,
        media_type,
        len(refined_pool),
        len(results),
    )

    return response


