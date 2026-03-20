import argparse
import logging
import os
import sys
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

# Ensure Backend/ is on sys.path when running as `python scripts/cache_media.py ...`
_HERE = os.path.dirname(__file__)
_BACKEND_DIR = os.path.abspath(os.path.join(_HERE, ".."))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

load_dotenv()

from config_loader import get_config
_CFG = get_config()

logging.basicConfig(
    level=_CFG["logging"]["app_level"].upper(),
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("pocket_journal.cache_media")

from services.embedding_service import get_embedding_service
from services.media_recommender.cache_store import MediaCacheStore

# Import recommendation contract for provider access.
# NOTE: In this repo snapshot, `recommendation.py` may not yet contain `_get_provider`.
# We therefore keep import safe and only fail when actually attempting to fetch candidates.
try:
    from services.media_recommender import recommendation as _recommendation_mod
except Exception:  # pragma: no cover
    _recommendation_mod = None


def _get_provider_for(media_type: str):
    if _recommendation_mod is None:
        raise ImportError("Failed to import services.media_recommender.recommendation")
    if not hasattr(_recommendation_mod, "_get_provider"):
        raise AttributeError("services.media_recommender.recommendation has no _get_provider")
    return _recommendation_mod._get_provider(media_type)


def _dedupe_by_id(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set[str] = set()
    out: List[Dict[str, Any]] = []
    for item in items:
        item_id = item.get("id")
        if item_id is None:
            continue
        item_id_s = str(item_id)
        if item_id_s in seen:
            continue
        seen.add(item_id_s)
        # Normalize id to string for stable Firestore doc IDs.
        item["id"] = item_id_s
        out.append(item)
    return out


def _embed_items(embedder, items: List[Dict[str, Any]]) -> Tuple[int, int]:
    """
    Batch embed items using a single embed_texts call.

    Returns: (embedded_count, requested_count)
    """

    if not items:
        return 0, 0

    # Phase 3 cache schema includes `description` for all media types.
    # Use description as the semantic text for embedding.
    texts: List[str] = []
    for it in items:
        desc = it.get("description")
        if isinstance(desc, str) and desc.strip():
            texts.append(desc)
        else:
            # Fallback to title if description is missing/empty.
            title = it.get("title") or ""
            texts.append(title)

    embeddings = embedder.embed_texts(texts)
    if len(embeddings) != len(items):
        raise RuntimeError(
            f"Embedding count mismatch: items={len(items)} embeddings={len(embeddings)}"
        )

    for it, vec in zip(items, embeddings):
        # embedding_service returns normalized numpy float32 vectors.
        it["embedding"] = vec.tolist() if hasattr(vec, "tolist") else list(vec)

    return len(items), len(texts)


def _get_media_types_from_config(cfg: Dict[str, Any]) -> List[str]:
    return list(cfg["cache"]["supported_media_types"])


def refresh_cache(
    media_type: Optional[str] = None,
    *,
    dry_run: bool = False,
    force: bool = False,
) -> None:
    """
    Refresh one media_type or all media types (when media_type is None).

    Standalone-friendly: no Flask context required.
    """

    cfg = get_config()
    cache_cfg = cfg["cache"]
    language_buckets = cache_cfg["language_buckets"]
    supported_media_types = _get_media_types_from_config(cfg)

    media_types = [media_type] if media_type else supported_media_types
    fetch_limit_total = int(cache_cfg["fetch_limit"])

    cache_store: Optional[MediaCacheStore] = None
    if not dry_run:
        # Initialize Firestore only when we might write.
        from persistence.db_manager import DBManager

        db_manager = DBManager()
        cache_store = MediaCacheStore(db_manager.db)

    for mt in media_types:
        start = time.time()
        try:
            buckets = language_buckets.get(mt) or []
            if not buckets:
                logger.warning("No language buckets configured for media_type=%s", mt)
                continue

            if cache_store is not None and not force and cache_store.is_cache_fresh(mt):
                logger.info("Cache fresh — skipping media_type=%s", mt)
                continue

            # Per-bucket limit so the overall number of fetched candidates
            # stays within CACHE_FETCH_LIMIT.
            per_bucket_limit = fetch_limit_total // len(buckets)

            provider = _get_provider_for(mt)

            merged: List[Dict[str, Any]] = []
            for bucket in buckets:
                lang = bucket.get("language")
                queries = bucket.get("queries")
                query = None
                if isinstance(queries, list) and queries:
                    query = queries[0]

                # Phase 3 spec: filters only by language.
                filters = {"language": lang}

                t0 = time.time()
                items = provider.fetch_candidates(query=query, filters=filters, limit=per_bucket_limit)
                fetched_count = len(items) if isinstance(items, list) else 0
                logger.info(
                    "Fetched media_type=%s language=%s bucket_items=%d duration_s=%.3f",
                    mt,
                    lang,
                    fetched_count,
                    time.time() - t0,
                )

                # Assign language field prior to embedding.
                if isinstance(items, list):
                    for it in items:
                        it["language"] = lang
                    merged.extend(items)

            deduped = _dedupe_by_id(merged)
            total_after_dedup = len(deduped)

            if total_after_dedup > 0:
                embedder = get_embedding_service()
                embedded_count, requested_count = _embed_items(embedder, deduped)
            else:
                embedded_count, requested_count = 0, 0

            cached_at = datetime.now(timezone.utc)
            for it in deduped:
                it["cached_at"] = cached_at

            if not dry_run and cache_store is not None:
                cache_store.write_cache(mt, deduped)
                written_count = total_after_dedup
            else:
                written_count = 0

            logger.info(
                "Cache refresh complete: media_type=%s fetched=%d deduped=%d embedded=%d written=%d duration_s=%.3f",
                mt,
                len(merged),
                total_after_dedup,
                embedded_count,
                written_count,
                time.time() - start,
            )
        except Exception:
            logger.exception("Cache refresh failed for media_type=%s", mt)
            # Per spec: partial cache is better than none. Continue others.
            continue


def refresh_all(*, dry_run: bool = False, force: bool = False) -> None:
    refresh_cache(None, dry_run=dry_run, force=force)


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    cfg = get_config()
    supported = set(cfg["cache"]["supported_media_types"])

    parser = argparse.ArgumentParser(description="Refresh media caches in Firestore.")
    parser.add_argument(
        "--media-type",
        dest="media_type",
        choices=sorted(supported),
        default=None,
        help="Refresh one media type only",
    )
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", help="Fetch+embed but do not write to Firestore")
    parser.add_argument("--force", dest="force", action="store_true", help="Skip freshness check and refresh even if cache is fresh")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = _parse_args(argv)

    refresh_cache(
        args.media_type,
        dry_run=bool(args.dry_run),
        force=bool(args.force),
    )


if __name__ == "__main__":
    main()

