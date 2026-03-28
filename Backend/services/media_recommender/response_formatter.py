import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger("pocket_journal.media.recommendation.formatter")

TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"


def _safe_get(d: Dict[str, Any], *keys):
    for k in keys:
        v = d.get(k)
        if v is not None:
            return v
    return None


def _first_image_url_from_images(images: Any) -> Optional[str]:
    if not images:
        return None
    if isinstance(images, list):
        for img in images:
            if isinstance(img, dict):
                url = img.get("url") or img.get("src") or img.get("uri")
                if url:
                    return url
            elif isinstance(img, str):
                return img
    elif isinstance(images, dict):
        # common shapes: { 'thumbnail': '...', 'small': '...' }
        for v in images.values():
            if isinstance(v, str):
                return v
    return None


def _get_from_metadata(metadata: Dict[str, Any], key: str):
    # Try direct
    if not metadata:
        return None
    if key in metadata and metadata.get(key) is not None:
        return metadata.get(key)
    # Check nested 'metadata' key which may contain provider fields
    nested = metadata.get("metadata")
    if isinstance(nested, dict) and key in nested and nested.get(key) is not None:
        return nested.get(key)
    # Also check nested 'volumeInfo' or similar sub-dicts
    for k in ("volumeInfo", "volume_info", "info", "album", "images", "imageLinks"):
        v = metadata.get(k)
        if isinstance(v, dict) and key in v and v.get(key) is not None:
            return v.get(key)
    return None


def _deep_find_key(obj: Any, key: str, max_depth: int = 4):
    """Recursively search nested dict/list for a given key and return first non-None value.

    This is a presentation-layer fallback to cope with provider-normalized nested shapes.
    """
    def _inner(o, k, depth):
        if depth < 0 or o is None:
            return None
        if isinstance(o, dict):
            if k in o and o.get(k) is not None:
                return o.get(k)
            for v in o.values():
                res = _inner(v, k, depth - 1)
                if res is not None:
                    return res
        elif isinstance(o, list):
            for elem in o:
                res = _inner(elem, k, depth - 1)
                if res is not None:
                    return res
        return None

    try:
        return _inner(obj, key, max_depth)
    except Exception:
        return None


