import base64
import logging
import os
import time
from typing import Dict, List, Optional, Any

import requests
from requests import HTTPError

from .base_provider import BaseHTTPProvider, STANDARD_MEDIA_ITEM
from config_loader import get_config
_API = get_config()["api"]

logger = logging.getLogger()


class PodcastAPIProvider(BaseHTTPProvider):
    """Podcast provider backed by Spotify episode search API."""

    token_url = _API["spotify"]["token_endpoint"]

    def __init__(self) -> None:
        client_id = os.getenv("SONG_ID")
        client_secret = os.getenv("SONG_SECRET")
        if not client_id or not client_secret:
            raise RuntimeError(
                "SONG_ID and SONG_SECRET environment variables are required for PodcastAPIProvider"
            )
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token: Optional[str] = None
        self._access_token_expires_at: Optional[float] = None

    def _is_token_valid(self) -> bool:
        if not self._access_token or not self._access_token_expires_at:
            return False
        return time.time() + 5 < self._access_token_expires_at

    def _get_access_token(self) -> str:
        if self._is_token_valid():
            return self._access_token
        basic = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode("utf-8")
        ).decode("utf-8")
        headers = {
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {"grant_type": "client_credentials"}
        resp = requests.post(self.token_url, headers=headers, data=data, timeout=int(_API["request_timeout"]))
        try:
            resp.raise_for_status()
            payload = resp.json()
            self._access_token = payload["access_token"]
            self._access_token_expires_at = time.time() + int(payload["expires_in"])
            logger.info("[SRV][podcasts] token_refreshed")
            return self._access_token
        except Exception as e:
            logger.error("[ERR][podcasts] token_request_failed error=%s", str(e))
            raise RuntimeError("Failed to fetch Spotify token")

    def _invalidate_token(self) -> None:
        self._access_token = None
        self._access_token_expires_at = None

    def _spotify_search(
        self,
        query: str,
        search_type: str,
        limit: int,
        offset: int = 0,
        market: Optional[str] = None,
    ) -> Dict[str, Any]:
        token = self._get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        params: Dict[str, object] = {
            "q": query,
            "type": search_type,
            "limit": limit,
            "offset": offset,
        }
        if market:
            params["market"] = market

        resp = requests.get(
            "https://api.spotify.com/v1/search",
            headers=headers,
            params=params,
            timeout=int(_API["request_timeout"]),
        )
        if resp.status_code == 401:
            self._invalidate_token()
            token = self._get_access_token()
            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.get(
                "https://api.spotify.com/v1/search",
                headers=headers,
                params=params,
                timeout=int(_API["request_timeout"]),
            )
        resp.raise_for_status()
        return resp.json()

    def _build_episode_items(self, episodes: List[dict]) -> List[dict]:
        items = []
        for ep in episodes:
            if not ep:
                continue

            title = (ep.get("name") or "").strip()
            if not title:
                continue

            description = (ep.get("description") or "Podcast episode on Spotify.")[:300]
            show = ep.get("show") or {}
            publisher = show.get("publisher") if show else None

            show_image_url = None
            ep_images = ep.get("images") or []
            show_images = show.get("images") or []
            if ep_images:
                show_image_url = ep_images[0].get("url")
            elif show_images:
                show_image_url = show_images[0].get("url")

            items.append({
                "id": ep.get("id"),
                "title": title,
                "description": description,
                "publisher": publisher,
                "show_image_url": show_image_url,
                "external_url": (ep.get("external_urls") or {}).get("spotify"),
                "duration_ms": ep.get("duration_ms"),
                "release_date": ep.get("release_date"),
            })
        return items

    def _build_show_items(self, shows: List[dict]) -> List[dict]:
        items = []
        for show in shows:
            if not show:
                continue

            show_id = show.get("id")
            title = (show.get("name") or "").strip()
            if not show_id or not title:
                continue

            images = show.get("images") or []
            show_image_url = images[0].get("url") if images else None
            description = (show.get("description") or show.get("publisher") or "Podcast show on Spotify.")[:300]

            items.append({
                "id": show_id,
                "title": title,
                "description": description,
                "publisher": show.get("publisher"),
                "show_image_url": show_image_url,
                "external_url": (show.get("external_urls") or {}).get("spotify"),
                "duration_ms": None,
                "release_date": None,
            })
        return items

    def fetch_candidates(
        self,
        query: Optional[str],
        filters: Optional[Dict[str, Any]],
        limit: int,
    ) -> List[STANDARD_MEDIA_ITEM]:
        q = (query or "").strip() or "top podcast episodes"
        queries = [q]
        market = None
        lang = None

        if filters:
            lang = (filters.get("language") or "").strip().lower()
            if lang in ("hi", "hindi"):
                queries = ["hindi podcast", "bollywood podcast", "hindi show episodes"]
                market = "IN"
            elif lang in ("en", "english"):
                queries = ["english podcast episodes", "top english podcast", "popular podcast"]
                market = "US"

            genre = (filters.get("genre") or "").strip()
            if genre:
                queries = [f"{qx} {genre}" for qx in queries]

        per_query = max(1, limit // len(queries))
        raw_items: List[dict] = []
        seen_ids: set = set()

        for qx in queries:
            offset = 0
            remaining = per_query
            page_size = 50

            while remaining > 0:
                cur_page = min(page_size, remaining)
                try:
                    payload = self._spotify_search(
                        query=qx,
                        search_type="episode",
                        limit=cur_page,
                        offset=offset,
                        market=market,
                    )
                    batch_items = self._build_episode_items(
                        payload.get("episodes", {}).get("items", []) or []
                    )
                except HTTPError as e:
                    status_code = getattr(e.response, "status_code", None)
                    if status_code == 403:
                        logger.warning(
                            "[PROVIDER][podcasts] search_forbidden query=%s fallback_to_shows", qx
                        )
                        try:
                            payload = self._spotify_search(
                                query=qx,
                                search_type="show",
                                limit=cur_page,
                                offset=offset,
                                market=market,
                            )
                            batch_items = self._build_show_items(
                                payload.get("shows", {}).get("items", []) or []
                            )
                        except Exception as show_exc:
                            logger.error(
                                "[PROVIDER][podcasts] fallback_show_search_failed query=%s error=%s",
                                qx,
                                str(show_exc),
                            )
                            break
                    else:
                        logger.error("[PROVIDER][podcasts] episode_search_failed query=%s error=%s", qx, str(e))
                        break
                except Exception as e:
                    logger.error("[PROVIDER][podcasts] episode_search_failed query=%s error=%s", qx, str(e))
                    break

                for item in batch_items:
                    item_id = item.get("id")
                    if item_id and item_id not in seen_ids:
                        raw_items.append(item)
                        seen_ids.add(item_id)

                fetched = len(batch_items)
                remaining -= fetched
                if fetched < cur_page:
                    break
                offset += fetched

        items = self._filter_by_language(raw_items, lang)
        logger.info("[PROVIDER][podcasts] cleaned_candidates count=%d", len(items))
        return items[:limit]

    def _filter_by_language(
        self, items: List[dict], language: Optional[str]
    ) -> List[dict]:
        def has_devanagari(text: str) -> bool:
            return any("\u0900" <= c <= "\u097F" for c in text)

        if not language:
            return items

        language = language.lower()

        if language in ("hi", "hindi"):
            filtered = [
                item for item in items
                if has_devanagari(
                    f"{item.get('title','')} {item.get('publisher','')} {item.get('description','')}"
                )
            ]
            return filtered if len(filtered) >= 10 else items

        elif language in ("en", "english"):
            return [
                item for item in items
                if not has_devanagari(
                    f"{item.get('title','')} {item.get('publisher','')}"
                )
            ]

        return items
