import logging
import os
from typing import List, Optional, Dict, Any

from .base_provider import BaseHTTPProvider, STANDARD_MEDIA_ITEM
from config_loader import get_config
_API = get_config()["api"]

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
                _API["tmdb"]["popular_endpoint"],
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
                _API["tmdb"]["toprated_endpoint"],
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

    def _fetch_movie_details(self, movie_id: int) -> Optional[dict]:
        """Fetch movie details (including runtime and poster_path) from TMDb details endpoint."""
        try:
            payload = self._request(
                "GET",
                f'{_API["tmdb"]["details_endpoint"]}/{movie_id}',
                params={
                    "api_key": self.api_key,
                    "language": "en-US",
                },
            )
            return payload or None
        except Exception:
            return None

    def fetch_candidates(self, query: Optional[str], filters: Optional[Dict[str, Any]], limit: int) -> List[STANDARD_MEDIA_ITEM]:
        # Determine number of pages to fetch (TMDb usually returns ~20 results per page)
        try:
            pages = max(1, min(int(_API["tmdb"]["max_pages"]), (int(limit) + int(_API["tmdb"]["results_per_page"]) - 1) // int(_API["tmdb"]["results_per_page"])))
        except Exception:
            pages = 1

        primary_raw = self._fetch_popular(pages=pages)
        primary = []
        for m in primary_raw:
            # try to enrich with details (runtime, poster_path) from movie details endpoint
            movie_id = m.get("id")
            runtime = None
            poster_path = m.get("poster_path")
            if movie_id:
                details = self._fetch_movie_details(movie_id)
                if details:
                    # runtime in minutes
                    try:
                        runtime = details.get("runtime")
                    except Exception:
                        runtime = None
                    # prefer detailed poster_path if present
                    poster_path = poster_path or details.get("poster_path")

            candidate = {
                "id": m.get("id"),
                "title": m.get("title") or m.get("original_title") or "",
                "description": m.get("overview") or "",
                # Preserve poster_path from TMDb raw response for formatting
                "poster_path": poster_path,
                "poster_url": f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None,
                "vote_average": m.get("vote_average"),
                "release_date": m.get("release_date"),
                "popularity": m.get("popularity"),
            }
            # include runtime and duration_ms if we found it
            if runtime is not None:
                candidate["runtime"] = runtime
                try:
                    candidate["duration_ms"] = int(float(runtime) * 60.0 * 1000.0)
                except Exception:
                    pass
            primary.append(candidate)

        cleaned = self._clean_items(primary)
        logger.info("TMDbProvider primary cleaned=%d", len(cleaned))

        # If insufficient, fetch top-rated as fallback (limited pages)
        if len(cleaned) < max(10, limit // 2):
            fallback_raw = self._fetch_top_rated(pages=pages)
            fallback = []
            for m in fallback_raw:
                movie_id = m.get("id")
                runtime = None
                poster_path = m.get("poster_path")
                if movie_id:
                    details = self._fetch_movie_details(movie_id)
                    if details:
                        runtime = details.get("runtime")
                        poster_path = poster_path or details.get("poster_path")

                cand = {
                    "id": m.get("id"),
                    "title": m.get("title") or m.get("original_title") or "",
                    "description": m.get("overview") or "",
                    "poster_path": poster_path,
                        "poster_url": f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None,
                    "vote_average": m.get("vote_average"),
                    "release_date": m.get("release_date"),
                    "popularity": m.get("popularity"),
                }
                if runtime is not None:
                    cand["runtime"] = runtime
                    try:
                        cand["duration_ms"] = int(float(runtime) * 60.0 * 1000.0)
                    except Exception:
                        pass
                fallback.append(cand)
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

