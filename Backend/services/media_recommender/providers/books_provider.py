import logging
from typing import List
import os

from .base_provider import BaseHTTPProvider, STANDARD_MEDIA_ITEM

logger = logging.getLogger("pocket_journal.media.providers.books")


class GoogleBooksProvider(BaseHTTPProvider):
    """Book provider backed by Google Books API.

    Uses broad text search without mood/genre filtering.
    """

    def __init__(self) -> None:
        # API key is optional; Google Books allows unauthenticated, but key is preferred.
        self.api_key = os.getenv("GOOGLE_BOOKS_API_KEY")

    def _search(self, query: str, max_results: int, start_index: int = 0) -> List[dict]:
        params = {
            "q": query,
            "maxResults": max_results,
            "startIndex": start_index,
            "printType": "books",
        }
        if self.api_key:
            params["key"] = self.api_key

        payload = self._request(
            "GET",
            "https://www.googleapis.com/books/v1/volumes",
            params=params,
        )
        if not payload:
            return []
        return payload.get("items", []) or []

    def fetch_candidates(self, limit: int) -> List[STANDARD_MEDIA_ITEM]:
        raw_items: List[dict] = []

        # Use single-character and common term queries to keep search neutral.
        queries = ["a", "the", "book"]
        for q in queries:
            for start in (0, 40, 80):
                batch = self._search(q, max_results=40, start_index=start)
                if not batch:
                    continue
                raw_items.extend(batch)
                if len(raw_items) >= max(limit * 3, 240):
                    break
            if len(raw_items) >= max(limit * 3, 240):
                break

        primary: List[dict] = []
        for v in raw_items:
            info = v.get("volumeInfo") or {}
            title = info.get("title") or ""
            description = info.get("description") or ""
            primary.append(
                {
                    "id": v.get("id") or info.get("industryIdentifiers", [{}])[0].get("identifier"),
                    "title": title,
                    "description": description,
                    "authors": info.get("authors"),
                    "publishedDate": info.get("publishedDate"),
                    "pageCount": info.get("pageCount"),
                    "categories": info.get("categories"),
                    "averageRating": info.get("averageRating"),
                    "ratingsCount": info.get("ratingsCount"),
                    "infoLink": info.get("infoLink"),
                }
            )

        cleaned = self._clean_items(primary)
        logger.info("GoogleBooksProvider primary cleaned=%d", len(cleaned))

        # Fallback: if we somehow still have a tiny pool, run an additional query
        if len(cleaned) < 30:
            fallback_raw: List[dict] = []
            for start in (0, 40, 80):
                batch = self._search("story", max_results=40, start_index=start)
                if not batch:
                    continue
                fallback_raw.extend(batch)

            fallback: List[dict] = []
            for v in fallback_raw:
                info = v.get("volumeInfo") or {}
                fallback.append(
                    {
                        "id": v.get("id")
                        or info.get("industryIdentifiers", [{}])[0].get("identifier"),
                        "title": info.get("title") or "",
                        "description": info.get("description") or "",
                        "authors": info.get("authors"),
                        "publishedDate": info.get("publishedDate"),
                        "pageCount": info.get("pageCount"),
                        "categories": info.get("categories"),
                        "averageRating": info.get("averageRating"),
                        "ratingsCount": info.get("ratingsCount"),
                        "infoLink": info.get("infoLink"),
                    }
                )

            fallback_cleaned = self._clean_items(fallback)
            logger.info("GoogleBooksProvider fallback cleaned=%d", len(fallback_cleaned))
            existing_ids = {c["id"] for c in cleaned}
            for item in fallback_cleaned:
                if item["id"] not in existing_ids:
                    cleaned.append(item)
                    existing_ids.add(item["id"])

        if len(cleaned) < 10:
            raise RuntimeError(
                f"GoogleBooksProvider returned insufficient candidates ({len(cleaned)})"
            )

        return cleaned[:limit]


