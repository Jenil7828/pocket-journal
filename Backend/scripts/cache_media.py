''"""
Pocket Journal — Media Cache Refresh Script
Fetches, embeds, and caches popular/trending media across all providers.

Usage:
  python scripts/cache_media.py                    # Refresh all media types
  python scripts/cache_media.py movies             # Refresh specific type
  python scripts/cache_media.py --dry-run          # Test without writing
  python scripts/cache_media.py --force            # Force refresh even if fresh
"""

import argparse
import logging
import sys
import time
from collections import Counter
from typing import List, Dict, Any, Optional

import numpy as np

# Setup logging before imports
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger()

# Add parent directory to path for imports
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Also add /app for Docker compatibility
if os.path.exists("/app"):
    sys.path.insert(0, "/app")

from config_loader import get_config
from persistence.db_manager import DBManager
from services.media_recommender.cache_store import MediaCacheStore
from services.media_recommender.providers.tmdb_provider import TMDbProvider
from services.media_recommender.providers.spotify_provider import SpotifyProvider
from services.media_recommender.providers.books_provider import GoogleBooksProvider
from services.media_recommender.providers.podcast_provider import PodcastAPIProvider
from services.embeddings.embedding_service import EmbeddingService
from services.media.media_normalizer import normalize_media
from services.media.media_provider_enricher import enrich_from_providers, should_enrich
from utils.firestore_serializer import serialize_for_firestore, FirestoreSerializationError

_CFG = get_config()


