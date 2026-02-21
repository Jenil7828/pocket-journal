import abc
import logging
from typing import Dict, List, Optional, Any

import requests

logger = logging.getLogger("pocket_journal.media.providers")


STANDARD_MEDIA_ITEM = Dict[str, object]


class UnauthorizedError(RuntimeError):
    pass


class MediaProvider(abc.ABC):
    """Abstract provider interface for all media domains.

    Implementations MUST:
    - Fetch a broad, neutral pool (popular/trending or very generic search)
    - Avoid modifying intent vectors or any persistent user state
    - Accept a semantic query and optional request-scoped filters
    - Clean invalid items (require title + description)
    - Return items in the standardized format
    """

    @abc.abstractmethod
    def fetch_candidates(self, query: Optional[str], filters: Optional[Dict[str, Any]], limit: int) -> List[STANDARD_MEDIA_ITEM]:
        """Fetch a pool of candidates using an optional semantic query and filters.

        Args:
            query: semantic search query (may be None to indicate a neutral search)
            filters: request-scoped filters (language, genre, year_from, year_to, etc.)
            limit: desired upper bound for returned candidates (after cleaning)
        """


class BaseHTTPProvider(MediaProvider):
    """Helper base-class with HTTP + retry utilities."""

    max_retries: int = 1  # allow one retry for server errors

    def _request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, object]] = None,
    ) -> Optional[dict]:
        """HTTP request with concise logging and limited retry behavior.

        Behavior:
        - If 401 -> raise UnauthorizedError
        - If 429 -> log rate limit warning and return None
        - If 5xx -> retry once, then raise RuntimeError including body snippet
        - Other non-2xx -> log and return None
        - Never swallow response body; include snippet in logs
        """
        attempt = 0
        last_resp = None
        while attempt <= self.max_retries:
            try:
                resp = requests.request(method, url, headers=headers, params=params, timeout=10)
                status = resp.status_code
                text_snippet = (resp.text or "")[:500]

                if 200 <= status < 300:
                    try:
                        return resp.json()
                    except Exception:
                        logger.warning("Non-JSON response from %s %s: %s", method, url, text_snippet)
                        return None

                if status == 401:
                    logger.warning("Unauthorized response from %s %s (status=401).", method, url)
                    # Raise to allow caller to handle token refresh
                    raise UnauthorizedError("Unauthorized (401)")

                if status == 429:
                    logger.warning("Rate limited by upstream %s %s (status=429). body=%s", method, url, text_snippet)
                    return None

                if 500 <= status < 600:
                    logger.warning("Server error from %s %s (status=%s). attempt=%s body=%s", method, url, status, attempt, text_snippet)
                    last_resp = resp
                    # retry once
                    attempt += 1
                    if attempt > self.max_retries:
                        raise RuntimeError(f"Upstream server error {status}: {text_snippet}")
                    continue

                # Other client errors: log and return None
                logger.warning("HTTP %s %s returned non-OK status=%s body=%s", method, url, status, text_snippet)
                return None

            except UnauthorizedError:
                # Propagate to caller
                raise
            except Exception as exc:  # network or other unexpected exceptions
                logger.warning("HTTP %s %s exception on attempt %s: %s", method, url, attempt, str(exc))
                last_resp = None
                attempt += 1
                if attempt > self.max_retries:
                    raise RuntimeError(f"HTTP request failed after retries: {exc}")
                continue

        # If we exit loop without successful response, raise a generic error
        if last_resp is not None:
            snippet = (last_resp.text or "")[:500]
            raise RuntimeError(f"HTTP request failed after retries, last status={last_resp.status_code} body={snippet}")
        raise RuntimeError("HTTP request failed after retries")

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
