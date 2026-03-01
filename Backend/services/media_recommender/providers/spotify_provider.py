import base64
import logging
import os
import time
from typing import Dict, List, Optional, Any

from .base_provider import BaseHTTPProvider, STANDARD_MEDIA_ITEM, UnauthorizedError

logger = logging.getLogger("pocket_journal.media.providers.spotify")


class SpotifyProvider(BaseHTTPProvider):
    """Song provider backed by Spotify Web API.

    Accepts a semantic query and request-scoped filters. Providers are stateless
    with respect to language or filters: every call must be independent.

    The provider caches only an access token and its expiry timestamp. All
    requests must handle 401 by invalidating and refreshing the token once.
    """

    token_url = "https://accounts.spotify.com/api/token"

    def __init__(self) -> None:
        client_id = os.getenv("SONG_ID")
        client_secret = os.getenv("SONG_SECRET")
        if not client_id or not client_secret:
            raise RuntimeError(
                "SONG_ID and SONG_SECRET environment variables are required for SpotifyProvider"
            )
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token: Optional[str] = None
        self._access_token_expires_at: Optional[float] = None

    def _is_token_valid(self) -> bool:
        if not self._access_token or not self._access_token_expires_at:
            return False
        return time.time() + 5 < self._access_token_expires_at  # 5s clock skew

    def _get_access_token(self) -> str:
        """Obtain a client credentials token and cache it with expiry.

        This function always fetches a new token if none cached or expired.
        It does not use the generic _request helper to avoid retry semantics.
        """
        if self._is_token_valid():
            return self._access_token  # type: ignore

        basic = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode("utf-8")).decode(
            "utf-8"
        )
        headers = {"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"}
        data = {"grant_type": "client_credentials"}

        # Use requests directly for token fetch; raise clean errors on failure
        import requests

        resp = requests.post(self.token_url, headers=headers, data=data, timeout=10)
        try:
            payload = resp.json()
        except Exception:
            payload = {}
        if resp.status_code // 100 != 2:
            logger.warning("Spotify token request failed status=%s body=%s", resp.status_code, (resp.text or "")[:300])
            raise RuntimeError(f"Spotify token request failed: {resp.status_code}")

        token = payload.get("access_token")
        expires = payload.get("expires_in")
        if not token:
            raise RuntimeError("Spotify token response missing access_token")

        self._access_token = token
        try:
            self._access_token_expires_at = time.time() + int(expires or 3600)
        except Exception:
            self._access_token_expires_at = time.time() + 3600

        logger.info("Spotify token refreshed")
        return token

    def _invalidate_token(self) -> None:
        self._access_token = None
        self._access_token_expires_at = None

    def _fetch_track_details(self, track_id: str) -> Optional[dict]:
        """Fetch full track details for a single track id to retrieve duration_ms if missing."""
        if not track_id:
            return None
        # Ensure token is valid
        token = self._get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        url = f"https://api.spotify.com/v1/tracks/{track_id}"
        try:
            payload = self._request("GET", url, headers=headers)
            return payload
        except UnauthorizedError:
            logger.info("Spotify 401 detected while fetching track details — retrying with refreshed token")
            self._invalidate_token()
            try:
                token = self._get_access_token()
                headers = {"Authorization": f"Bearer {token}"}
                payload = self._request("GET", url, headers=headers)
                return payload
            except UnauthorizedError:
                logger.warning("Spotify track details unauthorized after refresh for id=%s", track_id)
                return None
        except Exception as exc:
            logger.warning("Failed to fetch Spotify track details id=%s: %s", track_id, str(exc))
            return None

    def _search_tracks(self, query: str, limit: int, offset: int = 0, market: Optional[str] = None) -> List[dict]:
        # Acquire token (refresh if needed)
        token = self._get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        params: Dict[str, object] = {
            "q": query,
            "type": "track",
            "limit": limit,
            "offset": offset,
        }
        if market:
            params["market"] = market

        # Call _request and handle UnauthorizedError by refreshing once
        try:
            payload = self._request(
                "GET",
                "https://api.spotify.com/v1/search",
                headers=headers,
                params=params,
            )
        except UnauthorizedError:
            # Token likely expired or invalid -> invalidate and retry once
            logger.info("Spotify 401 detected — retrying with new token")
            self._invalidate_token()
            # fetch new token and retry request once
            try:
                new_token = self._get_access_token()
                new_headers = {"Authorization": f"Bearer {new_token}"}
                payload = self._request(
                    "GET",
                    "https://api.spotify.com/v1/search",
                    headers=new_headers,
                    params=params,
                )
            except UnauthorizedError:
                # Still unauthorized after refresh
                raise RuntimeError("Spotify API unauthorized after token refresh")

        if not payload:
            return []
        tracks = payload.get("tracks", {}).get("items", []) or []
        # Ensure only track items
        return [t for t in tracks if (t or {}).get("type") == "track"]

    def _build_items_from_tracks(self, tracks: List[dict]) -> List[dict]:
        primary: List[dict] = []
        for t in tracks:
            if not t:
                continue
            if (t.get("type") or "").lower() != "track":
                continue
            title = (t.get("name") or "").strip()
            if not title or len(title) < 3:
                continue
            # Basic spam filtering (avoid repeated single-word titles)
            lowered = title.lower()
            words = [w for w in lowered.split() if w]
            if words and len(words) >= 3 and all(w == words[0] for w in words):
                continue

            album = t.get("album") or {}
            artists = t.get("artists") or []
            artist_names = ", ".join(a.get("name", "") for a in artists if a.get("name"))
            # Extract album image
            album_images = album.get("images") or []
            album_image_url = album_images[0].get("url") if album_images else None

            # Extract external URL
            external_urls = t.get("external_urls") or {}
            external_url = external_urls.get("spotify") if isinstance(external_urls, dict) else None
            description_parts = [
                f"Artist: {artist_names}" if artist_names else "",
                f"Album: {album.get('name', '')}" if album.get("name") else "",
            ]
            description = ". ".join([p for p in description_parts if p]).strip()
            # If duration_ms missing, attempt to enrich by fetching track details
            duration_ms_val = t.get("duration_ms")
            if duration_ms_val is None:
                details = self._fetch_track_details(t.get("id"))
                if details:
                    duration_ms_val = details.get("duration_ms")
            primary.append(
                {
                    "id": t.get("id"),
                    "title": title,
                    "description": description or "Song on Spotify.",
                    "popularity": t.get("popularity"),
                    "duration_ms": duration_ms_val,
                    # also include 'duration' as ms for tolerant formatters
                    "duration": duration_ms_val,
                    "album": album,
                    "album_image_url": album_image_url,   # pre-extracted
                    "artist_names": artist_names,          # pre-flattened string
                    "artists": artists,
                    "external_url": external_url,          # pre-resolved string
                    "external_urls": t.get("external_urls"),
                }
            )
            # Debug: log if duration is missing for this track after enrichment
            if logger.isEnabledFor(logging.DEBUG) and (duration_ms_val is None):
                logger.debug("Spotify track missing duration_ms after enrichment id=%s title=%s keys=%s", t.get("id"), t.get("name"), list(t.keys()))
        return primary

    def _dedupe_by_id(self, items: List[STANDARD_MEDIA_ITEM]) -> List[STANDARD_MEDIA_ITEM]:
        seen = set()
        unique: List[STANDARD_MEDIA_ITEM] = []
        for item in items:
            mid = item.get("id")
            if not mid or mid in seen:
                continue
            seen.add(mid)
            unique.append(item)
        return unique


    def fetch_candidates(self, query: Optional[str], filters: Optional[Dict[str, Any]], limit: int) -> List[STANDARD_MEDIA_ITEM]:
        """Fetch a pool of candidates from Spotify using a semantic query and request-scoped filters.

        Implements language-specific queries and post-fetch language filtering.
        """
        q = (query or "").strip() or "top hits"
        queries = [q]
        market = None
        lang = None
        if filters:
            lang = (filters.get("language") or "").strip().lower()
            if lang in ("hi", "hindi"):
                queries = ["hindi songs", "bollywood hits", "hindi film songs"]
                market = "IN"
            elif lang in ("en", "english"):
                queries = ["english pop hits", "top english songs", "english top 40"]
                market = "US"
            genre = (filters.get("genre") or "").strip()
            if genre:
                queries = [f"{q} {genre}" for q in queries]
            year_from = filters.get("year_from")
            year_to = filters.get("year_to")
            if year_from or year_to:
                try:
                    yf = int(year_from) if year_from else None
                    yt = int(year_to) if year_to else None
                    if yf and yt:
                        queries = [f"{q} year:{yf}-{yt}" for q in queries]
                    elif yf:
                        queries = [f"{q} year:{yf}-" for q in queries]
                    elif yt:
                        queries = [f"{q} year:-{yt}" for q in queries]
                except Exception:
                    pass

        # Divide limit evenly across queries
        per_query = max(1, limit // len(queries))
        raw_items: List[dict] = []
        seen_ids = set()
        for qx in queries:
            offset = 0
            remaining = per_query
            page_size = 50
            while remaining > 0:
                cur_page = min(page_size, remaining)
                batch = self._search_tracks(qx, limit=cur_page, offset=offset, market=market)
                if not batch:
                    break
                # Deduplicate by track id
                for item in batch:
                    tid = item.get("id")
                    if tid and tid not in seen_ids:
                        raw_items.append(item)
                        seen_ids.add(tid)
                fetched = len(batch)
                remaining -= fetched
                if fetched < cur_page:
                    break
                offset += fetched

        tracks = raw_items
        primary = self._build_items_from_tracks(tracks)
        normalized = []
        for p in primary:
            item: Dict[str, Any] = {}
            if p.get("id") is not None:
                item["id"] = p.get("id")
            item["title"] = p.get("title")
            item["description"] = p.get("description")
            for k, v in p.items():
                if k in ("id", "title", "description"):
                    continue
                item[k] = v
            normalized.append(item)

        cleaned = self._dedupe_by_id(self._clean_items(normalized))
        logger.info(
            "SpotifyProvider cleaned candidates (queries=%s, market=%s, count=%d)",
            queries,
            market,
            len(cleaned),
        )

        if len(cleaned) < 10:
            logger.warning("Low Spotify candidate pool: %d", len(cleaned))

        # Language post-filter
        cleaned = self._filter_by_language(cleaned, lang)
        return cleaned[:limit]

    def _filter_by_language(self, items: List[dict], language: Optional[str]) -> List[dict]:
        def has_devanagari(text: str) -> bool:
            return any('\u0900' <= c <= '\u097F' for c in text)

        if not language:
            return items
        language = language.lower()
        if language in ("hi", "hindi"):
            filtered = []
            for item in items:
                text = f"{item.get('title','')} {item.get('artist_names','')} {item.get('album_name','')}"
                if has_devanagari(text):
                    filtered.append(item)
            if len(filtered) < 10:
                return items  # fallback to all if too few
            return filtered
        elif language in ("en", "english"):
            filtered = []
            for item in items:
                text = f"{item.get('title','')} {item.get('artist_names','')}"
                if not has_devanagari(text):
                    filtered.append(item)
            return filtered
        else:
            return items

