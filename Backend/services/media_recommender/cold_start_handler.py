"""
Cold Start Handler - Phase 4: Personalization Feedback Loop

Handles cases where users have no taste vector or journal embedding.
Returns popular items from cache as fallback.

Used in recommendation pipeline to ensure no failures due to missing data.
"""

import logging
from typing import List, Dict, Any, Optional

import numpy as np

from services.media_recommender.cache_store import MediaCacheStore

# Clean root logger - no module prefix
logger = logging.getLogger()


class ColdStartHandler:
    """
    Provides fallback recommendations for cold start scenarios.
    """

    def __init__(self, db):
        """
        Args:
            db: Firebase Firestore client
        """
        self.db = db
        self.cache_store = MediaCacheStore(db)

    def get_cold_start_candidates(
        self,
        media_type: str,
        language: Optional[str] = None,
        top_k: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Fetch top popular items from cache when user has no taste vector.

        Strategy:
        1. Read all items from cache
        2. Filter by popularity (click count, save count, etc.)
        3. Return top_k

        Args:
            media_type: One of: songs, movies, books, podcasts
            language: Optional language filter (for songs/podcasts)
            top_k: Number of items to return

        Returns:
            List of items sorted by popularity
        """
        try:
            # Read from cache
            items = self.cache_store.read_cache(media_type, language=language)

            if not items:
                logger.warning(
                    "[SRV][cold_start] no_cache_items media_type=%s language=%s",
                    media_type,
                    language,
                )
                return []

            # Sort by popularity metrics if available
            # Priority: popularity_score → like_count → view_count
            def get_popularity_score(item: Dict[str, Any]) -> float:
                score = 0.0
                if "popularity_score" in item:
                    score += float(item.get("popularity_score", 0)) * 10
                if "like_count" in item:
                    score += float(item.get("like_count", 0)) * 2
                if "view_count" in item:
                    score += float(item.get("view_count", 0)) * 0.1
                if "added_at" in item:
                    # Prefer recently added items slightly
                    score += 0.5
                return score

            sorted_items = sorted(items, key=get_popularity_score, reverse=True)

            result = sorted_items[:top_k]

            logger.info(
                "[SRV][cold_start] candidates_generated media_type=%s top_k=%d returned=%d",
                media_type,
                top_k,
                len(result),
            )

            return result

        except Exception as e:
            logger.error(
                "[ERR][cold_start] failed_to_generate media_type=%s error=%s",
                media_type,
                str(e),
            )
            return []

    def should_use_cold_start(
        self,
        taste_vector: Optional[np.ndarray],
        journal_embedding: Optional[np.ndarray],
    ) -> bool:
        """
        Determine if cold start fallback should be used.

        Returns True if:
        - No taste vector AND no journal embedding

        Returns:
            Boolean indicating if cold start should be used
        """
        has_taste_vector = taste_vector is not None and len(taste_vector) > 0
        has_journal_embedding = journal_embedding is not None and len(journal_embedding) > 0

        should_cold_start = not has_taste_vector and not has_journal_embedding


        return should_cold_start

