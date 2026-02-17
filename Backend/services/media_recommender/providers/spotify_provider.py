import base64
import logging
import os
from typing import Dict, List, Optional

from .base_provider import BaseHTTPProvider, STANDARD_MEDIA_ITEM

logger = logging.getLogger("pocket_journal.media.providers.spotify")


class SpotifyProvider(BaseHTTPProvider):
    """Song provider backed by Spotify Web API.

    Uses a broad text search with a generic query (no mood/genre seeding).
    Language preference is honoured only via market and lightweight script checks,
    never through mood/genre filters.
    """

    token_url = "https://accounts.spotify.com/api/token"

    def __init__(self, language: Optional[str] = None) -> None:
        """Initialize provider.

        language: optional language preference such as 'english', 'en', 'hindi', 'hi', or 'both'.
        """
        client_id = os.getenv("SONG_ID")
        client_secret = os.getenv("SONG_SECRET")
        if not client_id or not client_secret:
            raise RuntimeError(
                "SONG_ID and SONG_SECRET environment variables are required for SpotifyProvider"
            )
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token: Optional[str] = None
        lang = (language or "both").strip().lower()
        self._language = lang
        # Normalise a few common values into Spotify markets per requirements
        if lang in ("en", "english"):
            self._market = "US"
        else:
            # 'hindi', 'hi', 'both' or anything else defaults to IN
            self._market = "IN"

    def _get_access_token(self) -> str:
        if self._access_token:
            return self._access_token

        basic = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode("utf-8")).decode(
            "utf-8"
        )
        headers = {"Authorization": f"Basic {basic}"}
        data = {"grant_type": "client_credentials"}

        # Use parent _request to leverage retry + logging
        import requests

        resp = requests.post(self.token_url, headers=headers, data=data, timeout=10)
        if resp.status_code // 100 != 2:
            raise RuntimeError(f"Spotify token request failed: {resp.status_code}")
        payload = resp.json()
        token = payload.get("access_token")
        if not token:
            raise RuntimeError("Spotify token response missing access_token")
        self._access_token = token
        return token

    def _search_tracks(self, query: str, limit: int, offset: int = 0) -> List[dict]:
        token = self._get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        params: Dict[str, object] = {
            "q": query,
            "type": "track",
            "limit": limit,
            "offset": offset,
            "market": self._market,
        }
        payload = self._request(
            "GET",
            "https://api.spotify.com/v1/search",
            headers=headers,
            params=params,
        )
        if not payload:
            return []
        tracks = payload.get("tracks", {}).get("items", []) or []
        # Explicitly ensure we only keep track items (no playlists/albums)
        return [t for t in tracks if (t or {}).get("type") == "track"]

    def _build_items_from_tracks(self, tracks: List[dict]) -> List[dict]:
        primary: List[dict] = []
        for t in tracks:
            if not t:
                continue
            if (t.get("type") or "").lower() != "track":
                # Extra safety: never treat non-track items as candidates
                continue
            title = (t.get("name") or "").strip()
            # Filter out spammy or low-information titles:
            if not title or len(title) < 3:
                continue
            lowered = title.lower()
            if lowered == "music":
                continue
            # Naive repeated-word spam filter (e.g., "music music music")
            words = [w for w in lowered.split() if w]
            if words and all(w == words[0] for w in words) and len(words) >= 3:
                continue

            album = t.get("album") or {}
            artists = t.get("artists") or []
            artist_names = ", ".join(a.get("name", "") for a in artists if a.get("name"))
            description_parts = [
                f"Artist: {artist_names}" if artist_names else "",
                f"Album: {album.get('name', '')}" if album.get("name") else "",
            ]
            description = ". ".join([p for p in description_parts if p]).strip()
            primary.append(
                {
                    "id": t.get("id"),
                    "title": title,
                    "description": description or "Song on Spotify.",
                    "popularity": t.get("popularity"),
                    "duration_ms": t.get("duration_ms"),
                    "album": album,
                    "artists": artists,
                    "external_urls": t.get("external_urls"),
                }
            )
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

    def fetch_candidates(self, limit: int) -> List[STANDARD_MEDIA_ITEM]:
        """Fetch a neutral pool of track candidates from Spotify.

        Language-specific behaviour (per requirements):
        - Hindi:  market=IN, query='genre:bollywood OR hindi'
        - English: market=US, query='tag:new OR tag:hipster'
        - Both/unspecified: market=IN, query='music'
        """
        # Select query based on language (market already chosen in __init__)
        if self._language in ("hi", "hindi"):
            query = "genre:bollywood OR hindi"
        elif self._language in ("en", "english"):
            query = "tag:new OR tag:hipster"
        else:
            query = "music"

        raw_items: List[dict] = []
        # Use several offsets with the SAME query; no fallback to unrelated terms
        for offset in (0, 50, 100, 150, 200):
            batch = self._search_tracks(query, limit=50, offset=offset)
            if not batch:
                continue
            raw_items.extend(batch)
            if len(raw_items) >= max(limit * 3, 240):
                break

        tracks = raw_items

        primary = self._build_items_from_tracks(tracks)
        cleaned = self._dedupe_by_id(self._clean_items(primary))
        logger.info(
            "SpotifyProvider cleaned candidates (lang=%s, market=%s, count=%d)",
            self._language,
            self._market,
            len(cleaned),
        )

        if len(cleaned) < 10:
            raise RuntimeError(f"SpotifyProvider returned insufficient candidates ({len(cleaned)})")

        return cleaned[:limit]


