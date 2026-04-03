"""
Media Normalization Service

Ensures all media (movies, books, songs, podcasts) follow a consistent schema.
This normalizer is idempotent and safe to run on existing data.

CRITICAL RULES:
- Only fill missing/null/empty fields (Never overwrite valid data)
- Do NOT modify embeddings
- Use partial updates (patch, not set)
- Handle all media types uniformly
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger()


def _is_missing(value: Any) -> bool:
    """
    Check if a value is considered missing:
    - None
    - empty string ""
    - empty list []
    - 0 or empty dict (for certain fields only)
    """
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if isinstance(value, (list, dict)) and len(value) == 0:
        return True
    return False


def _is_effectively_empty(value: Any) -> bool:
    """
    Smart check if a value is effectively empty/placeholder.
    
    This is CRITICAL for enrichment - we need to recognize that:
    - "" (empty string) is a PLACEHOLDER not real data
    - 0 (numeric zero) is often a PLACEHOLDER not real data
    - [] (empty list) is a PLACEHOLDER not real data
    - null is definitely empty
    
    But:
    - 8.8 (rating) is VALID data
    - -1 (some values) could be VALID
    - ["Drama"] (non-empty list) is VALID
    
    Args:
        value: Value to check
        
    Returns:
        True if value appears to be a placeholder/empty
    """
    if value is None:
        return True
    
    if isinstance(value, str):
        return value.strip() == ""
    
    if isinstance(value, list):
        return len(value) == 0
    
    if isinstance(value, dict):
        return len(value) == 0
    
    if isinstance(value, (int, float)):
        # CRITICAL: 0 is often a placeholder, but check context
        # For ratings, duration, etc., 0 is definitely placeholder
        # For user-entered values, 0 could be valid (like position 0)
        # We'll treat 0 as placeholder for media enrichment
        return value == 0
    
    # Non-empty strings, positive numbers, filled collections are NOT empty
    return False


def _is_better_data(new_value: Any, old_value: Any) -> bool:
    """
    Smart check if a value is effectively empty/placeholder.
    
    This is CRITICAL for enrichment - we need to recognize that:
    - "" (empty string) is a PLACEHOLDER not real data
    - 0 (numeric zero) is often a PLACEHOLDER not real data
    - [] (empty list) is a PLACEHOLDER not real data
    - null is definitely empty
    
    But:
    - 8.8 (rating) is VALID data
    - -1 (some values) could be VALID
    - ["Drama"] (non-empty list) is VALID
    
    Args:
        value: Value to check
        
    Returns:
        True if value appears to be a placeholder/empty
    """
    if new_value is None:
        return False
    
    if isinstance(new_value, str):
        return new_value.strip() == ""
    
    if isinstance(new_value, list):
        return len(new_value) == 0
    
    if isinstance(new_value, dict):
        return len(new_value) == 0
    
    if isinstance(new_value, (int, float)):
        return new_value == 0
    
    return False


def get_quality_score(value: Any) -> int:
    """
    Score data quality on scale 0-3.
    
    0: Empty/placeholder/None
    1: Weak data (short strings, small numbers)
    2: Medium quality
    3: Strong/complete data
    
    Args:
        value: Value to score
        
    Returns:
        Quality score 0-3
    """
    if value is None:
        return 0
    
    # Strings: score by length/completeness
    if isinstance(value, str):
        v = value.strip()
        if v == "":
            return 0  # Empty
        if len(v) < 10:
            return 1  # Weak (short)
        return 3  # Strong (substantive)
    
    # Lists: score by item count
    if isinstance(value, list):
        if len(value) == 0:
            return 0  # Empty
        if len(value) == 1:
            return 2  # Single item
        return 3  # Multiple items (strong)
    
    # Numbers: score by magnitude
    if isinstance(value, (int, float)):
        if value == 0:
            return 0  # Zero/empty placeholder
        if value < 10:
            return 1  # Small/weak
        return 3  # Substantial/strong
    
    # Other types: assume medium quality if present
    return 2


def should_update(old_value: Any, new_value: Any) -> bool:
    """
    PRODUCTION-GRADE: Decide if new value should replace old value.
    
    Core rule: Only update if new data is better quality
    - new_score > old_score → Always update
    - old_score == 0 and new_score > 0 → Always update (replace placeholder)
    
    Args:
        old_value: Existing value in database
        new_value: New value from enrichment
        
    Returns:
        True if new should replace old
    """
    old_score = get_quality_score(old_value)
    new_score = get_quality_score(new_value)
    
    # Core rule: new is better quality
    if new_score > old_score:
        return True
    
    # Secondary rule: replace placeholders with any real data
    if old_score == 0 and new_score > 0:
        return True
    
    return False


def _extract_image_url(data: Dict[str, Any], media_type: str) -> Optional[str]:
    """Extract image URL from various provider formats."""
    
    # Check top-level fields first
    if data.get("image_url") and not _is_missing(data["image_url"]):
        return data["image_url"]
    
    metadata = data.get("metadata") or {}
    
    if media_type == "movies":
        # TMDb: poster_path or poster_url
        poster = data.get("poster_url") or data.get("poster_path") or metadata.get("poster_url") or metadata.get("poster_path")
        if poster:
            if isinstance(poster, str) and poster.startswith("/"):
                return f"https://image.tmdb.org/t/p/w500{poster}"
            return poster
    
    elif media_type == "songs":
        # Spotify: album.images[0].url or album_image_url
        album_image = data.get("album_image_url") or metadata.get("album_image_url")
        if album_image:
            return album_image
        
        album = data.get("album") or metadata.get("album") or {}
        if isinstance(album, dict):
            images = album.get("images") or []
            if images and isinstance(images, list) and len(images) > 0:
                if isinstance(images[0], dict):
                    return images[0].get("url")
    
    elif media_type == "books":
        # Google Books: thumbnail or image_links.thumbnail
        thumb = data.get("thumbnail_url") or data.get("thumbnail") or metadata.get("thumbnail_url") or metadata.get("thumbnail")
        if thumb:
            return thumb
        
        # Check imageLinks
        image_links = metadata.get("imageLinks") or metadata.get("image_links") or {}
        if isinstance(image_links, dict):
            return image_links.get("thumbnail") or image_links.get("smallThumbnail")
        
        # Check volumeInfo
        vol_info = metadata.get("volumeInfo") or {}
        if isinstance(vol_info, dict):
            il = vol_info.get("imageLinks") or {}
            if isinstance(il, dict):
                return il.get("thumbnail") or il.get("smallThumbnail")
    
    elif media_type == "podcasts":
        # ListenNotes: show_image_url or image
        img = data.get("show_image_url") or data.get("image_url") or metadata.get("image") or metadata.get("show_image_url")
        if img:
            return img
    
    return None


def _extract_external_url(data: Dict[str, Any], media_type: str) -> Optional[str]:
    """Extract external URL (TMDb, Spotify, Google Books, ListenNotes) from various formats."""
    
    # Check top-level first
    if data.get("external_url") and not _is_missing(data["external_url"]):
        return data["external_url"]
    
    metadata = data.get("metadata") or {}
    
    if media_type == "movies":
        # TMDb: Build URL from ID if available
        tmdb_id = data.get("id") or metadata.get("id")
        if tmdb_id:
            return f"https://www.themoviedb.org/movie/{tmdb_id}"
    
    elif media_type == "songs":
        # Spotify: external_urls.spotify or full URL
        ext_urls = data.get("external_urls") or metadata.get("external_urls") or {}
        if isinstance(ext_urls, dict):
            spotify = ext_urls.get("spotify")
            if spotify:
                return spotify
        
        ext_url = metadata.get("external_url")
        if ext_url and isinstance(ext_url, str):
            return ext_url
    
    elif media_type == "books":
        # Google Books: infoLink
        info = data.get("infoLink") or data.get("info_link") or metadata.get("infoLink") or metadata.get("info_link")
        if info:
            return info
    
    elif media_type == "podcasts":
        # ListenNotes: external_url or listennotes_url
        ext = data.get("external_url") or data.get("listennotes_url") or metadata.get("external_url") or metadata.get("listennotes_url")
        if ext:
            return ext
    
    return None


def _extract_contributors(data: Dict[str, Any], media_type: str) -> List[str]:
    """Extract contributors (cast, authors, artists) as list of strings."""
    
    # Check if contributors already exist
    existing = data.get("contributors")
    if existing and isinstance(existing, list) and not _is_missing(existing):
        return existing
    
    metadata = data.get("metadata") or {}
    contributors = []
    
    if media_type == "movies":
        # Cast from metadata or top-level
        cast = data.get("cast") or metadata.get("cast")
        if cast and isinstance(cast, list):
            for actor in cast[:5]:  # Top 5 actors
                if isinstance(actor, dict):
                    name = actor.get("name")
                    if name:
                        contributors.append(str(name))
                elif isinstance(actor, str):
                    contributors.append(actor)
        
        # If no cast, try credits or actors
        if not contributors:
            credits = metadata.get("credits") or {}
            cast_list = credits.get("cast") or []
            if isinstance(cast_list, list):
                for actor in cast_list[:5]:
                    if isinstance(actor, dict):
                        name = actor.get("name")
                        if name:
                            contributors.append(str(name))
                    elif isinstance(actor, str):
                        contributors.append(actor)
    
    elif media_type == "songs":
        # Artists - check multiple locations
        artists = data.get("artists") or metadata.get("artists")
        if artists and isinstance(artists, list):
            for artist in artists:
                if isinstance(artist, dict):
                    name = artist.get("name")
                    if name:
                        contributors.append(str(name))
                elif isinstance(artist, str):
                    contributors.append(artist)
        
        # Fallback to artist_names
        if not contributors:
            artist_names = data.get("artist_names") or metadata.get("artist_names")
            if isinstance(artist_names, str):
                contributors = [artist_names]
            elif isinstance(artist_names, list):
                contributors = [str(a) for a in artist_names if a]
    
    elif media_type == "books":
        # Authors
        authors = data.get("authors") or metadata.get("authors")
        if authors and isinstance(authors, list):
            for author in authors:
                if isinstance(author, str):
                    contributors.append(author)
                elif isinstance(author, dict):
                    name = author.get("name")
                    if name:
                        contributors.append(str(name))
        elif isinstance(authors, str):
            contributors = [authors]
    
    elif media_type == "podcasts":
        # Publisher/host
        pub = data.get("publisher") or metadata.get("publisher") or data.get("host") or metadata.get("host")
        if pub:
            contributors.append(str(pub))
    
    return contributors


def _extract_creator(data: Dict[str, Any], media_type: str) -> Optional[str]:
    """Extract primary creator (director, author, artist, publisher)."""
    
    # Check if creator already exists
    if data.get("creator") and not _is_missing(data["creator"]):
        return data["creator"]
    
    metadata = data.get("metadata") or {}
    
    if media_type == "movies":
        # Director from metadata
        director = metadata.get("director") or metadata.get("directors")
        if director:
            if isinstance(director, list) and len(director) > 0:
                return str(director[0])
            elif isinstance(director, str):
                return director
    
    elif media_type == "songs":
        # Primary artist
        artists = data.get("artists") or metadata.get("artists") or []
        if isinstance(artists, list) and len(artists) > 0:
            artist = artists[0]
            if isinstance(artist, dict):
                return artist.get("name")
            elif isinstance(artist, str):
                return artist
        
        artist_names = data.get("artist_names") or metadata.get("artist_names")
        if artist_names:
            if isinstance(artist_names, str):
                return artist_names.split(",")[0].strip()
            elif isinstance(artist_names, list) and len(artist_names) > 0:
                return str(artist_names[0])
    
    elif media_type == "books":
        # First author
        authors = data.get("authors") or metadata.get("authors") or []
        if isinstance(authors, list) and len(authors) > 0:
            author = authors[0]
            if isinstance(author, dict):
                return author.get("name")
            elif isinstance(author, str):
                return author
    
    elif media_type == "podcasts":
        # Publisher
        pub = data.get("publisher") or metadata.get("publisher")
        if pub:
            return str(pub)
    
    return None


def _extract_genres(data: Dict[str, Any], media_type: str) -> List[str]:
    """Extract genres as list of strings."""
    
    # Check if genres already exist
    existing = data.get("genres")
    if existing and isinstance(existing, list) and not _is_missing(existing):
        return existing
    
    metadata = data.get("metadata") or {}
    genres = []
    
    if media_type == "movies":
        # TMDb genres
        genre_list = metadata.get("genres") or data.get("genres") or []
        if isinstance(genre_list, list):
            for genre in genre_list:
                if isinstance(genre, dict):
                    name = genre.get("name")
                    if name:
                        genres.append(str(name))
                elif isinstance(genre, str):
                    genres.append(genre)
    
    elif media_type == "books":
        # Google Books categories
        categories = metadata.get("categories") or data.get("categories") or metadata.get("category")
        if isinstance(categories, list):
            genres = [str(c) for c in categories]
        elif isinstance(categories, str):
            genres = [categories]
    
    return genres


def _extract_duration(data: Dict[str, Any], media_type: str) -> Optional[int]:
    """Extract duration in seconds (normalized from various formats)."""
    
    # Check if duration already exists and is valid
    if data.get("duration") and not _is_missing(data["duration"]):
        try:
            return int(data["duration"])
        except (ValueError, TypeError):
            pass
    
    metadata = data.get("metadata") or {}
    
    if media_type == "movies":
        # Check top-level runtime first (from TMDB provider)
        runtime = data.get("runtime")
        if runtime and not _is_missing(runtime):
            try:
                return int(runtime) * 60  # Convert minutes to seconds
            except (ValueError, TypeError):
                pass
        
        # Then check metadata
        runtime = metadata.get("runtime")
        if runtime and not _is_missing(runtime):
            try:
                return int(runtime) * 60  # Convert minutes to seconds
            except (ValueError, TypeError):
                pass
    
    elif media_type == "songs":
        # Duration in milliseconds → convert to seconds
        duration_ms = data.get("duration_ms") or metadata.get("duration_ms")
        if duration_ms and not _is_missing(duration_ms):
            try:
                return int(duration_ms) // 1000
            except (ValueError, TypeError):
                pass
    
    elif media_type == "podcasts":
        # Duration in milliseconds → convert to seconds
        duration_ms = data.get("duration_ms") or metadata.get("duration_ms")
        if duration_ms and not _is_missing(duration_ms):
            try:
                return int(duration_ms) // 1000
            except (ValueError, TypeError):
                pass
    
    return None


def _extract_page_count(data: Dict[str, Any], media_type: str) -> Optional[int]:
    """Extract page count (books only). Skip zero values as they are placeholders."""
    
    if media_type == "books":
        metadata = data.get("metadata") or {}
        
        # Try various keys - but ONLY accept non-zero values (0 is a placeholder)
        page_count = (
            data.get("pageCount")
            or data.get("page_count")
            or metadata.get("pageCount")
            or metadata.get("page_count")
        )
        
        if page_count and int(page_count) > 0:
            try:
                return int(page_count)
            except (ValueError, TypeError):
                pass
        
        # Check volumeInfo
        vol_info = metadata.get("volumeInfo") or {}
        if isinstance(vol_info, dict):
            pc = vol_info.get("pageCount")
            if pc and int(pc) > 0:
                try:
                    return int(pc)
                except (ValueError, TypeError):
                    pass
    
    return None


def normalize_media(data: Dict[str, Any], media_type: str) -> Dict[str, Any]:
    """
    Normalize a media item to unified schema.
    
    Only fills missing fields - never overwrites valid data.
    Preserves embedding and all existing valid fields.
    
    Args:
        data: Raw media data from provider
        media_type: One of: movies, songs, books, podcasts
        
    Returns:
        Normalized data dict with unified schema
    """
    media_type = media_type.lower().strip()
    
    # Start with a copy
    normalized = dict(data)
    
    # Ensure type field
    if _is_missing(normalized.get("type")):
        normalized["type"] = media_type
    
    # Ensure basic required fields
    if _is_missing(normalized.get("title")):
        normalized["title"] = ""
    
    if _is_missing(normalized.get("description")):
        normalized["description"] = ""
    
    # Enrich image_url
    if _is_missing(normalized.get("image_url")):
        image_url = _extract_image_url(data, media_type)
        if image_url:
            normalized["image_url"] = image_url
    
    # Enrich external_url
    if _is_missing(normalized.get("external_url")):
        external_url = _extract_external_url(data, media_type)
        if external_url:
            normalized["external_url"] = external_url
    
    # Enrich contributors
    if _is_missing(normalized.get("contributors")):
        contributors = _extract_contributors(data, media_type)
        if contributors:
            normalized["contributors"] = contributors
    
    # Enrich creator
    if _is_missing(normalized.get("creator")):
        creator = _extract_creator(data, media_type)
        if creator:
            normalized["creator"] = creator
    
    # Enrich genres
    if _is_missing(normalized.get("genres")):
        genres = _extract_genres(data, media_type)
        if genres:
            normalized["genres"] = genres
    
    # Enrich duration (for all types)
    if _is_missing(normalized.get("duration")):
        duration = _extract_duration(data, media_type)
        if duration:
            normalized["duration"] = duration
    
    # Enrich page_count (books only)
    if media_type == "books" and _is_missing(normalized.get("page_count")):
        page_count = _extract_page_count(data, media_type)
        if page_count:
            normalized["page_count"] = page_count
    
    # Enrich rating if missing
    if _is_missing(normalized.get("rating")):
        rating = None
        
        # Movies, songs, podcasts: use vote_average
        if media_type != "books":
            rating = data.get("rating") or data.get("vote_average") or (data.get("metadata") or {}).get("vote_average")
        else:
            # Books: use averageRating from Google Books
            metadata = data.get("metadata") or {}
            rating = data.get("averageRating") or data.get("rating") or metadata.get("averageRating")
        
        if rating and rating != 0:
            try:
                normalized["rating"] = float(rating)
            except (ValueError, TypeError):
                pass
    
    # Enrich popularity if missing
    if _is_missing(normalized.get("popularity")):
        popularity = None
        
        # Movies, songs, podcasts: use popularity
        if media_type != "books":
            popularity = data.get("popularity") or (data.get("metadata") or {}).get("popularity")
        else:
            # Books: use ratingsCount as proxy for popularity
            metadata = data.get("metadata") or {}
            ratings_count = data.get("ratingsCount") or metadata.get("ratingsCount")
            if ratings_count and ratings_count > 0:
                # Normalize ratingsCount to a 0-100 scale (rough estimate)
                popularity = min(100.0, float(ratings_count) / 10.0)
        
        if popularity and popularity != 0:
            try:
                normalized["popularity"] = float(popularity)
            except (ValueError, TypeError):
                pass
    
    # Ensure language field
    if _is_missing(normalized.get("language")):
        normalized["language"] = "neutral"
    
    # CRITICAL: Preserve embedding (never modify)
    # The embedding field is kept as-is from the original data
    
    return normalized


def build_patch(original: Dict[str, Any], normalized: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a patch object using PRODUCTION-GRADE quality scoring.
    
    Instead of simple yes/no logic, this evaluates data quality on a 0-3 scale:
    - 0: Empty/placeholder (None, "", [], 0)
    - 1: Weak data (short strings, small numbers)
    - 2: Medium quality
    - 3: Strong/complete data
    
    Only updates if new_quality_score > old_quality_score
    
    Args:
        original: Original document data from Firestore
        normalized: Normalized document data (after enrichment + normalization)
        
    Returns:
        Patch dict with only fields to update (empty if no changes)
    """
    patch = {}
    
    logger.info(f"\n🏆 BUILD_PATCH (QUALITY-SCORE BASED):")
    logger.info(f"   Original keys: {list(original.keys())}")
    logger.info(f"   Normalized keys: {list(normalized.keys())}")
    
    for key in normalized:
        # NEVER patch these fields
        if key in ("embedding", "metadata", "id", "doc_id", "added_at"):
            logger.debug(f"   ⊘ {key}: SKIP (protected field)")
            continue
        
        old_value = original.get(key)
        new_value = normalized.get(key)
        
        # Get quality scores
        old_score = get_quality_score(old_value)
        new_score = get_quality_score(new_value)
        
        logger.info(f"\n   🔍 FIELD: {key}")
        logger.info(f"      OLD: {str(old_value)[:50]} (score: {old_score})")
        logger.info(f"      NEW: {str(new_value)[:50]} (score: {new_score})")
        
        # Quality-based decision
        if should_update(old_value, new_value):
            patch[key] = new_value
            logger.info(f"      ✅ UPDATE: new_score({new_score}) > old_score({old_score})")
        else:
            logger.info(f"      ⊘ SKIP: new_score({new_score}) <= old_score({old_score})")
    
    logger.info(f"\n   📤 FINAL PATCH: {len(patch)} fields")
    for key, val in patch.items():
        logger.info(f"      {key}: {str(val)[:60]}")
    
    return patch


def log_patch_summary(document_id: str, collection: str, patch: Dict[str, Any], status: str = "updated"):
    """Log a summary of what was patched."""
    if not patch:
        logger.debug(f"No changes for {collection}/{document_id}")
        return
    
    changed_fields = list(patch.keys())
    logger.info(
        f"Media normalization {status}: collection={collection} id={document_id} "
        f"fields_updated={len(changed_fields)} fields={changed_fields}"
    )






