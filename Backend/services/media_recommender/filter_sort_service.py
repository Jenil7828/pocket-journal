"""
Enhanced Media Filtering and Sorting Service

Provides reusable filtering, sorting, searching, and pagination logic
for media recommendations without modifying existing recommendation pipeline.

This layer sits between the recommendation engine and response formatting.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger("pocket_journal.media.filter_sort_service")


class MediaFilterSortService:
    """Filter, sort, search, and paginate media items in-memory."""

    def __init__(self):
        """Initialize the filter/sort service."""
        pass

    @staticmethod
    def filter_by_type(items: List[Dict[str, Any]], media_type: str) -> List[Dict[str, Any]]:
        """Filter items by media type (movies, songs, books, podcasts)."""
        if not media_type or media_type.lower() == "all":
            return items
        
        media_type_lower = media_type.lower()
        # Normalize type strings for comparison
        type_map = {
            "movie": ["movie"],
            "movies": ["movie"],
            "song": ["song", "track"],
            "songs": ["song", "track"],
            "book": ["book"],
            "books": ["book"],
            "podcast": ["podcast", "episode"],
            "podcasts": ["podcast", "episode"],
        }
        
        acceptable_types = type_map.get(media_type_lower, [media_type_lower])
        
        return [
            item for item in items
            if item.get("type", "").lower() in acceptable_types
        ]

    @staticmethod
    def filter_by_genre(items: List[Dict[str, Any]], genre: str) -> List[Dict[str, Any]]:
        """Filter items by genre (case-insensitive, partial match allowed)."""
        if not genre:
            return items
        
        genre_lower = genre.lower().strip()
        filtered = []
        
        for item in items:
            genres = item.get("genres") or []
            if isinstance(genres, str):
                genres = [genres]
            
            # Check if any genre matches (case-insensitive, partial match)
            if any(genre_lower in g.lower() for g in genres if isinstance(g, str)):
                filtered.append(item)
        
        return filtered

    @staticmethod
    def filter_by_mood(items: List[Dict[str, Any]], mood: str) -> List[Dict[str, Any]]:
        """Filter items by mood tag."""
        if not mood:
            return items
        
        mood_lower = mood.lower().strip()
        filtered = []
        
        for item in items:
            # Check mood_tag field (if populated by recommendation service)
            mood_tag = item.get("mood_tag", "").lower()
            if mood_lower in mood_tag:
                filtered.append(item)
            else:
                # Fallback: check if mood is inferred from genre
                genres = item.get("genres") or []
                if isinstance(genres, str):
                    genres = [genres]
                genres_str = " ".join(str(g).lower() for g in genres)
                if mood_lower in genres_str:
                    filtered.append(item)
        
        return filtered

    @staticmethod
    def search(items: List[Dict[str, Any]], search_query: str) -> List[Dict[str, Any]]:
        """Search items by title or description (case-insensitive)."""
        if not search_query:
            return items
        
        search_lower = search_query.lower().strip()
        filtered = []
        
        for item in items:
            title = item.get("title", "").lower()
            description = item.get("description", "").lower()
            
            if search_lower in title or search_lower in description:
                filtered.append(item)
        
        return filtered

    @staticmethod
    def sort_items(
        items: List[Dict[str, Any]],
        sort_by: str = "default",
        is_favorite_map: Optional[Dict[str, bool]] = None,
    ) -> List[Dict[str, Any]]:
        """Sort items by rating, trending (popularity), or favorites."""
        if not sort_by or sort_by == "default":
            return items
        
        sort_by_lower = sort_by.lower()
        
        if sort_by_lower == "rating":
            # Sort by rating descending (highest first)
            return sorted(
                items,
                key=lambda x: (x.get("rating") or 0, x.get("score") or 0),
                reverse=True
            )
        
        elif sort_by_lower == "trending":
            # Sort by popularity descending (highest first)
            return sorted(
                items,
                key=lambda x: x.get("popularity") or 0,
                reverse=True
            )
        
        elif sort_by_lower == "favorites":
            # Sort: favorites first, then by original order
            if not is_favorite_map:
                return items
            
            def favorite_sort_key(item):
                item_id = item.get("id")
                is_fav = is_favorite_map.get(item_id, False)
                return (not is_fav, 0)  # Favorites (True) sort before non-favorites (False)
            
            return sorted(items, key=favorite_sort_key)
        
        else:
            logger.warning(f"Unknown sort_by value: {sort_by}, returning unsorted")
            return items

    @staticmethod
    def paginate(
        items: List[Dict[str, Any]],
        offset: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Paginate items.
        
        Returns:
            (paginated_items, total_count, returned_count)
        """
        if offset < 0:
            offset = 0
        if limit < 1:
            limit = 1
        if limit > 100:
            limit = 100
        
        total_count = len(items)
        paginated = items[offset : offset + limit]
        returned_count = len(paginated)
        
        return paginated, total_count, returned_count

    @staticmethod
    def apply_all_filters(
        items: List[Dict[str, Any]],
        media_type: Optional[str] = None,
        genre: Optional[str] = None,
        mood: Optional[str] = None,
        search_query: Optional[str] = None,
        sort_by: str = "default",
        offset: int = 0,
        limit: int = 20,
        is_favorite_map: Optional[Dict[str, bool]] = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Apply all filters, sorting, and pagination in sequence.
        
        Returns:
            (filtered_paginated_items, metadata)
        """
        # Phase 1: Filtering (type, genre, mood, search)
        filtered_items = items
        
        if media_type:
            filtered_items = MediaFilterSortService.filter_by_type(filtered_items, media_type)
        
        if genre:
            filtered_items = MediaFilterSortService.filter_by_genre(filtered_items, genre)
        
        if mood:
            filtered_items = MediaFilterSortService.filter_by_mood(filtered_items, mood)
        
        if search_query:
            filtered_items = MediaFilterSortService.search(filtered_items, search_query)
        
        # Phase 2: Sorting
        sorted_items = MediaFilterSortService.sort_items(
            filtered_items,
            sort_by=sort_by,
            is_favorite_map=is_favorite_map,
        )
        
        # Phase 3: Pagination
        paginated_items, total_count, returned_count = MediaFilterSortService.paginate(
            sorted_items,
            offset=offset,
            limit=limit,
        )
        
        metadata = {
            "total_count": total_count,
            "returned_count": returned_count,
            "offset": offset,
            "limit": limit,
            "filters_applied": {
                "type": media_type,
                "genre": genre,
                "mood": mood,
                "search": search_query,
                "sort": sort_by,
            }
        }
        
        return paginated_items, metadata


def transform_to_ui_format(item: Dict[str, Any], is_favorite: bool = False) -> Dict[str, Any]:
    """Transform item to UI-ready format with additional metadata."""
    return {
        # Core fields (required for UI rendering)
        "id": item.get("id"),
        "type": item.get("type", "unknown"),
        "title": item.get("title"),
        "description": item.get("description"),
        "year": item.get("release_date"),
        "genre": item.get("genres") or [],
        "image_url": item.get("image_url"),
        "external_url": item.get("external_url"),
        "rating": item.get("rating"),
        "popularity": item.get("popularity"),
        "mood_tag": item.get("mood_tag"),
        "is_favorite": is_favorite,
        
        # Optional extended fields (for advanced UI)
        "added_at": item.get("added_at"),
        "duration": item.get("duration"),
        "contributors": item.get("contributors"),
        "score": item.get("score"),
    }

