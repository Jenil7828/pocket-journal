import logging
import threading
import time
from typing import Dict, Optional, Any

import numpy as np

from config_loader import get_config
from .candidate_generator import generate_candidates, refine_candidates
from .intent_builder import build_intent_vector, build_semantic_query
from .providers.books_provider import GoogleBooksProvider
from .providers.podcast_provider import PodcastAPIProvider
from .providers.spotify_provider import SpotifyProvider
from .providers.tmdb_provider import TMDbProvider
from .ranking_engine import rank_candidates
from .response_formatter import format_results

logger = logging.getLogger("pocket_journal.media.recommendation")

_CFG = get_config()
_PROVIDER_CACHE: Dict[str, object] = {}


def _get_provider(media_type: str):
    """Get or create a cached provider instance."""
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


def _get_language_from_filters(filters: Optional[Dict[str, Any]], media_type: str) -> Optional[str]:
    """Extract language from filters, only for songs and podcasts."""
    if not filters or not media_type:
        return None

    media_base = media_type.lower().split(":", 1)[0]
    if media_base not in ("song", "songs", "spotify", "podcast", "podcasts"):
        return None

    lang = filters.get("language")
    if not lang:
        return None

    lang_lower = str(lang).lower().strip()
    if lang_lower in ("hi", "hindi"):
        return "hindi"
    elif lang_lower in ("en", "english"):
        return "english"

    return None


def _trigger_background_refresh(media_type: str) -> None:
    """Start a daemon thread to refresh cache in the background."""
    def bg_task():
        try:
            from scripts.cache_media import refresh_cache
            refresh_cache(media_type)
            logger.info("pocket_journal.media.phase3: background_refresh_completed media_type=%s", media_type)
        except Exception as e:
            logger.warning("pocket_journal.media.phase3: background_refresh_failed media_type=%s error=%s", media_type, str(e))

    thread = threading.Thread(target=bg_task, daemon=True)
    thread.start()


def recommend_media(
    uid: str,
    media_type: str,
    *,
    filters: Optional[Dict[str, Any]] = None,
    fetch_limit: Optional[int] = None,
    refine_top: Optional[int] = None,
    top_k: Optional[int] = None,
) -> Dict[str, object]:
    """Unified media recommendation with cache-first pipeline.

    Step 1: Build intent vector
    Step 2: Try reading from cache
    Step 3: If cache hit, rank from cache
    Step 4: If cache miss, use live pipeline

    Always returns a dict with 'uid', 'media_type', 'results', 'source'.
    Never raises. Never returns 500.
    """

    # Use config defaults if not provided
    if fetch_limit is None:
        fetch_limit = int(_CFG["recommendation"]["fetch_limit"])
    if refine_top is None:
        refine_top = int(_CFG["recommendation"]["refine_top"])
    if top_k is None:
        top_k = int(_CFG["recommendation"]["top_k"])

    # Step 1: Build intent vector
    try:
        intent_vec, emotional_intensity, beta = build_intent_vector(uid, media_type)
        intent_vec = np.asarray(intent_vec, dtype=np.float32).reshape(-1)
        logger.info(
            "pocket_journal.media.intent: uid=%s media_type=%s beta=%.4f emotional_intensity=%.4f",
            uid,
            media_type,
            float(beta),
            float(emotional_intensity),
        )
    except Exception as e:
        logger.error("pocket_journal.media.recommendation: Failed to build intent vector uid=%s media_type=%s error=%s", uid, media_type, str(e))
        return {
            "uid": uid,
            "media_type": media_type,
            "results": [],
            "source": "fallback",
            "warning": "No candidates available",
        }

    language = _get_language_from_filters(filters, media_type)

    # Step 2: Try reading from cache
    cache_hit = False
    cached_candidates = []
    try:
        from .cache_store import MediaCacheStore
        from persistence.db_manager import DBManager

        db_manager = DBManager(firebase_json_path=None)
        fs = db_manager.db

        cache_store = MediaCacheStore(fs)
        cached_candidates = cache_store.read_cache(media_type, language=language)

        if cached_candidates:
            cache_hit = True
            logger.info(
                "pocket_journal.media.phase3: cache_hit media_type=%s items=%d language=%s",
                media_type,
                len(cached_candidates),
                language,
            )
            # Check if cache is fresh; if not, trigger background refresh
            try:
                is_fresh = cache_store.is_cache_fresh(media_type)
                if not is_fresh:
                    _trigger_background_refresh(media_type)
            except Exception:
                pass
    except Exception as e:
        logger.warning("pocket_journal.media.phase3: cache_read_failed media_type=%s error=%s", media_type, str(e))

    # Step 3: If cache hit, rank and return
    if cache_hit and cached_candidates:
        try:
            # Compute similarity for items with embeddings
            refined_pool = []
            for item in cached_candidates:
                if item.get("embedding"):
                    emb = np.asarray(item["embedding"], dtype=np.float32).reshape(-1)
                    try:
                        similarity = float(np.dot(intent_vec, emb) / (np.linalg.norm(intent_vec) * np.linalg.norm(emb) + 1e-8))
                    except Exception:
                        similarity = 0.0
                    item["_embedding"] = item["embedding"]
                    item["similarity"] = similarity
                refined_pool.append(item)

            results = rank_candidates(intent_vector=intent_vec, refined_candidates=refined_pool, top_k=top_k)
            formatted = format_results(media_type, results)

            logger.info(
                "pocket_journal.media.recommendation: cache_return uid=%s media_type=%s results=%d source=cache",
                uid,
                media_type,
                len(formatted),
            )

            return {
                "uid": uid,
                "media_type": media_type,
                "results": formatted,
                "source": "cache",
            }
        except Exception as e:
            logger.warning("pocket_journal.media.phase3: cache_ranking_failed uid=%s media_type=%s error=%s", uid, media_type, str(e))

    # Step 4: Live pipeline fallback
    try:
        logger.warning(
            "pocket_journal.media.phase3: cache_miss_fallback_to_live media_type=%s language=%s",
            media_type,
            language,
        )

        semantic_query = build_semantic_query(uid, media_type)
        logger.info("pocket_journal.media.filters: semantic_query=%s filters=%s", semantic_query, filters)

        provider = _get_provider(media_type.split(":", 1)[0])
        raw_candidates = generate_candidates(provider=provider, query=semantic_query, filters=filters, fetch_limit=fetch_limit)

        if not raw_candidates:
            logger.warning("pocket_journal.media.phase3: no_candidates uid=%s media_type=%s", uid, media_type)
            return {
                "uid": uid,
                "media_type": media_type,
                "results": [],
                "source": "fallback",
                "warning": "No candidates available",
            }

        refined_pool = refine_candidates(intent_vector=intent_vec, raw_candidates=raw_candidates, refine_top=refine_top)

        results = rank_candidates(intent_vector=intent_vec, refined_candidates=refined_pool, top_k=top_k)
        formatted = format_results(media_type, results)

        logger.info(
            "pocket_journal.media.recommendation: live_return uid=%s media_type=%s results=%d source=live",
            uid,
            media_type,
            len(formatted),
        )

        return {
            "uid": uid,
            "media_type": media_type,
            "results": formatted,
            "source": "live",
        }

    except Exception as e:
        logger.error("pocket_journal.media.recommendation: live_pipeline_failed uid=%s media_type=%s error=%s", uid, media_type, str(e))
        return {
            "uid": uid,
            "media_type": media_type,
            "results": [],
            "source": "fallback",
            "warning": "No candidates available",
        }