class MediaCacheRefresher:
    """Orchestrates media fetching, embedding, and caching."""

    def __init__(self):
        self.db_manager = DBManager(firebase_json_path=None)
        self.db = self.db_manager.db
        self.cache_store = MediaCacheStore(self.db)
        self.embedding_service = EmbeddingService()
        
        self.providers = {
            "movies": TMDbProvider(),
            "songs": SpotifyProvider(),
            "books": GoogleBooksProvider(),
            "podcasts": PodcastAPIProvider(),
        }

    def get_language_buckets(self, media_type: str) -> List[Dict[str, Any]]:
        """
        Define language buckets for each media type.
        Songs and podcasts support hindi/english/neutral.
        Movies and books are neutral only.
        """
        if media_type in ("songs", "podcasts"):
            return [
                {
                    "language": "hindi",
                    "queries": (
                        ["hindi songs", "bollywood hits", "hindi film songs"]
                        if media_type == "songs"
                        else ["hindi podcast", "bollywood podcast", "hindi audio"]
                    ),
                    "market": "IN",
                },
                {
                    "language": "english",
                    "queries": (
                        ["english pop hits", "top english songs", "top 40", "english music"]
                        if media_type == "songs"
                        else ["popular podcast", "top podcast", "english podcast"]
                    ),
                    "market": "US",
                },
                {
                    "language": "neutral",
                    "queries": (
                        ["top hits", "popular songs", "trending music"]
                        if media_type == "songs"
                        else ["top podcast episodes", "trending podcast"]
                    ),
                    "market": None,
                },
            ]
        else:
            # Movies and books: neutral only
            return [
                {"language": "neutral", "queries": None, "market": None}
            ]

    def fetch_candidates_for_bucket(
        self, provider, media_type: str, bucket: Dict[str, Any], limit_per_bucket: int
    ) -> List[Dict[str, Any]]:
        """Fetch candidates for a specific language bucket."""
        language = bucket["language"]
        queries = bucket["queries"]
        market = bucket["market"]
        candidates: List[Dict[str, Any]] = []
        seen_ids = set()

        try:
            requested_queries = queries or [None]
            per_query_limit = max(1, limit_per_bucket // len(requested_queries))
            base_filters: Dict[str, Any] = {}
            if media_type in ("songs", "podcasts") and language != "neutral":
                base_filters["language"] = language
            if market:
                base_filters["market"] = market

            for query in requested_queries:
                items = provider.fetch_candidates(
                    query=query,
                    filters=base_filters or None,
                    limit=per_query_limit,
                )
                for item in items:
                    item_id = str(item.get("id", "")).strip()
                    if not item_id or item_id in seen_ids:
                        continue
                    seen_ids.add(item_id)
                    metadata = item.get("metadata") or {}

                    if media_type == "movies":
                        candidates.append({
                            "id": item_id,
                            "title": item.get("title", ""),
                            "description": item.get("description", ""),
                            "poster_url": item.get("poster_url") or metadata.get("poster_url", ""),
                            "rating": float(
                                item.get("vote_average")
                                or item.get("rating")
                                or metadata.get("vote_average")
                                or metadata.get("rating")
                                or 0
                            ),
                            "release_date": item.get("release_date") or metadata.get("release_date", ""),
                            "popularity": float(item.get("popularity") or metadata.get("popularity") or 0),
                            "duration_ms": item.get("duration_ms") or metadata.get("duration_ms", 0),
                            "language": language,
                        })
                    elif media_type == "books":
                        candidates.append({
                            "id": item_id,
                            "title": item.get("title", ""),
                            "description": item.get("description", ""),
                            "authors": item.get("authors") or metadata.get("authors", []),
                            "thumbnail_url": item.get("thumbnail_url") or metadata.get("thumbnail_url", ""),
                            "published_date": (
                                item.get("publishedDate")
                                or item.get("published_date")
                                or metadata.get("publishedDate")
                                or metadata.get("published_date", "")
                            ),
                            "page_count": (
                                item.get("pageCount")
                                or item.get("page_count")
                                or metadata.get("pageCount")
                                or metadata.get("page_count", 0)
                            ),
                            "info_link": (
                                item.get("infoLink")
                                or item.get("info_link")
                                or metadata.get("infoLink")
                                or metadata.get("info_link", "")
                            ),
                            "language": language,
                        })
                    elif media_type == "songs":
                        album = item.get("album") or metadata.get("album") or {}
                        candidates.append({
                            "id": item_id,
                            "title": item.get("title", ""),
                            "description": item.get("description", ""),
                            "artist_names": item.get("artist_names") or metadata.get("artist_names", ""),
                            "album_name": album.get("name", "") if isinstance(album, dict) else item.get("album_name", ""),
                            "album_image_url": item.get("album_image_url") or metadata.get("album_image_url", ""),
                            "external_url": item.get("external_url") or metadata.get("external_url", ""),
                            "duration_ms": item.get("duration_ms") or metadata.get("duration_ms", 0),
                            "popularity": item.get("popularity") or metadata.get("popularity", 0),
                            "language": language,
                        })
                    elif media_type == "podcasts":
                        candidates.append({
                            "id": item_id,
                            "title": item.get("title", ""),
                            "description": item.get("description", ""),
                            "publisher": item.get("publisher") or metadata.get("publisher", ""),
                            "show_image_url": item.get("show_image_url") or metadata.get("show_image_url", ""),
                            "external_url": item.get("external_url") or metadata.get("external_url", ""),
                            "duration_ms": item.get("duration_ms") or metadata.get("duration_ms", 0),
                            "release_date": item.get("release_date") or metadata.get("release_date", ""),
                            "language": language,
                        })
        
        except Exception as e:
            logger.error(f"Error fetching {media_type} candidates for {language}: {e}")

        logger.info(
            f"[SRV][cache_media] fetched media_type={media_type} language={language} count={len(candidates)}"
        )
        return candidates

    def refresh_media_type(
        self, media_type: str, force: bool = False, dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Refresh cache for a single media type.
        Returns stats dict with items_fetched, items_embedded, items_written, duration_ms.
        """
        media_type = media_type.lower().strip()
        if media_type not in self.providers:
            raise ValueError(f"Unknown media_type: {media_type}")

        refresh_start = time.time()
        
        # Check if cache is fresh
        if not force and self.cache_store.is_cache_fresh(media_type):
            logger.info(f"[SRV][cache_media] cache_fresh media_type={media_type}")
            return {
                "media_type": media_type,
                "status": "skipped",
                "reason": "cache_fresh",
                "duration_ms": int((time.time() - refresh_start) * 1000),
            }

        try:
            provider = self.providers[media_type]
            buckets = self.get_language_buckets(media_type)
            
            # Determine fetch limit per bucket
            total_fetch_limit = int(_CFG["cache"].get("fetch_limit_per_type", 500))
            limit_per_bucket = max(100, total_fetch_limit // len(buckets))

            # Fetch all candidates across all buckets
            all_candidates = []
            for bucket in buckets:
                bucket_candidates = self.fetch_candidates_for_bucket(
                    provider, media_type, bucket, limit_per_bucket
                )
                all_candidates.extend(bucket_candidates)

            items_fetched = len(all_candidates)
            logger.info(
                f"[SRV][cache_media] fetched media_type={media_type} total_items={items_fetched}"
            )

            if not all_candidates:
                logger.warning(f"[SRV][cache_media] no_candidates media_type={media_type}")
                return {
                    "media_type": media_type,
                    "status": "completed",
                    "items_fetched": 0,
                    "items_embedded": 0,
                    "items_written": 0,
                    "duration_ms": int((time.time() - refresh_start) * 1000),
                }

            existing_ids = self.cache_store.get_existing_ids(media_type)
            new_candidates = [
                item for item in all_candidates
                if str(item.get("id", "")).strip() and str(item.get("id", "")).strip() not in existing_ids
            ]
            skipped_existing = items_fetched - len(new_candidates)
            logger.info(
                f"[SRV][cache_media] dedupe_against_db media_type={media_type} existing={len(existing_ids)} fetched={items_fetched} new={len(new_candidates)} skipped={skipped_existing}"
            )

            if not new_candidates:
                return {
                    "media_type": media_type,
                    "status": "completed",
                    "items_fetched": items_fetched,
                    "items_embedded": 0,
                    "items_written": 0,
                    "items_skipped_existing": skipped_existing,
                    "duration_ms": int((time.time() - refresh_start) * 1000),
                }

            # Extract text for embedding
            texts_to_embed = [
                f"{item.get('title', '')} {item.get('description', '')}".strip()
                for item in new_candidates
            ]

            # Batch embed
            embed_start = time.time()
            embeddings = self.embedding_service.embed_texts(texts_to_embed)
            embed_duration_ms = int((time.time() - embed_start) * 1000)

            if not embeddings or len(embeddings) != len(new_candidates):
                logger.error(f"[ERR][cache_media] embedding_count_mismatch expected={len(new_candidates)} got={len(embeddings or [])}")
                return {
                    "media_type": media_type,
                    "status": "failed",
                    "reason": "embedding_count_mismatch",
                    "duration_ms": int((time.time() - refresh_start) * 1000),
                }

            # Add embeddings to candidates, enrich, and normalize
            normalized_candidates = []
            for item, emb in zip(new_candidates, embeddings):
                item["embedding"] = emb
                
                # Step 1: Enrich from providers if missing critical fields
                if should_enrich(item, media_type):
                    logger.debug(f"Enriching new {media_type} item: {item.get('id')}")
                    item = enrich_from_providers(item, media_type)
                
                # Step 2: Normalize the media before writing (CRITICAL: ensures schema consistency)
                normalized_item = normalize_media(item, media_type)
                normalized_candidates.append(normalized_item)

            items_embedded = len(embeddings)

            # Write to cache
            if not dry_run:
                write_start = time.time()
                self.cache_store.write_cache(media_type, normalized_candidates)
                write_duration_ms = int((time.time() - write_start) * 1000)
                logger.info(
                    f"[SRV][cache_media] written media_type={media_type} items={items_embedded} duration_ms={write_duration_ms}"
                )
            else:
                logger.info(
                    f"[SRV][cache_media] dry_run media_type={media_type} items={items_embedded}"
                )

            items_written = items_embedded if not dry_run else 0
            duration_ms = int((time.time() - refresh_start) * 1000)

            # Count by language
            lang_counts = Counter(item.get("language", "neutral") for item in new_candidates)

            return {
                "media_type": media_type,
                "status": "completed",
                "items_fetched": items_fetched,
                "items_embedded": items_embedded,
                "items_written": items_written,
                "items_skipped_existing": skipped_existing,
                "language_distribution": dict(lang_counts),
                "embed_duration_ms": embed_duration_ms,
                "total_duration_ms": duration_ms,
                "dry_run": dry_run,
            }

        except Exception as e:
            logger.error(f"[ERR][cache_media] refresh_failed media_type={media_type} error={str(e)}")
            return {
                "media_type": media_type,
                "status": "failed",
                "error": str(e),
                "duration_ms": int((time.time() - refresh_start) * 1000),
            }

    def refresh_all(self, force: bool = False, dry_run: bool = False) -> Dict[str, Any]:
        """Refresh cache for all media types."""
        results = {}
        total_start = time.time()

        for media_type in ["movies", "songs", "books", "podcasts"]:
            results[media_type] = self.refresh_media_type(media_type, force=force, dry_run=dry_run)

        return {
            "status": "completed",
            "results": results,
            "total_duration_ms": int((time.time() - total_start) * 1000),
        }

    def _sanitize_item_for_firestore(self, item: Dict[str, Any], media_type: str, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Sanitize a single item for Firestore writing.
        Converts numpy arrays to lists and validates all types.
        
        Args:
            item: Item to sanitize
            media_type: Type of media (for logging)
            item_id: Item ID (for error context)
            
        Returns:
            Sanitized item, or None if sanitization fails
        """
        try:
            sanitized = serialize_for_firestore(item, path=f"{media_type}/{item_id}")
            return sanitized
        except FirestoreSerializationError as e:
            logger.error(
                f"[ERR][cache_media] sanitization_failed media_type={media_type} item_id={item_id} error={str(e)}"
            )
            return None

    def _sanitize_batch(self, items: List[Dict[str, Any]], media_type: str) -> tuple:
        """
        Sanitize a batch of items for Firestore.
        Skips bad records instead of crashing entire batch.
        
        Args:
            items: List of items to sanitize
            media_type: Type of media (for logging)
            
        Returns:
            Tuple of (sanitized_items, failed_count, skipped_ids)
        """
        sanitized_items = []
        failed_count = 0
        skipped_ids = []
        
        for item in items:
            item_id = item.get("id", "unknown")
            sanitized = self._sanitize_item_for_firestore(item, media_type, item_id)
            
            if sanitized is None:
                failed_count += 1
                skipped_ids.append(item_id)
                logger.warning(
                    f"[SRV][cache_media] skipping_bad_record media_type={media_type} item_id={item_id}"
                )
            else:
                sanitized_items.append(sanitized)
        
        if failed_count > 0:
            logger.warning(
                f"[SRV][cache_media] batch_sanitization_summary media_type={media_type} total={len(items)} sanitized={len(sanitized_items)} failed={failed_count}"
            )
        
        return sanitized_items, failed_count, skipped_ids

    
def refresh_cache(media_type: str, force: bool = False, dry_run: bool = False) -> Dict[str, Any]:
    """
    Public function for refresh_cache() — called by job endpoint.
    Refreshes a single media type cache.
    """
    logger.info(f"[SRV][cache_media] refresh_cache_starting media_type={media_type} force={force} dry_run={dry_run}")
    refresher = MediaCacheRefresher()
    result = refresher.refresh_media_type(media_type, force=force, dry_run=dry_run)
    logger.info(f"[SRV][cache_media] refresh_cache_completed status={result.get('status')}")
    return result


def refresh_all(force: bool = False, dry_run: bool = False) -> Dict[str, Any]:
    """
    Public function for refresh_all() — called by job endpoint.
    Refreshes all media type caches.
    """
    logger.info(f"[SRV][cache_media] refresh_all_starting force={force} dry_run={dry_run}")
    refresher = MediaCacheRefresher()
    result = refresher.refresh_all(force=force, dry_run=dry_run)
    logger.info(f"[SRV][cache_media] refresh_all_completed")
    return result


def main():
    """CLI interface for manual cache refresh."""
    parser = argparse.ArgumentParser(
        description="Refresh Pocket Journal media cache",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/cache_media.py                       # Refresh all media types
  python scripts/cache_media.py songs                 # Refresh specific type
  python scripts/cache_media.py --dry-run             # Test without writing
  python scripts/cache_media.py songs --force         # Force refresh
        """,
    )
    
    parser.add_argument(
        "media_type",
        nargs="?",
        default=None,
        help="Media type to refresh (movies|songs|books|podcasts). If not provided, refreshes all.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and embed but do not write to Firestore",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force refresh even if cache is fresh",
    )

    args = parser.parse_args()

    try:
        if args.media_type:
            result = refresh_cache(args.media_type, force=args.force, dry_run=args.dry_run)
            print(f"Result: {result}")
        else:
            result = refresh_all(force=args.force, dry_run=args.dry_run)
            print(f"Result: {result}")
    except Exception as e:
        logger.exception(f"CLI failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()







