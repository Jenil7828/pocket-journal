import logging
from typing import List, Optional, Dict, Any
import os

from .base_provider import BaseHTTPProvider, STANDARD_MEDIA_ITEM
from config_loader import get_config
_API = get_config()["api"]

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
            _API["google_books_endpoint"],
            params=params,
        )
        if not payload:
            return []
        return payload.get("items", []) or []

    def fetch_candidates(self, query: Optional[str], filters: Optional[Dict[str, Any]], limit: int) -> List[STANDARD_MEDIA_ITEM]:
        raw_items: List[dict] = []

        q = (query or "").strip() or "book"
        # Google Books allows maxResults up to 40 per request. Page deterministically.
        remaining = max(0, int(limit))
        start = 0
        page_size = int(_API["google_books_page_size"])
        while remaining > 0:
            cur = min(page_size, remaining)
            batch = self._search(q, max_results=cur, start_index=start)
            if not batch:
                break
            raw_items.extend(batch)
            fetched = len(batch)
            remaining -= fetched
            if fetched < cur:
                break
            start += fetched

        primary: List[dict] = []
        for v in raw_items:
            info = v.get("volumeInfo") or {}
            title = info.get("title") or ""
            description = info.get("description") or ""
            # extract thumbnail if present
            thumb = None
            il = info.get("imageLinks") or info.get("image_links") or {}
            if isinstance(il, dict):
                thumb = il.get("thumbnail") or il.get("smallThumbnail")
                # Upgrade http thumbnails to https
                if thumb and thumb.startswith("http://"):
                    thumb = "https://" + thumb[7:]

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
                    "thumbnail_url": thumb,
                }
            )

        cleaned = self._clean_items(primary)
        logger.info("GoogleBooksProvider primary cleaned=%d", len(cleaned))

        if len(cleaned) < 10:
            logger.warning("Low GoogleBooks candidate pool: %d", len(cleaned))

        return cleaned[:limit]
