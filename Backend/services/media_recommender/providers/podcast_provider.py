import logging
import os
from typing import List

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

    def fetch_candidates(self, limit: int) -> List[STANDARD_MEDIA_ITEM]:
        primary_raw = self._fetch_best_podcasts(pages=5)
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

        if len(cleaned) < 30:
            fallback_raw = self._fetch_curated(pages=5)
            fallback = []
            for p in fallback_raw:
                fallback.append(
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

            fallback_cleaned = self._clean_items(fallback)
            logger.info("PodcastAPIProvider fallback cleaned=%d", len(fallback_cleaned))
            existing_ids = {c["id"] for c in cleaned}
            for item in fallback_cleaned:
                if item["id"] not in existing_ids:
                    cleaned.append(item)
                    existing_ids.add(item["id"])

        if len(cleaned) < 10:
            raise RuntimeError(
                f"PodcastAPIProvider returned insufficient candidates ({len(cleaned)})"
            )

        return cleaned[:limit]


