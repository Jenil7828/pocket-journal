import abc
import logging
from typing import Dict, List, Optional

import requests

logger = logging.getLogger("pocket_journal.media.providers")


STANDARD_MEDIA_ITEM = Dict[str, object]


class MediaProvider(abc.ABC):
    """Abstract provider interface for all media domains.

    Implementations MUST:
    - Fetch a broad, neutral pool (popular/trending or very generic search)
    - Avoid mood / genre based filtering
    - Clean invalid items (require title + description)
    - Retry each API call up to 2 additional times on failure
    - Use a fallback endpoint if primary yields < 30 items
    - Raise an error if total cleaned results are still < 10
    - Return items in the standardized format
    """

    @abc.abstractmethod
    def fetch_candidates(self, limit: int) -> List[STANDARD_MEDIA_ITEM]:
        """Fetch a neutral pool of candidates.

        Args:
            limit: Desired upper bound for returned candidates (after cleaning).
        """


class BaseHTTPProvider(MediaProvider):
    """Helper base-class with HTTP + retry utilities."""

    max_retries: int = 2  # number of retries in addition to the initial attempt

    def _request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, object]] = None,
    ) -> Optional[dict]:
        """HTTP request with basic retry and concise logging."""
        attempt = 0
        last_exc: Optional[Exception] = None
        while attempt <= self.max_retries:
            try:
                resp = requests.request(method, url, headers=headers, params=params, timeout=10)
                if resp.status_code // 100 == 2:
                    return resp.json()
                logger.warning(
                    "HTTP %s %s failed (status=%s, attempt=%s)",
                    method,
                    url,
                    resp.status_code,
                    attempt,
                )
            except Exception as exc:  # pragma: no cover - network failure path
                last_exc = exc
                logger.warning(
                    "HTTP %s %s exception on attempt %s: %s",
                    method,
                    url,
                    attempt,
                    str(exc),
                )
            attempt += 1

        if last_exc:
            raise RuntimeError(f"HTTP request failed after retries: {last_exc}")
        raise RuntimeError(f"HTTP request failed after retries for {url}")

    @staticmethod
    def _clean_items(raw_items: List[dict]) -> List[STANDARD_MEDIA_ITEM]:
        """Filter and normalize raw API results into the standard schema."""
        cleaned: List[STANDARD_MEDIA_ITEM] = []
        for item in raw_items or []:
            try:
                mid = str(item.get("id") or item.get("guid") or item.get("external_id") or "")
                title = (item.get("title") or "").strip()
                description = (item.get("description") or "").strip()
                # Enforce minimum fields
                if not mid or not title or not description:
                    continue
                metadata = dict(item)
                # Remove potentially large text fields we already normalized
                metadata.pop("overview", None)
                metadata.pop("description", None)
                metadata.pop("long_description", None)
                cleaned.append(
                    {
                        "id": mid,
                        "title": title,
                        "description": description,
                        "metadata": metadata,
                    }
                )
            except Exception:
                # Ignore malformed items, but keep going
                continue
        return cleaned


