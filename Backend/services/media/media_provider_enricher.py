"""
Provider Enrichment Layer

Fetches missing media fields from external providers (TMDb, Google Books, Spotify).
Only updates missing/null/empty fields. Never overwrites valid data.

CRITICAL RULES:
- Only fetch if field is missing
- Never overwrite existing valid data
- Rate limit to avoid provider throttling
- Handle provider errors gracefully
- Do NOT modify embeddings
"""

import logging
import time
import os
from typing import Dict, List, Any, Optional

logger = logging.getLogger("pocket_journal.media.enricher")

# Rate limiting: delay between API calls
API_CALL_DELAY = 0.2  # seconds


def _is_missing(value: Any) -> bool:
    """Check if a value is considered missing."""
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if isinstance(value, (list, dict)) and len(value) == 0:
        return True
    return False


class TMDbEnricher:
    """Fetch missing movie data from TMDb API."""
    
    def __init__(self):
        self.api_key = os.getenv("TMDB_API_KEY")
        if not self.api_key:
            logger.warning("TMDB_API_KEY not set - movie enrichment disabled")
            self.api_key = None
    
    def fetch_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """Search for movie by title and fetch full details."""
        if not self.api_key or not title:
            return None
        
        try:
            import requests
            
            # Search for movie
            search_url = "https://api.themoviedb.org/3/search/movie"
            search_params = {
                "api_key": self.api_key,
                "query": title,
                "language": "en-US",
            }
            
            time.sleep(API_CALL_DELAY)
            search_resp = requests.get(search_url, params=search_params, timeout=5)
            search_resp.raise_for_status()
            search_data = search_resp.json()
            
            results = search_data.get("results", [])
            if not results:
                logger.debug(f"TMDb: No results for movie '{title}'")
                return None
            
            # Get first result (most likely match)
            best_match = results[0]
            movie_id = best_match.get("id")
            
            if not movie_id:
                return None
            
            # Fetch full movie details with credits
            details_url = f"https://api.themoviedb.org/3/movie/{movie_id}"
            details_params = {
                "api_key": self.api_key,
                "language": "en-US",
                "append_to_response": "credits",
            }
            
            time.sleep(API_CALL_DELAY)
            details_resp = requests.get(details_url, params=details_params, timeout=5)
            details_resp.raise_for_status()
            movie_data = details_resp.json()
            
            return self._extract_fields(movie_data)
        
        except Exception as e:
            logger.error(f"TMDb enrichment failed for '{title}': {e}")
            return None
    
    def _extract_fields(self, movie_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract enriched fields from TMDb movie data."""
        extracted = {}
        
        # Image URL
        if movie_data.get("poster_path"):
            extracted["image_url"] = f"https://image.tmdb.org/t/p/w500{movie_data['poster_path']}"
        
        # External URL
        if movie_id := movie_data.get("id"):
            extracted["external_url"] = f"https://www.themoviedb.org/movie/{movie_id}"
        
        # Duration (runtime in minutes -> convert to seconds)
        if runtime := movie_data.get("runtime"):
            extracted["duration"] = int(runtime) * 60
        
        # Genres
        genres = []
        for genre in movie_data.get("genres", []):
            if isinstance(genre, dict) and (name := genre.get("name")):
                genres.append(name)
        if genres:
            extracted["genres"] = genres
        
        # Contributors (cast)
        contributors = []
        credits = movie_data.get("credits", {})
        if isinstance(credits, dict):
            cast = credits.get("cast", [])
            for actor in cast[:5]:  # Top 5 actors
                if isinstance(actor, dict) and (name := actor.get("name")):
                    contributors.append(name)
        if contributors:
            extracted["contributors"] = contributors
        
        # Creator (director)
        if credits := movie_data.get("credits", {}):
            crew = credits.get("crew", [])
            for person in crew:
                if isinstance(person, dict) and person.get("job") == "Director":
                    if name := person.get("name"):
                        extracted["creator"] = name
                        break
        
        return extracted


class GoogleBooksEnricher:
    """Fetch missing book data from Google Books API."""
    
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_BOOKS_API_KEY")
    
    def fetch_by_title(self, title: str, author: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Search for book by title and optional author."""
        if not title:
            return None
        
        try:
            import requests
            
            # Build search query
            query = title
            if author:
                query = f"{query} author:{author}"
            
            search_url = "https://www.googleapis.com/books/v1/volumes"
            search_params = {
                "q": query,
                "maxResults": 5,
            }
            if self.api_key:
                search_params["key"] = self.api_key
            
            time.sleep(API_CALL_DELAY)
            search_resp = requests.get(search_url, params=search_params, timeout=5)
            search_resp.raise_for_status()
            search_data = search_resp.json()
            
            items = search_data.get("items", [])
            if not items:
                logger.debug(f"Google Books: No results for book '{title}'")
                return None
            
            # Get first result (most likely match)
            best_match = items[0]
            vol_info = best_match.get("volumeInfo", {})
            
            return self._extract_fields(vol_info, best_match)
        
        except Exception as e:
            logger.error(f"Google Books enrichment failed for '{title}': {e}")
            return None
    
    def _extract_fields(self, vol_info: Dict[str, Any], book_item: Dict[str, Any]) -> Dict[str, Any]:
        """Extract enriched fields from Google Books data."""
        extracted = {}
        
        # Image URL
        image_links = vol_info.get("imageLinks", {})
        if isinstance(image_links, dict):
            if img_url := image_links.get("thumbnail"):
                extracted["image_url"] = img_url
        
        # External URL
        if external_url := book_item.get("volumeInfo", {}).get("infoLink"):
            extracted["external_url"] = external_url
        
        # Page count
        if page_count := vol_info.get("pageCount"):
            extracted["page_count"] = int(page_count)
        
        # Published date
        if pub_date := vol_info.get("publishedDate"):
            extracted["release_date"] = pub_date
        
        # Contributors (authors)
        authors = vol_info.get("authors", [])
        if isinstance(authors, list):
            extracted["contributors"] = [str(a) for a in authors]
        
        # Creator (first author)
        if authors and len(authors) > 0:
            extracted["creator"] = str(authors[0])
        
        # Genres (categories)
        categories = vol_info.get("categories", [])
        if isinstance(categories, list):
            extracted["genres"] = [str(c) for c in categories]
        
        return extracted


class SpotifyEnricher:
    """Enrich song data (no API calls, use fallback strategies)."""
    
    def enrich_song(self, title: str, artist: Optional[str] = None) -> Dict[str, Any]:
        """Generate enrichment data for song using fallback strategies."""
        extracted = {}
        
        # For songs, create YouTube search URL as external_url if missing
        if title:
            query = title
            if artist:
                query = f"{query} {artist}"
            
            # YouTube search URL
            query_encoded = query.replace(" ", "+")
            extracted["external_url"] = f"https://www.youtube.com/results?search_query={query_encoded}"
        
        return extracted


def enrich_from_providers(data: Dict[str, Any], media_type: str) -> Dict[str, Any]:
    """
    Enrich media data by fetching missing fields from providers.
    
    Only updates missing/null/empty fields.
    Never overwrites existing valid data.
    
    CRITICAL: Returns enriched data with ALL provider fields included.
    The enriched data MUST flow through to normalization and patching.
    
    Args:
        data: Original media data
        media_type: "movies", "songs", "books", or "podcasts"
        
    Returns:
        Enriched data dict with provider fields added where missing
    """
    enriched = dict(data)
    title = data.get("title", "")
    fields_added = []
    
    if media_type == "movies":
        critical_fields = ["image_url", "external_url", "duration", "genres", "contributors"]
        missing = [f for f in critical_fields if _is_missing(enriched.get(f))]
        
        if missing and title:
            logger.info(f"📡 TMDb enrichment for movie '{title}': fetching {missing}")
            tmdb = TMDbEnricher()
            provider_data = tmdb.fetch_by_title(title)
            
            if provider_data:
                logger.debug(f"   Provider returned: {list(provider_data.keys())}")
                for key, value in provider_data.items():
                    if _is_missing(enriched.get(key)):
                        enriched[key] = value
                        fields_added.append(key)
                        logger.info(f"   ✓ Added {key} from TMDb")
                    else:
                        logger.debug(f"   ⊘ {key}: Already in data, skipping")
            else:
                logger.warning(f"   ⚠️  No data returned from TMDb")
    
    elif media_type == "books":
        critical_fields = ["image_url", "external_url", "page_count", "contributors"]
        missing = [f for f in critical_fields if _is_missing(enriched.get(f))]
        
        if missing and title:
            author = enriched.get("author") or enriched.get("creator")
            logger.info(f"📡 Google Books enrichment for book '{title}': fetching {missing}")
            books = GoogleBooksEnricher()
            provider_data = books.fetch_by_title(title, author=author)
            
            if provider_data:
                logger.debug(f"   Provider returned: {list(provider_data.keys())}")
                for key, value in provider_data.items():
                    if _is_missing(enriched.get(key)):
                        enriched[key] = value
                        fields_added.append(key)
                        logger.info(f"   ✓ Added {key} from Google Books")
                    else:
                        logger.debug(f"   ⊘ {key}: Already in data, skipping")
            else:
                logger.warning(f"   ⚠️  No data returned from Google Books")
    
    elif media_type == "songs":
        critical_fields = ["external_url"]
        missing = [f for f in critical_fields if _is_missing(enriched.get(f))]
        
        if missing and title:
            logger.info(f"📡 Spotify enrichment for song '{title}': using fallback strategies")
            spotify = SpotifyEnricher()
            artist = enriched.get("artist") or enriched.get("creator")
            provider_data = spotify.enrich_song(title, artist=artist)
            
            if provider_data:
                logger.debug(f"   Provider returned: {list(provider_data.keys())}")
                for key, value in provider_data.items():
                    if _is_missing(enriched.get(key)):
                        enriched[key] = value
                        fields_added.append(key)
                        logger.info(f"   ✓ Added {key} from Spotify fallback")
                    else:
                        logger.debug(f"   ⊘ {key}: Already in data, skipping")
            else:
                logger.warning(f"   ⚠️  No data returned from Spotify fallback")
    
    elif media_type == "podcasts":
        # For podcasts, use existing provider if available
        logger.debug(f"Podcast '{title}': using existing provider data")
    
    if fields_added:
        logger.info(f"✅ Enrichment added {len(fields_added)} fields: {fields_added}")
    else:
        logger.debug(f"No new fields added (already complete or no provider match)")
    
    return enriched


def should_enrich(data: Dict[str, Any], media_type: str) -> bool:
    """Check if document should be enriched from providers."""
    # Define critical fields per type
    critical = {
        "movies": ["image_url", "external_url"],
        "books": ["image_url", "external_url", "page_count"],
        "songs": ["external_url"],
        "podcasts": [],
    }
    
    fields = critical.get(media_type, [])
    
    # Check if any critical field is missing
    for field in fields:
        if _is_missing(data.get(field)):
            return True
    
    return False


