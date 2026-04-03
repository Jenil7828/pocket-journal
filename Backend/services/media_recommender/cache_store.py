from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from firebase_admin import firestore

from config_loader import get_config
from utils.firestore_serializer import serialize_for_firestore, FirestoreSerializationError

# Clean root logger - no module prefix
logger = logging.getLogger()


_CFG = get_config()
_MAX_AGE_HOURS: int = int(_CFG["cache"]["max_age_hours"])
_BATCH_SIZE: int = int(_CFG["cache"]["batch_size"])
_EMBEDDING_BATCH_SIZE: int = 10  # Conservative size for embedding-heavy writes (each item ~4KB)
_SCHEMA_VERSION: str = str(_CFG["cache"]["schema_version"])


class MediaCacheStore:
    """
    Handles all Firestore cache reads and writes.
    Pure data layer — no recommendation/ranking business logic.
    """

    def __init__(self, db):
        self.db = db

    def collection_name(self, media_type: str) -> str:
        # "songs" -> "media_cache_songs"
        return f"media_cache_{media_type}"

    def read_cache(self, media_type: str, language: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Read all cached items for a media type, optionally filtered by language.

        For language-filtered reads:
        - If language="hindi": WHERE language == "hindi" OR language == "neutral"
        - If language="english": WHERE language == "english" OR language == "neutral"
        - If language=None: all items

        Returns list of dicts with all fields including embedding as List[float].
        Skips _metadata document automatically.

        Implementation note: Firestore does not support OR queries directly.
        Run two separate queries (one for the specific language, one for "neutral")
        and merge results in Python. Deduplicate by id.
        """

        col_ref = self.db.collection(self.collection_name(media_type))

        def _stream_query(query) -> Dict[str, Dict[str, Any]]:
            out: Dict[str, Dict[str, Any]] = {}
            for doc in query.stream():
                if getattr(doc, "id", None) == "_metadata":
                    continue
                data = doc.to_dict() or {}
                doc_id = str(getattr(doc, "id", ""))
                # Ensure id is present for downstream logic that expects it.
                if doc_id and "id" not in data:
                    data["id"] = doc_id
                out[doc_id] = data
            return out

        if language is None:
            query = col_ref
            merged = _stream_query(query)
            return list(merged.values())

        normalized = (language or "").strip().lower()
        if normalized not in {"hindi", "english"}:
            # For any other language filter, treat as "neutral only".
            query = col_ref.where("language", "==", "neutral")
            merged = _stream_query(query)
            return list(merged.values())

        # Firestore does not support OR queries directly.
        query_lang = col_ref.where("language", "==", normalized)
        query_neutral = col_ref.where("language", "==", "neutral")

        items_lang = _stream_query(query_lang)
        items_neutral = _stream_query(query_neutral)

        items_lang.update(items_neutral)  # neutral is already deduped by doc id
        return list(items_lang.values())

    def get_existing_ids(self, media_type: str) -> set[str]:
        """Return cached document ids for a media type, excluding metadata."""
        col_ref = self.db.collection(self.collection_name(media_type))
        out: set[str] = set()
        for doc in col_ref.stream():
            doc_id = str(getattr(doc, "id", ""))
            if doc_id and doc_id != "_metadata":
                out.add(doc_id)
        return out

    def write_cache(self, media_type: str, items: List[Dict[str, Any]]) -> None:
        """
        Batch write items to cache collection.

        Each item must have: id, title, description, embedding, language.
        
        IMPORTANT: All items are sanitized for Firestore compatibility:
        - numpy.ndarray → list
        - numpy scalars → Python scalars
        - Nested structures are validated

        Items with embeddings are written individually to avoid Firestore's 10MB
        transaction size limit. Items without embeddings use batch writes in chunks
        of _BATCH_SIZE (currently 400).

        Overwrites existing docs by id (idempotent).
        Writes _metadata doc after all items committed.
        
        Raises:
            FirestoreSerializationError: If items contain unsupported types after sanitization
        """

        if not items:
            # Still write metadata so freshness check isn't stuck on older content.
            meta_ref = self.db.collection(self.collection_name(media_type)).document("_metadata")
            meta_ref.set(
                {
                    "last_refreshed": firestore.SERVER_TIMESTAMP,
                    "item_count": 0,
                    "item_count_by_language": {},
                    "schema_version": _SCHEMA_VERSION,
                }
            )
            return

        # Sanitize all items for Firestore compatibility
        sanitized_items = []
        failed_items = []
        
        for idx, item in enumerate(items):
            item_id = str(item.get("id", f"item_{idx}"))
            try:
                sanitized = serialize_for_firestore(
                    item, 
                    path=f"{media_type}/{item_id}"
                )
                sanitized_items.append(sanitized)
            except FirestoreSerializationError as e:
                logger.error(
                    "[DB][cache_store] sanitization_failed media_type=%s item_id=%s error=%s",
                    media_type, item_id, str(e)
                )
                failed_items.append(item_id)
        
        if failed_items:
            logger.warning(
                "[DB][cache_store] skipping_items media_type=%s total=%d sanitized=%d failed=%d",
                media_type, len(items), len(sanitized_items), len(failed_items)
            )
        
        if not sanitized_items:
            logger.error(
                "[DB][cache_store] all_items_failed media_type=%s",
                media_type
            )
            return

        collection_ref = self.db.collection(self.collection_name(media_type))
        existing_ids = self.get_existing_ids(media_type)
        existing_stats = self.get_cache_stats(media_type)
        added_at = datetime.now(timezone.utc)
        new_items = []
        for item in sanitized_items:
            if str(item.get("id")) in existing_ids:
                continue
            stamped = dict(item)
            stamped.setdefault("added_at", added_at)
            new_items.append(stamped)

        # Check if any items contain embeddings
        has_embeddings = any("embedding" in item for item in new_items)

        logger.info(
            "[DB][cache_store] writing_new media_type=%s requested=%d new=%d has_embeddings=%s",
            media_type,
            len(sanitized_items),
            len(new_items),
            has_embeddings,
        )

        if not new_items:
            meta_ref = collection_ref.document("_metadata")
            meta_ref.set(
                {
                    "last_refreshed": firestore.SERVER_TIMESTAMP,
                    "item_count": len(existing_ids),
                    "item_count_by_language": existing_stats.get("item_count_by_language") or {},
                    "schema_version": _SCHEMA_VERSION,
                },
                merge=True,
            )
            return

        logger.info(
            "[DB][cache_store] writing_items count=%d media_type=%s has_embeddings=%s failed_count=%d",
            len(new_items),
            self.collection_name(media_type),
            has_embeddings,
            len(failed_items),
        )

        if has_embeddings:
            # Individual writes to avoid transaction size limit
            for item in new_items:
                item_id = str(item["id"])
                ref = collection_ref.document(item_id)
                ref.set(item)  # individual set, not batched
        else:
            # Batch writes for small items without embeddings
            for i in range(0, len(new_items), _BATCH_SIZE):
                batch = self.db.batch()
                chunk = new_items[i : i + _BATCH_SIZE]
                for item in chunk:
                    ref = collection_ref.document(str(item["id"]))
                    batch.set(ref, item)
                batch.commit()

        # Write metadata after all items
        meta_ref = collection_ref.document("_metadata")
        lang_counts = Counter(existing_stats.get("item_count_by_language") or {})
        lang_counts.update(Counter(i.get("language", "neutral") for i in new_items))
        meta_ref.set(
            {
                "last_refreshed": firestore.SERVER_TIMESTAMP,
                "item_count": len(existing_ids) + len(new_items),
                "item_count_by_language": dict(lang_counts),
                "schema_version": _SCHEMA_VERSION,
            }
        )

    def is_cache_fresh(self, media_type: str, max_age_hours: int = _MAX_AGE_HOURS) -> bool:
        """
        Read _metadata.last_refreshed for the collection.
        Return True if (now - last_refreshed) < max_age_hours.
        Return False if _metadata doc doesn't exist.

        max_age_hours configurable via MEDIA_CACHE_MAX_AGE_HOURS env var.
        """

        meta_ref = self.db.collection(self.collection_name(media_type)).document("_metadata")
        meta_doc = meta_ref.get()
        if not getattr(meta_doc, "exists", False):
            return False

        meta = meta_doc.to_dict() or {}
        last_refreshed = meta.get("last_refreshed")
        if last_refreshed is None:
            return False

        if getattr(last_refreshed, "tzinfo", None) is None:
            last_refreshed = last_refreshed.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        age_hours = (now - last_refreshed).total_seconds() / 3600.0
        return age_hours < max_age_hours

    def get_cache_stats(self, media_type: str) -> Dict[str, Any]:
        """
        Return {item_count, last_refreshed, age_hours, is_fresh, item_count_by_language}.
        Used for health checks and monitoring.
        """

        meta_ref = self.db.collection(self.collection_name(media_type)).document("_metadata")
        meta_doc = meta_ref.get()
        if not getattr(meta_doc, "exists", False):
            return {
                "item_count": 0,
                "last_refreshed": None,
                "age_hours": None,
                "is_fresh": False,
                "item_count_by_language": {},
            }

        meta = meta_doc.to_dict() or {}
        last_refreshed = meta.get("last_refreshed")
        if last_refreshed is None:
            return {
                "item_count": int(meta.get("item_count", 0) or 0),
                "last_refreshed": None,
                "age_hours": None,
                "is_fresh": False,
                "item_count_by_language": meta.get("item_count_by_language") or {},
            }

        if getattr(last_refreshed, "tzinfo", None) is None:
            last_refreshed = last_refreshed.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        age_hours = (now - last_refreshed).total_seconds() / 3600.0

        return {
            "item_count": int(meta.get("item_count", 0) or 0),
            "last_refreshed": last_refreshed,
            "age_hours": age_hours,
            "is_fresh": self.is_cache_fresh(media_type),
            "item_count_by_language": meta.get("item_count_by_language") or {},
        }

