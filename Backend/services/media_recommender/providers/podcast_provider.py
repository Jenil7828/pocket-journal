import logging
import os
from typing import List, Optional, Dict, Any

from .base_provider import BaseHTTPProvider, STANDARD_MEDIA_ITEM

logger = logging.getLogger("pocket_journal.media.providers.podcasts")


class PodcastAPIProvider(BaseHTTPProvider):
    """Podcast provider backed by a generic podcast API (Listen Notes compatible).

    Uses 'best_podcasts' and 'curated_podcasts' endpoints with no mood/genre filtering.
    """

    base_url = "https://listen-api.listennotes.com/api/v2"

    def __init__(self) -> None:
        api_key = os.getenv("PODCAST_API_KEY") or os.getenv("LISTEN_NOTES_API_KEY")
        if not api_key:
            raise RuntimeError(
                "PODCAST_API_KEY or LISTEN_NOTES_API_KEY env var is required for PodcastAPIProvider"
            )
        self.api_key = api_key

    @property
    def _headers(self):
        return {"X-ListenAPI-Key": self.api_key}

    def _fetch_best_podcasts(self, pages: int = 3) -> List[dict]:
        items: List[dict] = []
        for page in range(1, pages + 1):
            payload = self._request(
                "GET",
                f"{self.base_url}/best_podcasts",
                headers=self._headers,
                params={
                    "page": page,
                    "safe_mode": 1,
                },
            )
            if not payload:
                continue
            items.extend(payload.get("podcasts", []) or [])
        return items

    def _fetch_curated(self, pages: int = 3) -> List[dict]:
        items: List[dict] = []
        for page in range(1, pages + 1):
            payload = self._request(
                "GET",
                f"{self.base_url}/curated_podcasts",
                headers=self._headers,
                params={
                    "page": page,
                    "safe_mode": 1,
                },
            )
            if not payload:
                continue
            for curated in payload.get("curated_lists", []) or []:
                items.extend(curated.get("podcasts", []) or [])
        return items

    def fetch_candidates(self, query: Optional[str] = None, filters: Optional[Dict[str, Any]] = None, limit: int = 100) -> List[STANDARD_MEDIA_ITEM]:
        # Determine pages needed (ListenNotes returns ~20-30 podcasts per page)
        try:
            pages = max(1, min(5, (int(limit) + 19) // 20))
        except Exception:
            pages = 1

        primary_raw = self._fetch_best_podcasts(pages=pages)
        primary = []
        for p in primary_raw:
            primary.append(
                {
                    "id": p.get("id") or p.get("rss") or p.get("listennotes_url"),
                    "title": p.get("title") or p.get("title_original") or "",
                    "description": p.get("description") or p.get("description_highlighted") or "",
                    "publisher": p.get("publisher"),
                    "language": p.get("language"),
                    "total_episodes": p.get("total_episodes"),
                    "listennotes_url": p.get("listennotes_url"),
                }
            )

        cleaned = self._clean_items(primary)
        logger.info("PodcastAPIProvider primary cleaned=%d", len(cleaned))

        if len(cleaned) < 10:
            logger.warning("Low Podcast candidate pool: %d", len(cleaned))

        return cleaned[:limit]

