"""
Unified Media Response Formatter

Ensures all API responses (search, recommendation, cache) follow a single schema.
Removes internal fields and applies consistent normalization.
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger()

# Define the canonical response schema
CANONICAL_MEDIA_SCHEMA = {
    "id",
    "title",
    "description",
    "type",
    "image_url",
    "release_date",
    "rating",
    "duration",
    "genres",
    "contributors",
    "creator",
    "external_url",
    "language",
    "popularity",
    "added_at",
    "page_count",  # books only
}

# Fields that should NEVER appear in API responses
INTERNAL_ONLY_FIELDS = {
    "ranking_info",
    "score",
    "phase",
    "hybrid_used",
    "mmr_used",
    "embedding",
    "_embedding",
    "metadata",
    "similarity",
}


def normalize_response_item(item: Dict[str, Any], media_type: str) -> Dict[str, Any]:
    """
    Normalize a single media item for API response.
    
    - Only includes fields in CANONICAL_MEDIA_SCHEMA
    - Removes all internal fields
    - Applies type-specific formatting
    - Ensures all required fields exist
    
    Args:
        item: Raw item from pipeline/search/cache
        media_type: One of: movies, songs, books, podcasts
        
    Returns:
        Normalized item safe for API response
    """
    normalized = {}
    media_type = media_type.lower().strip()
    
    # Copy canonical fields only
    for field in CANONICAL_MEDIA_SCHEMA:
        value = item.get(field)
        if value is not None:
            # Special handling for certain fields
            if field == "rating":
                # Ensure rating is numeric
                try:
                    normalized[field] = float(value) if value else None
                except (ValueError, TypeError):
                    normalized[field] = None
            elif field == "popularity":
                # Ensure popularity is numeric
                try:
                    normalized[field] = float(value) if value else None
                except (ValueError, TypeError):
                    normalized[field] = None
            elif field == "duration":
                # Ensure duration is numeric
                try:
                    normalized[field] = int(value) if value else None
                except (ValueError, TypeError):
                    normalized[field] = None
            elif field == "genres":
                # Ensure genres is a list
                if isinstance(value, list):
                    normalized[field] = value
                elif isinstance(value, str):
                    normalized[field] = [value] if value else []
                else:
                    normalized[field] = []
            elif field == "contributors":
                # Ensure contributors is a list
                if isinstance(value, list):
                    normalized[field] = value
                else:
                    normalized[field] = []
            else:
                normalized[field] = value
    
    # Ensure type field
    if "type" not in normalized or not normalized.get("type"):
        normalized["type"] = media_type
    
    # Ensure all required fields exist (even if empty)
    defaults = {
        "id": "",
        "title": "",
        "description": "",
        "type": media_type,
        "image_url": None,
        "release_date": None,
        "rating": None,
        "duration": None,
        "genres": [],
        "contributors": [],
        "creator": None,
        "external_url": None,
        "language": "neutral",
        "popularity": None,
        "added_at": None,
    }
    
    # Fill in missing fields with defaults
    for field, default_value in defaults.items():
        if field not in normalized:
            normalized[field] = default_value
    
    # Remove fields that shouldn't be in response
    for internal_field in INTERNAL_ONLY_FIELDS:
        normalized.pop(internal_field, None)
    
    return normalized


def normalize_response_list(items: List[Dict[str, Any]], media_type: str) -> List[Dict[str, Any]]:
    """
    Normalize a list of media items for API response.
    
    Args:
        items: List of items to normalize
        media_type: One of: movies, songs, books, podcasts
        
    Returns:
        List of normalized items
    """
    return [normalize_response_item(item, media_type) for item in items]


def format_search_response(
    results: List[Dict[str, Any]],
    media_type: str,
    query: str,
    limit: int,
    metrics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Format search API response with unified schema.
    
    Args:
        results: Search results from provider
        media_type: One of: movies, songs, books, podcasts
        query: Search query used
        limit: Limit applied
        metrics: Optional metrics dict
        
    Returns:
        Formatted response dict
    """
    normalized_results = normalize_response_list(results, media_type)
    
    return {
        "results": normalized_results,
        "metrics": {
            "query": query,
            "media_type": media_type,
            "limit": limit,
            "returned": len(normalized_results),
            **(metrics or {}),
        }
    }


def format_recommendation_response(
    results: List[Dict[str, Any]],
    media_type: str,
    total: int,
    offset: int,
    limit: int,
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Format recommendation API response with unified schema.
    
    Args:
        results: Recommendation results
        media_type: One of: movies, songs, books, podcasts
        total: Total count after filtering
        offset: Offset used
        limit: Limit used
        filters: Optional applied filters
        
    Returns:
        Formatted response dict
    """
    normalized_results = normalize_response_list(results, media_type)
    
    return {
        "results": normalized_results,
        "metrics": {
            "media_type": media_type,
            "total": total,
            "returned": len(normalized_results),
            "offset": offset,
            "limit": limit,
            "filters": filters or {},
        }
    }


def strip_internal_fields(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove internal fields from an item.
    
    Args:
        item: Item to clean
        
    Returns:
        Item without internal fields
    """
    cleaned = dict(item)
    for field in INTERNAL_ONLY_FIELDS:
        cleaned.pop(field, None)
    return cleaned


def strip_internal_fields_list(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove internal fields from a list of items.
    
    Args:
        items: Items to clean
        
    Returns:
        Items without internal fields
    """
    return [strip_internal_fields(item) for item in items]

