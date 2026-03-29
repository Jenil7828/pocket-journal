"""
Unified Media Search Service — Hybrid Cache-First Strategy with Fuzzy Search

Implements fuzzy search with RapidFuzz for typo tolerance.
"""

import logging
import time
import re
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from rapidfuzz import fuzz
from config_loader import get_config
from services.media_recommender.cache_store import MediaCacheStore
from services.media_recommender.providers.tmdb_provider import TMDbProvider
from services.media_recommender.providers.spotify_provider import SpotifyProvider
from services.media_recommender.providers.books_provider import GoogleBooksProvider
from services.media_recommender.providers.podcast_provider import PodcastAPIProvider
from services.embedding_service import EmbeddingService

logger = logging.getLogger("pocket_journal.search_service")
_CFG = get_config()


def normalize_text(text: str) -> str:
    """Normalize text for fuzzy matching."""
    if not text:
        return ""
    text = re.sub(r'[^\w\s]', '', text.lower())
    return text.strip()


@dataclass
class SearchMetrics:
    """Track search performance."""
    cache_hit_count: int = 0
    fallback_triggered: bool = False
    cache_latency_ms: float = 0.0
    provider_latency_ms: float = 0.0
    final_result_count: int = 0
    deduplication_count: int = 0


class SearchService:
    """Search service with fuzzy matching and cache-first strategy."""

    def __init__(self, db):
        firestore_client = db.db if hasattr(db, 'db') else db
        self.db = firestore_client
        self.cache_store = MediaCacheStore(firestore_client)
        self.embedding_service = EmbeddingService()
        self.providers = {
            "movies": TMDbProvider(),
            "songs": SpotifyProvider(),
            "books": GoogleBooksProvider(),
            "podcasts": PodcastAPIProvider(),
        }

    def _search_cache(self, media_type: str, query: str, language: Optional[str] = None, limit: int = 20) -> Tuple[List[Dict[str, Any]], SearchMetrics]:
        """Search cache with fuzzy scoring and relevance filtering."""
        metrics = SearchMetrics()
        start_time = time.time()
        
        if not query or not query.strip():
            logger.warning("search_cache: empty query")
            return [], metrics
        
        query = query.strip().lower()
        
        try:
            cache_language = language if media_type in {"songs", "podcasts"} else None
            cached_items = self.cache_store.read_cache(media_type, language=cache_language)
        except Exception as e:
            logger.error(f"Cache read failed: {e}")
            return [], metrics
        
        # Score all items
        scored_results = []
        all_scores = []
        
        # Get fuzzy threshold from config
        fuzzy_threshold = _CFG.get("search", {}).get("fuzzy_threshold_relevance", 75)
        
        for item in cached_items:
            score = self._compute_score(item, query, media_type)
            all_scores.append(score)
            scored_results.append((score, item))
        
        # Filter by relevance threshold from config
        relevant_results = [(score, item) for score, item in scored_results if score >= fuzzy_threshold]
        
        # Sort by score DESC, then popularity
        relevant_results.sort(key=lambda x: (-x[0], -self._get_popularity(x[1], media_type)))
        
        # Calculate relevance metrics
        max_score = max(all_scores) if all_scores else 0
        avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
        relevant_count = len(relevant_results)
        
        results = [item for _, item in relevant_results[:limit]]
        metrics.cache_hit_count = relevant_count
        metrics.cache_latency_ms = (time.time() - start_time) * 1000
        
        logger.info(
            f"Cache search: {media_type} '{query}' → {len(results)} relevant "
            f"(avg_score={avg_score:.1f}, max_score={max_score:.1f}, total={len(all_scores)})"
        )
        
        return results, metrics

    def _compute_score(self, item: Dict[str, Any], query: str, media_type: str) -> float:
        """Compute fuzzy match score (0-100)."""
        if not query or not item:
            return 0
        
        query_norm = normalize_text(query)
        if len(query_norm) < 3:
            fields = self._get_searchable_fields(item, media_type)
            for field_value in fields.values():
                if query_norm in normalize_text(str(field_value)):
                    return 50
            return 0
        
        fields = self._get_searchable_fields(item, media_type)
        
        title_score = 0
        title = fields.get("title", "")
        if title:
            title_norm = normalize_text(str(title))
            partial = fuzz.partial_ratio(query_norm, title_norm)
            token_sort = fuzz.token_sort_ratio(query_norm, title_norm)
            title_score = max(partial, token_sort)
        
        description_score = 0
        description = fields.get("description", "")
        if description:
            desc_norm = normalize_text(str(description))
            description_score = fuzz.partial_ratio(query_norm, desc_norm)
        
        return (title_score * 0.7) + (description_score * 0.3)

    def _get_searchable_fields(self, item: Dict[str, Any], media_type: str) -> Dict[str, Any]:
        """Get searchable fields by media type."""
        if media_type == "songs":
            return {"title": item.get("title", ""), "artist_names": item.get("artist_names", ""), "album_name": item.get("album_name", "")}
        elif media_type == "movies":
            return {"title": item.get("title", ""), "description": item.get("description", "")}
        elif media_type == "books":
            authors = " ".join(item.get("authors", [])) if isinstance(item.get("authors"), list) else item.get("authors", "")
            return {"title": item.get("title", ""), "authors": authors, "description": item.get("description", "")}
        elif media_type == "podcasts":
            return {"title": item.get("title", ""), "publisher": item.get("publisher", ""), "description": item.get("description", "")}
        return {}

    def _get_popularity(self, item: Dict[str, Any], media_type: str) -> float:
        """Get popularity score."""
        if media_type in {"songs", "movies", "podcasts"}:
            return item.get("popularity", 0)
        return item.get("rating", 0) if media_type == "books" else 0

    def _should_fallback(self, cache_results: List[Dict], limit: int) -> bool:
        """
        Decide if fallback to providers is needed.
        
        Return True only if NO relevant cache results at all.
        """
        # Fallback if no relevant cache results at all
        return len(cache_results) == 0

    def _search_providers(self, media_type: str, query: str, language: Optional[str] = None, limit: int = 20) -> Tuple[List[Dict[str, Any]], SearchMetrics]:
        """Search providers with fuzzy filtering and priority boost."""
        metrics = SearchMetrics()
        start_time = time.time()
        
        if media_type not in self.providers or not query or not query.strip():
            metrics.provider_latency_ms = (time.time() - start_time) * 1000
            return [], metrics
        
        try:
            provider = self.providers[media_type]
            fetch_limit = min(limit * 2, 100)
            filters = {"language": language} if language and media_type in {"songs", "podcasts"} else None
            
            raw_results = provider.fetch_candidates(query=query, filters=filters, limit=fetch_limit)
            normalized = self._normalize_provider_results(raw_results, media_type)
            
            scored_results = []
            for item in normalized:
                score = self._compute_score(item, query, media_type)
                
                # Provider priority boost: if title closely matches (>= 75), boost by +20
                title = item.get("title", "")
                if title and score >= 75:
                    score = min(100, score + 20)  # Boost but cap at 100
                
                if score >= 50:
                    scored_results.append((score, item))
            
            scored_results.sort(key=lambda x: (-x[0], -self._get_popularity(x[1], media_type)))
            results = [item for _, item in scored_results[:limit]]
            metrics.provider_latency_ms = (time.time() - start_time) * 1000
            
            logger.info(f"Provider search: {media_type} '{query}' → {len(results)} results ({metrics.provider_latency_ms:.1f}ms)")
            return results, metrics
        except Exception as e:
            logger.error(f"Provider search failed: {e}")
            metrics.provider_latency_ms = (time.time() - start_time) * 1000
            return [], metrics

    def _normalize_provider_results(self, results: List[Dict[str, Any]], media_type: str) -> List[Dict[str, Any]]:
        """Normalize provider results."""
        normalized = []
        for item in results:
            if not item:
                continue
            normalized_item = self._normalize_single_item(item, media_type)
            if normalized_item:
                normalized.append(normalized_item)
        return normalized

    def _normalize_single_item(self, item: Dict[str, Any], media_type: str) -> Optional[Dict[str, Any]]:
        """Normalize single item."""
        try:
            if media_type == "songs":
                return {
                    "id": item.get("id") or item.get("track_id"),
                    "title": item.get("title") or item.get("name"),
                    "description": f"Artist: {item.get('artist_names', '')}. Album: {item.get('album_name', '')}",
                    "artist_names": item.get("artist_names", ""),
                    "album_name": item.get("album_name", ""),
                    "album_image_url": item.get("album_image_url") or item.get("poster_url"),
                    "external_url": item.get("external_url") or item.get("url"),
                    "duration_ms": item.get("duration_ms", 0),
                    "popularity": item.get("popularity", 0),
                    "language": item.get("language", "neutral"),
                }
            elif media_type == "movies":
                metadata = item.get("metadata") or {}
                poster_path = item.get("poster_path") or metadata.get("poster_path") or ""
                poster_url = item.get("poster_url") or metadata.get("poster_url") or ""
                if not poster_url and poster_path:
                    poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}"
                return {
                    "id": str(item.get("id") or metadata.get("id") or ""),
                    "title": item.get("title") or metadata.get("title") or "",
                    "description": item.get("description") or metadata.get("description") or metadata.get("overview") or "",
                    "poster_url": poster_url,
                    "rating": float(item.get("rating") or metadata.get("rating") or metadata.get("vote_average") or 0),
                    "release_date": item.get("release_date") or metadata.get("release_date") or "",
                    "popularity": float(item.get("popularity") or metadata.get("popularity") or 0),
                    "language": "neutral",
                }
            elif media_type == "books":
                return {
                    "id": item.get("id") or item.get("google_books_id"),
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                    "authors": item.get("authors", []),
                    "thumbnail_url": item.get("thumbnail_url") or item.get("poster_url"),
                    "published_date": item.get("published_date", ""),
                    "page_count": item.get("page_count", 0),
                    "info_link": item.get("info_link") or item.get("url", ""),
                    "language": "neutral",
                }
            elif media_type == "podcasts":
                return {
                    "id": item.get("id") or item.get("episode_id"),
                    "title": item.get("title") or item.get("name"),
                    "description": item.get("description", ""),
                    "publisher": item.get("publisher") or item.get("show_name", ""),
                    "show_image_url": item.get("show_image_url") or item.get("poster_url"),
                    "external_url": item.get("external_url") or item.get("url"),
                    "duration_ms": item.get("duration_ms", 0),
                    "release_date": item.get("release_date", ""),
                    "language": item.get("language", "neutral"),
                }
        except Exception as e:
            logger.warning(f"Normalization failed: {e}")
        return None

    def _merge_results(self, cache_results: List[Dict[str, Any]], provider_results: List[Dict[str, Any]], media_type: str, limit: int) -> Tuple[List[Dict[str, Any]], int]:
        """Merge and deduplicate results."""
        merged = {}
        for item in cache_results:
            item_id = item.get("id")
            if item_id and item_id not in merged:
                merged[item_id] = item
        
        for item in provider_results:
            item_id = item.get("id")
            if item_id and item_id not in merged:
                merged[item_id] = item
        
        dedup_count = len(cache_results) + len(provider_results) - len(merged)
        final_results = list(merged.values())[:limit]
        
        logger.info(f"Merged: cache={len(cache_results)}, provider={len(provider_results)}, dedup={dedup_count}, final={len(final_results)}")
        
        return final_results, dedup_count

    def _write_cache_async(self, media_type: str, items: List[Dict[str, Any]]) -> None:
        """Async cache write."""
        if not items:
            return
        try:
            executor = ThreadPoolExecutor(max_workers=1)
            executor.submit(self._write_cache_worker, media_type, items)
        except Exception as e:
            logger.error(f"Cache write task failed: {e}")

    def _write_cache_worker(self, media_type: str, items: List[Dict[str, Any]]) -> None:
        """Background cache enrichment."""
        try:
            start_time = time.time()
            enriched_items = []
            
            for item in items:
                if not item:
                    continue
                try:
                    text_for_embedding = self._build_embedding_text(item, media_type)
                    embedding = self.embedding_service.embed_text(text_for_embedding)
                    item["embedding"] = embedding.tolist() if hasattr(embedding, "tolist") else list(embedding)
                    if "language" not in item:
                        item["language"] = "neutral"
                    from datetime import datetime, timezone
                    item["cached_at"] = datetime.now(timezone.utc).isoformat()
                    enriched_items.append(item)
                except Exception as e:
                    logger.warning(f"Item enrichment failed: {e}")
            
            if enriched_items:
                self.cache_store.write_cache(media_type, enriched_items)
                elapsed = (time.time() - start_time) * 1000
                logger.info(f"Cache write: {len(enriched_items)} items ({elapsed:.1f}ms)")
        except Exception as e:
            logger.error(f"Cache write worker failed: {e}")

    def _build_embedding_text(self, item: Dict[str, Any], media_type: str) -> str:
        """Build text for embedding."""
        if media_type == "songs":
            return f"{item.get('title', '')} {item.get('artist_names', '')} {item.get('album_name', '')}"
        elif media_type == "movies":
            return f"{item.get('title', '')} {item.get('description', '')}"
        elif media_type == "books":
            authors = " ".join(item.get("authors", [])) if isinstance(item.get("authors"), list) else item.get("authors", "")
            return f"{item.get('title', '')} {authors} {item.get('description', '')}"
        elif media_type == "podcasts":
            return f"{item.get('title', '')} {item.get('publisher', '')} {item.get('description', '')}"
        return str(item)

    def _strip_embeddings(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove embeddings from results for API response."""
        cleaned_results = []
        for item in results:
            if not item:
                continue
            cleaned_item = {k: v for k, v in item.items() if k != "embedding"}
            cleaned_results.append(cleaned_item)
        return cleaned_results

    def search(self, media_type: str, query: str, language: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
        """Search always goes directly to provider for accuracy. Results are cached after response."""
        if media_type not in {"movies", "songs", "books", "podcasts"}:
            raise ValueError(f"Invalid media_type: {media_type}")

        limit = max(1, min(limit, 50))

        if language:
            language = language.strip().lower()
            if language not in {"hindi", "english", "neutral"}:
                language = None

        if not query or not query.strip():
            return {"results": [], "metrics": {"final_result_count": 0}}

        provider_results, provider_metrics = self._search_providers(
            media_type, query, language, limit
        )

        # Sort by rating DESC
        provider_results.sort(
            key=lambda x: float(x.get("rating") or x.get("vote_average") or 0),
            reverse=True
        )

        final_results = self._strip_embeddings(provider_results[:limit])

        logger.info(
            "Search completed: %s '%s' → %d results (source=provider)",
            media_type, query, len(final_results)
        )

        # Store all results to cache asynchronously so future searches benefit
        if provider_results:
            self._write_cache_async(media_type, provider_results)

        return {
            "results": final_results,
            "metrics": {
                "final_result_count": len(final_results),
                "provider_latency_ms": provider_metrics.provider_latency_ms,
            }
        }





