"""
Preferences service for managing user media preferences.

Supports both legacy and new preference formats with automatic normalization.
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger()

# Valid media types
VALID_MEDIA_TYPES = {"movies", "songs", "books", "podcasts"}

# Valid genres per media type (optional whitelist)
VALID_GENRES = {
    "movies": [
        "Action", "Adventure", "Animation", "Comedy", "Crime", "Documentary",
        "Drama", "Family", "Fantasy", "History", "Horror", "Music", "Mystery",
        "Romance", "Science Fiction", "Thriller", "War", "Western"
    ],
    "songs": [
        "Pop", "Rock", "Hip-Hop", "Rap", "R&B", "Soul", "Country", "Folk",
        "Jazz", "Blues", "Classical", "Electronic", "EDM", "Indie", "Metal",
        "Alternative", "Dance", "Latin", "Reggae", "K-Pop", "J-Pop"
    ],
    "books": [
        "Fiction", "Mystery", "Thriller", "Romance", "Science Fiction",
        "Fantasy", "Biography", "History", "Self-Help", "Poetry", "Drama",
        "Adventure", "Horror", "Young Adult", "Children's", "Graphic Novel"
    ],
    "podcasts": [
        "True Crime", "News", "Education", "Comedy", "Drama", "Sports",
        "Business", "Technology", "Science", "Health", "Interview",
        "Society", "Self-Help", "Entertainment"
    ]
}

# Valid content intensity values
VALID_CONTENT_INTENSITY = ["light", "moderate", "heavy"]

# Valid languages
VALID_LANGUAGES = [
    "english", "spanish", "french", "german", "italian", "portuguese",
    "russian", "chinese", "japanese", "korean", "hindi", "arabic"
]


def normalize_preferences(raw_prefs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize user preferences from legacy or new format into standard structure.
    
    Legacy format:
    {
        "music": [...],
        "movies": [...],
        "books": [...],
        "languages": [...]
    }
    
    New format:
    {
        "preferred_media_types": [...],
        "genres": {
            "movies": [...],
            "music": [...],
            "books": [...],
            "podcasts": [...]
        },
        "filters": {
            "languages": [...],
            "content_intensity": "..."
        }
    }
    
    Args:
        raw_prefs: Raw preference dictionary
        
    Returns:
        Normalized preference dictionary
    """
    if not raw_prefs or not isinstance(raw_prefs, dict):
        return get_default_preferences()
    
    # Detect format and normalize
    if "preferred_media_types" in raw_prefs or "genres" in raw_prefs:
        # Already new format or mixed
        return _normalize_new_format(raw_prefs)
    else:
        # Legacy format
        return _normalize_legacy_format(raw_prefs)


def _normalize_legacy_format(legacy: Dict[str, Any]) -> Dict[str, Any]:
    """Convert legacy format to new format."""
    genres = {}
    
    # Map legacy keys to new structure
    if "music" in legacy and legacy["music"]:
        genres["music"] = legacy["music"] if isinstance(legacy["music"], list) else []
    if "movies" in legacy and legacy["movies"]:
        genres["movies"] = legacy["movies"] if isinstance(legacy["movies"], list) else []
    if "books" in legacy and legacy["books"]:
        genres["books"] = legacy["books"] if isinstance(legacy["books"], list) else []
    if "podcasts" in legacy and legacy["podcasts"]:
        genres["podcasts"] = legacy["podcasts"] if isinstance(legacy["podcasts"], list) else []
    
    languages = []
    if "languages" in legacy and legacy["languages"]:
        languages = legacy["languages"] if isinstance(legacy["languages"], list) else []
    
    content_intensity = legacy.get("content_intensity", "moderate") if isinstance(legacy.get("content_intensity"), str) else "moderate"
    
    return {
        "preferred_media_types": list(genres.keys()) if genres else [],
        "genres": genres,
        "filters": {
            "languages": languages,
            "content_intensity": content_intensity
        }
    }


