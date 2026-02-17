import logging
import os
from typing import List

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

    def _fetch_popular(self, pages: int = 3) -> List[dict]:
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

    def _fetch_top_rated(self, pages: int = 3) -> List[dict]:
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

    def fetch_candidates(self, limit: int) -> List[STANDARD_MEDIA_ITEM]:
        # Primary: popular movies (multiple pages)
        primary_raw = self._fetch_popular(pages=5)
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

        # Fallback: top rated movies if we don't reach 30 items
        if len(cleaned) < 30:
            fallback_raw = self._fetch_top_rated(pages=5)
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
            # Extend while avoiding duplicates by id
            existing_ids = {c["id"] for c in cleaned}
            for item in fallback_cleaned:
                if item["id"] not in existing_ids:
                    cleaned.append(item)
                    existing_ids.add(item["id"])

        if len(cleaned) < 10:
            raise RuntimeError(f"TMDbProvider returned insufficient candidates ({len(cleaned)})")

        return cleaned[:limit]


