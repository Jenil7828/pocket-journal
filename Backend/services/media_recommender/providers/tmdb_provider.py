import logging
import os
from typing import List, Optional, Dict, Any

from .base_provider import BaseHTTPProvider, STANDARD_MEDIA_ITEM

logger = logging.getLogger("pocket_journal.media.providers.tmdb")


class TMDbProvider(BaseHTTPProvider):
    """Movie provider backed by TMDb.

    Uses popular and top_rated endpoints with no mood/genre filtering.
    """

    def __init__(self) -> None:
        api_key = os.getenv("TMDB_API_KEY")
        if not api_key:
            raise RuntimeError("TMDB_API_KEY environment variable is required for TMDbProvider")
        self.api_key = api_key

    def _fetch_popular(self, pages: int = 1) -> List[dict]:
        items: List[dict] = []
        for page in range(1, pages + 1):
            payload = self._request(
                "GET",
                "https://api.themoviedb.org/3/movie/popular",
                params={
                    "api_key": self.api_key,
                    "language": "en-US",
                    "page": page,
                },
            )
            if not payload:
                continue
            items.extend(payload.get("results", []))
        return items

    def _fetch_top_rated(self, pages: int = 1) -> List[dict]:
        items: List[dict] = []
        for page in range(1, pages + 1):
            payload = self._request(
                "GET",
                "https://api.themoviedb.org/3/movie/top_rated",
                params={
                    "api_key": self.api_key,
                    "language": "en-US",
                    "page": page,
                },
            )
            if not payload:
                continue
            items.extend(payload.get("results", []))
        return items

    def fetch_candidates(self, query: Optional[str], filters: Optional[Dict[str, Any]], limit: int) -> List[STANDARD_MEDIA_ITEM]:
        # Determine number of pages to fetch (TMDb usually returns ~20 results per page)
        try:
            pages = max(1, min(5, (int(limit) + 19) // 20))
        except Exception:
            pages = 1

        primary_raw = self._fetch_popular(pages=pages)
        primary = []
        for m in primary_raw:
            primary.append(
                {
                    "id": m.get("id"),
                    "title": m.get("title") or m.get("original_title") or "",
                    "description": m.get("overview") or "",
                    "vote_average": m.get("vote_average"),
                    "release_date": m.get("release_date"),
                    "popularity": m.get("popularity"),
                }
            )

        cleaned = self._clean_items(primary)
        logger.info("TMDbProvider primary cleaned=%d", len(cleaned))

        # If insufficient, fetch top-rated as fallback (limited pages)
        if len(cleaned) < max(10, limit // 2):
            fallback_raw = self._fetch_top_rated(pages=pages)
            fallback = []
            for m in fallback_raw:
                fallback.append(
                    {
                        "id": m.get("id"),
                        "title": m.get("title") or m.get("original_title") or "",
                        "description": m.get("overview") or "",
                        "vote_average": m.get("vote_average"),
                        "release_date": m.get("release_date"),
                        "popularity": m.get("popularity"),
                    }
                )
            fallback_cleaned = self._clean_items(fallback)
            logger.info("TMDbProvider fallback cleaned=%d", len(fallback_cleaned))
            existing_ids = {c["id"] for c in cleaned}
            for item in fallback_cleaned:
                if item["id"] not in existing_ids:
                    cleaned.append(item)
                    existing_ids.add(item["id"])

        if len(cleaned) < 10:
            logger.warning("Low TMDb candidate pool: %d", len(cleaned))

        return cleaned[:limit]

