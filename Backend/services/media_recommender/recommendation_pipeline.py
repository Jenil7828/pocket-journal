"""
Unified media recommendation pipeline service.

Implements the corrected pipeline for all media types:
  1. Fetch large candidate pool from cache (~300 items)
  2. Apply hard filters (genre, search, mood)
  3. Apply personalized ranking
  4. Apply sorting (optional)
  5. Paginate
  6. Strip internal fields (embeddings, similarity)

This shared service eliminates code duplication across all media types
(movies, songs, books, podcasts) while ensuring consistent behavior.
"""

import logging
import numpy as np
from typing import Tuple, List, Dict, Any, Optional

from config_loader import get_config
from services.media_recommender.cache_store import MediaCacheStore
from services.media_recommender.intent_builder import build_intent_vector
from services.media_recommender.enhanced_ranking_engine import rank_candidates_phase5
from services.media_recommender.response_schema import strip_internal_fields_list
from persistence.db_manager import DBManager

# Clean root logger - no module prefix
logger = logging.getLogger()
_CFG = get_config()


class RecommendationPipeline:
    """Unified recommendation pipeline for all media types."""
    
    def __init__(self):
        """Initialize the pipeline service."""
        self.cache_store = None
        try:
            db_manager = DBManager(firebase_json_path=None)
            self.cache_store = MediaCacheStore(db_manager.db)
        except Exception as e:
            logger.warning(f"[ERR][pipeline] cache_init_failed error={str(e)}")
    
    def get_recommendations(
        self,
        uid: str,
        media_type: str,
        genre: Optional[str] = None,
        mood: Optional[str] = None,
        search: Optional[str] = None,
        sort: Optional[str] = None,
        language: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get recommendations with filtering, ranking, and sorting.
        
        Pipeline:
          1. Fetch large candidate pool from cache
          2. Apply hard filters (genre, search, mood)
          3. Apply personalized ranking
          4. Apply sorting
          5. Paginate
          6. Strip internal fields
        
        Args:
            uid: User ID
            media_type: "movies", "songs", "books", or "podcasts"
            genre: Optional genre filter
            mood: Optional mood filter
            search: Optional search query
            sort: Optional sort order (default, rating, trending, recent)
            language: Optional language filter (songs/podcasts only)
            limit: Results per page (1-100)
            offset: Pagination offset
        
        Returns:
            Tuple of (results list, total count after filtering)
        """
        # Validate parameters
        limit = max(1, min(limit, 100))
        offset = max(0, offset)
        
        # Step 1: Fetch large candidate pool
        candidates = self._fetch_candidates(media_type, language)
        
        if not candidates:
            logger.warning(
                f"[SRV][pipeline] no_candidates media_type={media_type}"
            )
            return [], 0
        
        # Step 2: Apply hard filters (on large pool before ranking)
        filtered = self._apply_filters(
            candidates,
            genre=genre,
            search_query=search,
            mood=mood
        )
        
        if not filtered and (genre or search or mood):
            # Fallback: if filters removed everything, return unfiltered ranked results
            logger.warning(
                f"[SRV][pipeline] all_items_filtered media_type={media_type}"
            )
            filtered = candidates
        
        # Step 3: Apply personalized ranking to filtered candidates
        # Pass desired_k (limit + offset) so ranking returns at least as many
        # items as needed for pagination. Previously top_k was capped to the
        # config default which caused the API to return only 10 results.
        desired_k = limit + offset
        ranked = self._rank_candidates(uid, filtered, media_type, desired_k=desired_k)
        
        # Step 4: Apply sorting
        sorted_items = self._apply_sorting(ranked, sort)
        
        # Step 5: Calculate total after filtering/sorting
        total_count = len(sorted_items)
        
        # Step 6: Paginate
        paginated = sorted_items[offset : offset + limit]
        
        # Step 7: Strip internal fields (embeddings, similarity)
        clean_results = self._strip_internal_fields(paginated)
        
        logger.info(
            f"[SRV][pipeline] recommendations_returned media_type={media_type} "
            f"total={total_count} returned={len(clean_results)} offset={offset} limit={limit}"
        )
        
        return clean_results, total_count
    
    def _fetch_candidates(self, media_type: str, language: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch large candidate pool from cache.
        
        Args:
            media_type: Media type to fetch
            language: Optional language filter (for songs/podcasts)
        
        Returns:
            List of ~300 candidate items
        """
        try:
            if not self.cache_store:
                logger.warning(f"[ERR][pipeline] cache_store_not_initialized media_type={media_type}")
                return []
            
            candidates = self.cache_store.read_cache(media_type, language=language)
            logger.debug(
                f"[SRV][pipeline] candidates_fetched media_type={media_type} language={language} count={len(candidates)}"
            )
            return candidates
        except Exception as e:
            logger.warning(
                f"[ERR][pipeline] fetch_candidates_failed media_type={media_type} error={str(e)}"
            )
            return []
    
    def _apply_filters(
        self,
        items: List[Dict[str, Any]],
        genre: Optional[str] = None,
        search_query: Optional[str] = None,
        mood: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Apply hard filters to candidate items.
        
        Args:
            items: Candidate items to filter
            genre: Optional genre filter (case-insensitive partial match)
            search_query: Optional search query (title/description)
            mood: Optional mood filter
        
        Returns:
            Filtered items
        """
        filtered = items
        
        # Genre filter
        if genre:
            genre_lower = genre.lower().strip()
            before_count = len(filtered)
            filtered = [
                item for item in filtered
                if item.get("genres") and any(
                    genre_lower in g.lower() for g in item.get("genres", [])
                    if isinstance(g, str)
                )
            ]
            logger.debug(
                f"[SRV][pipeline] genre_filter_applied genre={genre} before={before_count} after={len(filtered)}"
            )
        
        # Search filter
        if search_query:
            query_lower = search_query.lower().strip()
            before_count = len(filtered)
            filtered = [
                item for item in filtered
                if (query_lower in (item.get("title") or "").lower()
                    or query_lower in (item.get("description") or "").lower())
            ]
            logger.debug(
                f"[SRV][pipeline] search_filter_applied query={search_query} before={before_count} after={len(filtered)}"
            )
        
        # Mood filter
        if mood:
            mood_lower = mood.lower().strip()
            before_count = len(filtered)
            filtered = [
                item for item in filtered
                if mood_lower in (item.get("mood_tag") or "").lower()
                or any(mood_lower in g.lower() for g in item.get("genres", []) if isinstance(g, str))
            ]
            logger.debug(
                f"[SRV][pipeline] mood_filter_applied mood={mood} before={before_count} after={len(filtered)}"
            )
        
        return filtered
    
    def _rank_candidates(
        self,
        uid: str,
        candidates: List[Dict[str, Any]],
        media_type: str,
        desired_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Apply personalized ranking to candidates.
        
        Args:
            uid: User ID
            candidates: Items to rank
            media_type: Media type for ranking context
        
        Returns:
            Ranked items
        """
        if not candidates:
            return []
        
        try:
            # Build intent vector from user taste
            intent_vec, emotional_intensity, beta = build_intent_vector(uid, media_type)
            intent_vec = np.asarray(intent_vec, dtype=np.float32).reshape(-1)

            logger.debug(
                f"[SRV][pipeline] ranking_intent_built media_type={media_type} beta={beta:.4f} items={len(candidates)}"
            )

            # Limit number of candidates to a configurable max to avoid pathological
            # runtime in Phase 5 (MMR and hybrid ranking can be O(n^2)). When no
            # restrictive filters (e.g., genre) are provided, the candidate pool may
            # be very large which leads to long response times. Trim by popularity
            # as a cheap heuristic.
            try:
                max_candidates = int(_CFG.get("recommendation", {}).get("ranking", {}).get("max_candidates_for_ranking", 500))
            except Exception:
                max_candidates = 500

            if len(candidates) > max_candidates:
                # Trim to top-N by popularity (descending)
                candidates = sorted(candidates, key=lambda x: float(x.get("popularity") or 0), reverse=True)[:max_candidates]
                logger.info(f"[SRV][pipeline] trimmed_candidates_for_ranking media_type={media_type} kept={len(candidates)}")

            # Add similarity scores to candidates
            for item in candidates:
                if item.get("embedding"):
                    emb = np.asarray(item["embedding"], dtype=np.float32).reshape(-1)
                    try:
                        similarity = float(np.dot(intent_vec, emb) / (np.linalg.norm(intent_vec) * np.linalg.norm(emb) + 1e-8))
                    except Exception:
                        similarity = 0.0
                    item["_embedding"] = item["embedding"]
                    item["similarity"] = similarity

            # Apply Phase 5 ranking with MMR + hybrid scoring
            use_phase5 = _CFG.get("recommendation", {}).get("ranking", {}).get("use_phase5", True)

            if use_phase5:
                # Determine how many items Phase5 should return. Ensure we at
                # minimum return the configured `recommendation.top_k` and also
                # respect the calling endpoint's requested pagination size
                # (`desired_k`). Cap to the available candidate count.
                config_top_k = int(_CFG.get("recommendation", {}).get("top_k", 10))
                desired_val = int(desired_k) if desired_k is not None else config_top_k
                top_k = min(len(candidates), max(config_top_k, desired_val))
                ranked = rank_candidates_phase5(
                    intent_vector=intent_vec,
                    candidates=candidates,
                    uid=uid,
                    user_mood=None,
                    use_mmr=True,
                    use_hybrid=True,
                    use_temporal_decay=True,
                    top_k=top_k,
                )
            else:
                # Fallback: sort by similarity
                ranked = sorted(candidates, key=lambda x: (x.get("similarity") or 0), reverse=True)

            logger.debug(
                f"[SRV][pipeline] candidates_ranked media_type={media_type} count={len(ranked)}"
            )
            return ranked
            
        except Exception as e:
            logger.warning(
                f"[ERR][pipeline] ranking_failed media_type={media_type} error={str(e)}"
            )
            return candidates
    
    def _apply_sorting(
        self,
        items: List[Dict[str, Any]],
        sort: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Apply sorting to ranked items.
        
        Args:
            items: Ranked items
            sort: Sort order (default, rating, trending, recent)
        
        Returns:
            Sorted items
        """
        if not sort or sort.lower() == "default":
            return items
        
        sort_lower = sort.lower().strip()
        
        if sort_lower == "rating":
            # Sort by rating (highest first)
            return sorted(items, key=lambda x: (x.get("rating") or 0), reverse=True)
        
        elif sort_lower == "trending":
            # Sort by popularity (highest first)
            return sorted(items, key=lambda x: (x.get("popularity") or 0), reverse=True)
        
        elif sort_lower == "recent":
            # Sort by release_date (newest releases first)
            # Handle Firestore DatetimeWithNanoseconds and string dates
            def get_timestamp_key(item):
                release_date = item.get("release_date")
                if release_date is None:
                    return 0  # Items without release_date go to the end
                # Convert Firestore timestamps to sortable format
                if hasattr(release_date, "timestamp"):
                    # Firestore DatetimeWithNanoseconds has a timestamp() method
                    return release_date.timestamp()
                elif isinstance(release_date, str):
                    # If it's a string, try to parse it (ISO format)
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(release_date.replace('Z', '+00:00'))
                        return dt.timestamp()
                    except Exception:
                        return 0
                else:
                    # For other types, try to convert to float
                    try:
                        return float(release_date)
                    except Exception:
                        return 0
            
            return sorted(items, key=get_timestamp_key, reverse=True)
        
        return items
    
    def _strip_internal_fields(
        self,
        items: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Remove internal fields before returning to client.
        
        Args:
            items: Items to clean
        
        Returns:
            Cleaned items without embeddings or internal scores
        """
        return strip_internal_fields_list(items)


# Singleton instance
_pipeline = None


def get_pipeline() -> RecommendationPipeline:
    """Get or create the singleton pipeline instance."""
    global _pipeline
    if _pipeline is None:
        _pipeline = RecommendationPipeline()
    return _pipeline



