import logging
import os
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from .base_provider import BaseHTTPProvider, STANDARD_MEDIA_ITEM
from config_loader import get_config
_API = get_config()["api"]

logger = logging.getLogger()


class TMDbProvider(BaseHTTPProvider):
    """Movie provider backed by TMDb.

    Uses popular and top_rated endpoints with no mood/genre filtering.
    """

    def __init__(self) -> None:
        try:
            api_key = os.environ["TMDB_API_KEY"]
        except KeyError:
            raise RuntimeError("TMDB_API_KEY environment variable is required for TMDbProvider")
        self.api_key = api_key

    def _fetch_endpoint(self, endpoint: str, pages: int = 1) -> List[dict]:
        items: List[dict] = []
        for page in range(1, pages + 1):
            payload = self._request(
                "GET",
                endpoint,
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

    def _fetch_popular(self, pages: int = 1) -> List[dict]:
        return self._fetch_endpoint(_API["tmdb"]["popular_endpoint"], pages=pages)

    def _fetch_top_rated(self, pages: int = 1) -> List[dict]:
        return self._fetch_endpoint(_API["tmdb"]["toprated_endpoint"], pages=pages)

    def _search_movies(self, query: str, pages: int = 3) -> List[dict]:
        """Search movies by title using TMDb search endpoint."""
        items: List[dict] = []
        for page in range(1, pages + 1):
            payload = self._request(
                "GET",
                "https://api.themoviedb.org/3/search/movie",
                params={
                    "api_key": self.api_key,
                    "language": "en-US",
                    "query": query,
                    "page": page,
                },
            )
            if not payload:
                break
            results = payload.get("results", [])
            if not results:
                break
            items.extend(results)
        return items

    def _fetch_now_playing(self, pages: int = 1) -> List[dict]:
        endpoint = _API["tmdb"].get("now_playing_endpoint", "https://api.themoviedb.org/3/movie/now_playing")
        return self._fetch_endpoint(endpoint, pages=pages)

    def _fetch_upcoming(self, pages: int = 1) -> List[dict]:
        endpoint = _API["tmdb"].get("upcoming_endpoint", "https://api.themoviedb.org/3/movie/upcoming")
        return self._fetch_endpoint(endpoint, pages=pages)

    def _fetch_trending(self, pages: int = 1) -> List[dict]:
        endpoint = _API["tmdb"].get("trending_endpoint", "https://api.themoviedb.org/3/trending/movie/week")
        return self._fetch_endpoint(endpoint, pages=pages)

    def _build_candidate(self, m: dict, details: Optional[dict] = None) -> dict:
        movie_id = m.get("id")
        runtime = None
        poster_path = m.get("poster_path")
        # If details were not provided by caller, fetch them (legacy path)
        if movie_id and details is None:
            details = self._fetch_movie_details(movie_id)
        if details:
            try:
                runtime = details.get("runtime")
            except Exception:
                runtime = None
            poster_path = poster_path or details.get("poster_path")

        candidate = {
            "id": str(m.get("id", "")),
            "title": m.get("title") or m.get("original_title") or "",
            "description": m.get("overview") or "",
            "poster_path": poster_path,
            "poster_url": f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else "",
            "rating": float(m.get("vote_average") or 0),
            "vote_average": float(m.get("vote_average") or 0),
            "release_date": m.get("release_date") or "",
            "popularity": float(m.get("popularity") or 0),
            "language": "neutral",
        }
        if runtime is not None:
            candidate["runtime"] = runtime
            try:
                candidate["duration_ms"] = int(float(runtime) * 60.0 * 1000.0)
            except Exception:
                pass
        return candidate

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

        # If a query is provided, use the search endpoint ONLY and do not fall back to other endpoints.
        if query and query.strip():
            primary_raw = self._search_movies(query=query.strip(), pages=pages)

            # Fetch details for all returned movies in parallel to speed up processing
            ids = [str(m.get("id")) for m in primary_raw if m.get("id")]
            unique_ids = list(dict.fromkeys(ids))
            details_map: Dict[str, Optional[dict]] = {}
            if unique_ids:
                max_workers = min(20, max(1, len(unique_ids)))
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_id = {}
                    for mid in unique_ids:
                        try:
                            future = executor.submit(self._fetch_movie_details, int(mid))
                            future_to_id[future] = mid
                        except Exception:
                            details_map[mid] = None

                    for fut in as_completed(future_to_id):
                        mid = future_to_id.get(fut)
                        try:
                            details_map[mid] = fut.result()
                        except Exception:
                            details_map[mid] = None

            primary = [self._build_candidate(m, details=details_map.get(str(m.get("id")))) for m in primary_raw]

            cleaned = self._clean_items(primary)
            logger.info("TMDbProvider primary cleaned=%d", len(cleaned))

            # When a user provides a search query, do NOT fall back to popular/top-rated/etc.
            # Return whatever the search endpoint returns (may be empty).
            if len(cleaned) < 10:
                logger.info("TMDbProvider search returned small pool: %d", len(cleaned))

            return cleaned[:limit]

        # No query provided: build a neutral candidate pool from multiple endpoints
        primary_raw: List[dict] = []
        primary_raw.extend(self._fetch_trending(pages=max(1, pages)))
        primary_raw.extend(self._fetch_now_playing(pages=max(1, pages)))
        primary_raw.extend(self._fetch_upcoming(pages=max(1, pages)))
        primary_raw.extend(self._fetch_popular(pages=max(1, pages)))

        primary = [self._build_candidate(m) for m in primary_raw]

        cleaned = self._clean_items(primary)
        logger.info("TMDbProvider primary cleaned=%d", len(cleaned))

        # If insufficient, fetch top-rated as fallback (limited pages)
        if len(cleaned) < max(10, limit // 2):
            fallback_raw = self._fetch_top_rated(pages=pages)
            fallback = [self._build_candidate(m) for m in fallback_raw]
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