def _normalize_new_format(new_prefs: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure new format has all required fields."""
    genres = new_prefs.get("genres", {})
    if not isinstance(genres, dict):
        genres = {}
    
    filters = new_prefs.get("filters", {})
    if not isinstance(filters, dict):
        filters = {}
    
    preferred_types = new_prefs.get("preferred_media_types", [])
    if not isinstance(preferred_types, list):
        preferred_types = list(genres.keys()) if genres else []
    
    return {
        "preferred_media_types": preferred_types,
        "genres": genres,
        "filters": {
            "languages": filters.get("languages", []) if isinstance(filters.get("languages"), list) else [],
            "content_intensity": filters.get("content_intensity", "moderate")
        }
    }


def get_default_preferences() -> Dict[str, Any]:
    """Get default preferences structure."""
    return {
        "preferred_media_types": [],
        "genres": {
            "movies": [],
            "music": [],
            "books": [],
            "podcasts": []
        },
        "filters": {
            "languages": ["english"],
            "content_intensity": "moderate"
        }
    }


def validate_preferences(prefs: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate user preferences.
    
    Args:
        prefs: Preference dictionary to validate
        
    Returns:
        (is_valid, error_message)
    """
    if not isinstance(prefs, dict):
        return False, "Preferences must be a dictionary"
    
    # Validate preferred_media_types
    media_types = prefs.get("preferred_media_types", [])
    if not isinstance(media_types, list):
        return False, "preferred_media_types must be a list"
    
    for mt in media_types:
        if mt not in VALID_MEDIA_TYPES and mt != "music":  # "music" is also accepted
            return False, f"Invalid media type: {mt}. Must be one of {VALID_MEDIA_TYPES}"
    
    # Validate genres
    genres = prefs.get("genres", {})
    if not isinstance(genres, dict):
        return False, "genres must be a dictionary"
    
    for media_type, genre_list in genres.items():
        if not isinstance(genre_list, list):
            return False, f"genres[{media_type}] must be a list"
        
        # Optional: validate genre names if whitelist is strict
        # For now, allow any genre strings (flexible approach)
        for genre in genre_list:
            if not isinstance(genre, str):
                return False, f"Genre must be string, got {type(genre)}"
    
    # Validate filters
    filters = prefs.get("filters", {})
    if not isinstance(filters, dict):
        return False, "filters must be a dictionary"
    
    languages = filters.get("languages", [])
    if not isinstance(languages, list):
        return False, "filters.languages must be a list"
    
    content_intensity = filters.get("content_intensity", "moderate")
    if not isinstance(content_intensity, str) or content_intensity not in VALID_CONTENT_INTENSITY:
        return False, f"content_intensity must be one of {VALID_CONTENT_INTENSITY}"
    
    return True, None


def get_user_preferences(user_doc_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and normalize preferences from user document.
    
    Args:
        user_doc_dict: User document as dictionary
        
    Returns:
        Normalized preferences
    """
    raw_prefs = user_doc_dict.get("preferences", {})
    return normalize_preferences(raw_prefs)


def filter_candidates_by_preferences(
    candidates: List[Dict[str, Any]],
    prefs: Dict[str, Any],
    media_type: str
) -> List[Dict[str, Any]]:
    """
    Apply user preferences as filters to media candidates.
    
    Args:
        candidates: List of media items
        prefs: User preferences
        media_type: Type of media (movies, songs, books, podcasts)
        
    Returns:
        Filtered candidates
    """
    if not prefs:
        return candidates
    
    filtered = candidates
    
    # Filter by content intensity if specified
    content_intensity = prefs.get("filters", {}).get("content_intensity")
    if content_intensity and content_intensity != "moderate":  # "moderate" is default/no-filter
        # This would need to be mapped to actual content metadata
        # For now, keep all (can be extended based on actual data model)
        pass
    
    # Filter by languages if specified
    preferred_languages = prefs.get("filters", {}).get("languages", [])
    if preferred_languages:
        filtered = [
            item for item in filtered
            if (item.get("language", "english").lower() in [l.lower() for l in preferred_languages])
               or (item.get("language") is None)  # Keep items without language info
        ]
    
    return filtered