def _serialize_timestamp(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    return str(value)


def _format_movie(item: Dict[str, Any]) -> Dict[str, Any]:
    metadata = item.get("metadata") or {}

    # Detect poster path in common locations, prefer top-level poster_url first
    poster = (
        item.get("poster_url")
        or _safe_get(item, "poster_path")
        or _safe_get(metadata, "poster_url", "poster_path")
        or _get_from_metadata(metadata, "poster_path")
    )
    # If poster is a TMDB poster path like '/abc.jpg', build full URL
    if poster and isinstance(poster, str) and poster.startswith("/"):
        poster_url = f"{TMDB_IMAGE_BASE}{poster}"
    else:
        poster_url = poster

    # Some providers may include images list
    if not poster_url:
        imgs = _safe_get(item, "images") or _get_from_metadata(metadata, "images") or metadata.get("images")
        poster_url = _first_image_url_from_images(imgs)

    return {
        "id": item.get("id"),
        "title": item.get("title"),
        "description": item.get("description"),
        "added_at": _serialize_timestamp(item.get("added_at") or metadata.get("added_at")),
        "release_date": item.get("release_date") or metadata.get("release_date"),
        "rating": item.get("vote_average") or metadata.get("vote_average") or metadata.get("rating"),
        "poster_url": poster_url,
        # Duration fields: prefer explicit runtime, fallback to common metadata keys
        "duration": _safe_get(item, "runtime") or _get_from_metadata(metadata, "runtime") or metadata.get("runtime") or metadata.get("duration") or metadata.get("runtime_minutes"),
        "duration_ms": _safe_get(item, "duration_ms") or _get_from_metadata(metadata, "duration_ms") or metadata.get("duration_ms") or metadata.get("runtime_ms") or _deep_find_key(metadata, "duration_ms") or _deep_find_key(metadata, "duration"),
        "score": item.get("score"),
    }


def _format_song(item: Dict[str, Any]) -> Dict[str, Any]:
    metadata = item.get("metadata") or {}
    # artists may be list of dicts
    artists = item.get("artists") or metadata.get("artists") or []
    if isinstance(artists, list):
        artist_names = ", ".join(a.get("name") if isinstance(a, dict) else str(a) for a in artists if a)
    else:
        artist_names = str(artists)

    # Album object may be nested in different places
    album = item.get("album") or _get_from_metadata(metadata, "album") or metadata.get("album") or metadata.get("albums") or {}
    album_name = None
    if isinstance(album, dict):
        album_name = album.get("name") or album.get("title")
    album_image_url = (
        item.get("album_image_url")
        or _get_from_metadata(metadata, "album_image_url")
    )
    if not album_image_url and isinstance(album, dict):
        images = album.get("images") or album.get("image") or album.get("pictures")
        album_image_url = _first_image_url_from_images(images)

    # fallback to top-level images or metadata images
    if not album_image_url:
        album_image_url = _first_image_url_from_images(item.get("images") or _get_from_metadata(metadata, "images") or metadata.get("images") or metadata.get("album_images"))

    # External URLs
    external_url = (
        item.get("external_url")
        or _get_from_metadata(metadata, "external_url")
    )
    if not external_url:
        external = _safe_get(item, "external_urls") or _get_from_metadata(metadata, "external_urls") or metadata.get("external_urls")
        if isinstance(external, dict):
            # prefer spotify key if present
            external_url = external.get("spotify") or next((v for v in external.values() if isinstance(v, str)), None)
        elif isinstance(external, str):
            external_url = external

    # Resolve duration_ms from multiple potential locations
    duration_ms_val = item.get("duration_ms") or _get_from_metadata(metadata, "duration_ms") or metadata.get("duration_ms") or item.get("duration") or _get_from_metadata(metadata, "duration") or metadata.get("duration") or _deep_find_key(metadata, "duration_ms") or _deep_find_key(metadata, "duration")
    # Normalize to integer milliseconds if present
    try:
        duration_ms_int = int(duration_ms_val) if duration_ms_val is not None else None
    except Exception:
        # if duration is in seconds maybe, convert multiplying
        try:
            duration_ms_int = int(float(duration_ms_val) * 1000)
        except Exception:
            duration_ms_int = None

    duration_seconds = int(duration_ms_int / 1000) if duration_ms_int is not None else None

    return {
        "id": item.get("id"),
        "title": item.get("title"),
        "added_at": _serialize_timestamp(item.get("added_at") or metadata.get("added_at")),
        "artist_names": artist_names or None,
        "album_name": album_name,
        "album_image_url": album_image_url,
        "duration_ms": duration_ms_int,
        "duration_seconds": duration_seconds,
        "external_url": external_url,
        "score": item.get("score"),
    }


def _format_book(item: Dict[str, Any]) -> Dict[str, Any]:
    metadata = item.get("metadata") or {}

    # Possible thumbnail locations: item.thumbnail_url, metadata.thumbnail, metadata.image_links.thumbnail, metadata.volumeInfo.imageLinks.thumbnail
    thumb = _safe_get(item, "thumbnail_url", "thumbnail", "image") or _get_from_metadata(metadata, "thumbnail_url") or _get_from_metadata(metadata, "thumbnail") or metadata.get("thumbnail")
    if not thumb:
        # nested shapes
        vol = metadata.get("volumeInfo") or metadata.get("volume_info") or metadata.get("info") or _get_from_metadata(metadata, "volumeInfo")
        if isinstance(vol, dict):
            il = vol.get("imageLinks") or vol.get("image_links") or vol.get("images")
            if isinstance(il, dict):
                thumb = _safe_get(il, "thumbnail", "smallThumbnail")

    # Sometimes metadata stores image links directly (Google Books v structure)
    if not thumb:
        il = metadata.get("imageLinks") or metadata.get("image_links") or _get_from_metadata(metadata, "imageLinks") or _get_from_metadata(metadata, "image_links")
        if isinstance(il, dict):
            thumb = _safe_get(il, "thumbnail", "smallThumbnail")

    return {
        "id": item.get("id"),
        "title": item.get("title"),
        "added_at": _serialize_timestamp(item.get("added_at") or metadata.get("added_at")),
        "authors": item.get("authors") or metadata.get("authors"),
        "description": item.get("description"),
        "thumbnail_url": thumb,
        "published_date": item.get("publishedDate") or item.get("published_date") or metadata.get("publishedDate"),
        "page_count": item.get("pageCount") or metadata.get("pageCount") or _deep_find_key(metadata, "pageCount") or _deep_find_key(metadata, "page_count"),
        "info_link": item.get("infoLink") or metadata.get("infoLink") or _safe_get(metadata, "volumeInfo", "infoLink"),
        "score": item.get("score"),
    }


def _format_podcast(item: Dict[str, Any]) -> Dict[str, Any]:
    metadata = item.get("metadata") or {}
    image_url = item.get("show_image_url") or item.get("image_url") or metadata.get("image") or metadata.get("thumbnail") or _first_image_url_from_images(metadata.get("images"))
    external = item.get("external_url") or item.get("listennotes_url") or metadata.get("external_url") or metadata.get("listennotes_url")
    if isinstance(external, dict):
        external = next((v for v in external.values() if isinstance(v, str)), None)
    duration_ms = item.get("duration_ms")
    duration_seconds = (duration_ms // 1000) if isinstance(duration_ms, int) and duration_ms is not None else 0
    return {
        "id": item.get("id", None),
        "title": item.get("title", None),
        "added_at": _serialize_timestamp(item.get("added_at") or metadata.get("added_at")),
        "publisher": item.get("publisher", None),
        "description": item.get("description", None),
        "show_image_url": image_url,
        "external_url": external,
        "duration_ms": duration_ms if duration_ms is not None else 0,
        "duration_seconds": duration_seconds,
        "release_date": item.get("release_date", None),
        "score": item.get("score", None),
    }


def format_results(media_type: str, ranked_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format ranked results into frontend-friendly schema based on media_type.

    This function strips internal fields (embeddings, similarity, raw metadata) and
    returns only displayable fields as per the spec.
    """
    base = media_type.split(":", 1)[0].lower()
    out: List[Dict[str, Any]] = []

    # Debug: log structure of first candidate metadata keys for verification
    if ranked_results and logger.isEnabledFor(logging.DEBUG):
        first = ranked_results[0]
        md = first.get("metadata") or {}
        logger.debug("Formatter preview first_candidate_keys=%s metadata_keys=%s", list(first.keys()), list(md.keys()) if isinstance(md, dict) else None)

    for item in ranked_results:
        try:
            if base in ("movie", "movies", "tmdb"):
                f = _format_movie(item)
            elif base in ("song", "songs", "spotify"):
                f = _format_song(item)
            elif base in ("book", "books", "google_books"):
                f = _format_book(item)
            elif base in ("podcast", "podcasts"):
                f = _format_podcast(item)
            else:
                # Generic fallback: expose id, title, description, score
                f = {"id": item.get("id"), "title": item.get("title"), "description": item.get("description"), "score": item.get("score")}
            out.append(f)
            # Additional debug logs to trace missing presentation fields
            try:
                if base in ("song", "songs", "spotify"):
                    if not f.get("duration_ms"):
                        logger.debug("Song missing duration_ms id=%s title=%s item_keys=%s metadata_keys=%s", item.get("id"), item.get("title"), list(item.keys()), list((item.get("metadata") or {}).keys()))
                if base in ("book", "books", "google_books"):
                    if not f.get("page_count"):
                        logger.debug("Book missing page_count id=%s title=%s item_keys=%s metadata_keys=%s", item.get("id"), item.get("title"), list(item.keys()), list((item.get("metadata") or {}).keys()))
            except Exception:
                # Do not break formatting due to logging
                logger.exception("Failed to log missing-field diagnostic for item %s", item.get("id"))
        except Exception as exc:
            logger.exception("Failed to format item %s for media_type=%s: %s", item.get("id"), media_type, str(exc))
            continue
    return out
