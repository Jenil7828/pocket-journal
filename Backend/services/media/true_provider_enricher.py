"""
TRUE PROVIDER ENRICHMENT - FORCES EXTERNAL API CALLS

This module ACTUALLY calls external providers (TMDb, Google Books) to fill
missing media data. No silent skipping. No relying on existing metadata alone.

CRITICAL: If this doesn't call the API, it's broken.
"""

import logging
import time
import os
import requests
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger("pocket_journal.true_enrichment")

# Rate limiting between API calls
API_RATE_LIMIT = 0.25  # seconds


def needs_enrichment(doc: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Check if document ACTUALLY needs enrichment.
    
    Returns: (needs_enrichment: bool, missing_fields: List[str])
    """
    missing = []
    
    # Movies need these fields
    if not doc.get("image_url"):
        missing.append("image_url")
    if not doc.get("external_url"):
        missing.append("external_url")
    if not doc.get("rating") or doc.get("rating", 0) == 0:
        missing.append("rating")
    if not doc.get("duration_ms") and not doc.get("duration") and doc.get("duration", 0) == 0:
        missing.append("duration")
    if not doc.get("genres") or len(doc.get("genres", [])) == 0:
        missing.append("genres")
    if not doc.get("contributors") or len(doc.get("contributors", [])) == 0:
        missing.append("contributors")
    
    return len(missing) > 0, missing


class TMDbAPIEnricher:
    """
    FULL TMDb PIPELINE - Mandatory two-step enrichment.
    
    STEP 1: Search by title
      → GET /search/movie?query={title}
      → Extract: id, title, vote_average, popularity, release_date, poster_path
    
    STEP 2: Fetch full details with credits
      → GET /movie/{id}?append_to_response=credits
      → Extract: runtime, genres, cast, crew (Director), homepage
    
    This WILL make TWO API calls per movie.
    """
    
    def __init__(self):
        self.api_key = os.getenv("TMDB_API_KEY")
        if not self.api_key:
            logger.error("❌ TMDB_API_KEY NOT SET - API ENRICHMENT DISABLED")
            logger.error("❌ Cannot enrich movies without API key")
            self.enabled = False
        else:
            self.enabled = True
            logger.info(f"✅ TMDb API enabled")
        
        self.base_url = "https://api.themoviedb.org/3"
        self.session = requests.Session()
        self.session.timeout = 10
    
    def search_movie(self, title: str) -> Optional[Dict[str, Any]]:
        """
        STEP 1: SEARCH for movie by title on TMDb.
        
        API Call: GET /search/movie?query={title}
        
        Extracts: id, title, vote_average, popularity, release_date, poster_path
        """
        if not self.enabled:
            logger.warning(f"⚠️  TMDb API not enabled - skipping search for '{title}'")
            return None
        
        logger.info(f"🔍 STEP 1 - SEARCH: '{title}'")
        
        try:
            search_url = f"{self.base_url}/search/movie"
            params = {
                "api_key": self.api_key,
                "query": title,
                "language": "en-US",
            }
            
            logger.debug(f"   API Call: GET /search/movie?query={title}")
            response = self.session.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])
            
            if not results:
                logger.warning(f"⚠️  No results found on TMDb for '{title}'")
                return None
            
            best_match = results[0]
            movie_id = best_match.get("id")
            found_title = best_match.get("title", title)
            
            logger.info(f"   ✅ Found: {found_title} (ID: {movie_id})")
            logger.debug(f"   Search result fields: {list(best_match.keys())}")
            
            return best_match
        
        except Exception as e:
            logger.error(f"❌ TMDb search failed for '{title}': {e}")
            return None
    
    def get_movie_details(self, movie_id: int) -> Optional[Dict[str, Any]]:
        """
        STEP 2: FETCH full movie details from TMDb with credits.
        
        API Call: GET /movie/{id}?append_to_response=credits
        
        Extracts: runtime, genres, cast, crew (Director), homepage, vote_average, popularity, release_date
        """
        if not self.enabled:
            logger.warning(f"⚠️  TMDb API not enabled - skipping details fetch for ID {movie_id}")
            return None
        
        logger.info(f"📥 STEP 2 - DETAILS: Fetching full movie data (ID: {movie_id})")
        
        try:
            details_url = f"{self.base_url}/movie/{movie_id}"
            params = {
                "api_key": self.api_key,
                "language": "en-US",
                "append_to_response": "credits",
            }
            
            logger.debug(f"   API Call: GET /movie/{movie_id}?append_to_response=credits")
            response = self.session.get(details_url, params=params, timeout=10)
            response.raise_for_status()
            
            movie_data = response.json()
            logger.debug(f"   Details fields: {list(movie_data.keys())}")
            
            return movie_data
        
        except Exception as e:
            logger.error(f"❌ TMDb details fetch failed for ID {movie_id}: {e}")
            return None
    
    def enrich_movie(self, doc: Dict[str, Any], doc_id: str = None) -> Dict[str, Any]:
        """
        FULL PIPELINE: Search → Details → Extract → Field-Level Patch → Update
        
        KEY CHANGE: Field-level patching (not object-level validation)
        - Extract whatever fields are available
        - Only include valid/non-empty values in patch
        - ALWAYS persist valid data, even if some fields missing
        - No more all-or-nothing rejection
        
        Args:
            doc: Document data
            doc_id: Firestore document ID (for logging)
        """
        title = doc.get("title", "")
        if doc_id is None:
            doc_id = doc.get("doc_id", "unknown")
        
        logger.info(f"\n{'='*80}")
        logger.info(f"🎬 ENRICHING: {title}")
        logger.info(f"   Doc ID: {doc_id}")
        logger.info(f"{'='*80}")
        
        # Check if enrichment is needed
        needs_it, missing = needs_enrichment(doc)
        if not needs_it:
            logger.info(f"✓ All critical fields populated, skipping")
            return {}
        
        logger.info(f"⚠️  Missing fields: {missing}")
        
        # STEP 1: Search for movie
        search_result = self.search_movie(title)
        if not search_result:
            logger.error(f"❌ Could not find movie on TMDb")
            return {}
        
        movie_id = search_result.get("id")
        
        # Rate limit
        time.sleep(API_RATE_LIMIT)
        
        # STEP 2: Get full details
        full_details = self.get_movie_details(movie_id)
        if not full_details:
            logger.error(f"❌ Could not fetch movie details")
            return {}
        
        # STEP 3: Extract fields from BOTH search and details
        extracted = self._extract_fields(search_result, full_details)
        logger.info(f"📦 RAW EXTRACTED DATA: {len(extracted)} fields found")
        
        # STEP 4: Build patch (field-level, only valid/non-empty values)
        patch = self._build_patch(doc, extracted)
        logger.info(f"📝 RAW PATCH (before cleaning): {patch}")
        
        # STEP 5: Clean patch (remove invalid values)
        patch = self._clean_patch(patch)
        logger.info(f"✨ FINAL PATCH (after cleaning): {patch}")
        
        # STEP 6: Log results (field-level granularity)
        self._log_enrichment_results(doc, patch, extracted)
        
        return patch
    
    def _extract_fields(self, search_result: Dict[str, Any], details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract all fields from SEARCH and DETAILS responses.
        
        Field mapping:
          image_url ← poster_path
          rating ← vote_average
          duration_ms ← runtime * 60000
          release_date ← release_date
          popularity ← popularity
          genres ← genres[]
          contributors ← credits.cast[]
          creator ← credits.crew (Director)
          external_url ← homepage
        """
        extracted = {}
        
        logger.info(f"\n🔄 EXTRACTING FIELDS:")
        
        # ─────────────────────────────────────────────────────────────
        # From SEARCH result
        # ─────────────────────────────────────────────────────────────
        
        # Rating (vote_average from search)
        if rating := search_result.get("vote_average"):
            if rating > 0:  # Only if valid
                extracted["rating"] = float(rating)
                logger.info(f"   ✓ rating: {rating}")
        
        # Popularity
        if popularity := search_result.get("popularity"):
            if popularity > 0:
                extracted["popularity"] = float(popularity)
                logger.info(f"   ✓ popularity: {popularity}")
        
        # Release date
        if release_date := search_result.get("release_date"):
            if release_date and release_date.strip():  # Only if not empty
                extracted["release_date"] = release_date
                logger.info(f"   ✓ release_date: {release_date}")
        
        # Image URL (poster_path)
        if poster_path := search_result.get("poster_path"):
            if poster_path:
                extracted["image_url"] = f"https://image.tmdb.org/t/p/w500{poster_path}"
                logger.info(f"   ✓ image_url: {extracted['image_url'][:50]}...")
        
        # ─────────────────────────────────────────────────────────────
        # From DETAILS response
        # ─────────────────────────────────────────────────────────────
        
        # Runtime → duration_ms (minutes * 60000)
        if runtime := details.get("runtime"):
            if runtime > 0:  # Only if valid
                extracted["duration_ms"] = int(runtime) * 60 * 1000
                extracted["duration"] = int(runtime) * 60  # Also in seconds
                logger.info(f"   ✓ duration_ms: {runtime} minutes → {extracted['duration_ms']} ms")
        
        # Genres
        genres = []
        for genre in details.get("genres", []):
            if isinstance(genre, dict):
                if name := genre.get("name"):
                    genres.append(name)
        if genres:
            extracted["genres"] = genres
            logger.info(f"   ✓ genres: {genres}")
        
        # Contributors (cast) - top 10 actors
        contributors = []
        credits = details.get("credits", {})
        if isinstance(credits, dict):
            cast = credits.get("cast", [])
            for actor in cast[:10]:  # Top 10
                if isinstance(actor, dict):
                    if name := actor.get("name"):
                        contributors.append(name)
        if contributors:
            extracted["contributors"] = contributors
            logger.info(f"   ✓ contributors: {len(contributors)} cast members")
        
        # Creator (director)
        if credits := details.get("credits", {}):
            crew = credits.get("crew", [])
            for person in crew:
                if isinstance(person, dict) and person.get("job") == "Director":
                    if name := person.get("name"):
                        extracted["creator"] = name
                        logger.info(f"   ✓ creator (director): {name}")
                        break
        
        # External URL (homepage from details)
        if movie_id := details.get("id"):
            # Use TMDb URL as official external URL
            extracted["external_url"] = f"https://www.themoviedb.org/movie/{movie_id}"
            logger.info(f"   ✓ external_url: {extracted['external_url']}")
        
        # Also save homepage if available (additional reference)
        if homepage := details.get("homepage"):
            if homepage and homepage.strip():
                logger.info(f"   ✓ homepage (reference): {homepage}")
                # Don't override external_url, but could store separately
        
        return extracted
    
    def _build_patch(self, original: Dict[str, Any], extracted: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build patch with ONLY fields that were missing/empty in original.
        
        Rules:
        - Only update if field missing OR default value (0, "", [])
        - Never overwrite valid existing data
        - CRITICAL: Do NOT skip valid extracted values
        """
        patch = {}
        
        logger.debug(f"\n🔨 BUILDING PATCH:")
        logger.debug(f"   Original fields: {list(original.keys())}")
        logger.debug(f"   Extracted fields: {list(extracted.keys())}")
        
        for field, value in extracted.items():
            # Don't skip if value exists - we'll clean it next
            original_value = original.get(field)
            
            # Check if field is missing or has default value
            is_missing = (
                original_value is None or
                original_value == "" or
                (isinstance(original_value, (list, dict)) and len(original_value) == 0) or
                original_value == 0
            )
            
            if is_missing:
                patch[field] = value
                logger.debug(f"   ✓ {field}: Will include in patch (original was missing)")
            else:
                logger.debug(f"   ✗ {field}: Skip (already in DB: {original_value})")
        
        return patch
    
    def _is_valid(self, value: Any) -> bool:
        """
        Check if a value is valid for persistence.
        
        Valid:
        - Non-None values
        - Non-empty strings
        - Non-empty arrays
        - Non-zero numbers (including floats like 85.3)
        
        Invalid:
        - None
        - "" (empty string)
        - [] (empty list)
        """
        if value is None:
            return False
        if isinstance(value, str):
            return len(value.strip()) > 0
        if isinstance(value, list):
            return len(value) > 0
        # Numbers: 0 is invalid, but any other number (0.5, 85.3, -1) is valid
        if isinstance(value, (int, float)):
            return value != 0
        # Everything else (dict, etc.) is valid
        return True
    
    def _clean_patch(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove invalid/empty values from patch.
        
        Keep only fields that have:
        - Non-None values
        - Non-empty strings
        - Non-empty arrays
        - Non-zero numbers
        
        This is FIELD-LEVEL cleaning, not object-level validation.
        Any valid field is kept, even if others are missing.
        """
        cleaned = {}
        
        logger.debug(f"\n🧹 CLEANING PATCH:")
        for field, value in patch.items():
            if self._is_valid(value):
                cleaned[field] = value
                logger.debug(f"   ✓ {field}: KEEP (valid)")
            else:
                logger.debug(f"   ✗ {field}: REMOVE (invalid: {value})")
        
        return cleaned
    
    def _log_enrichment_results(self, original_doc: Dict[str, Any], patch: Dict[str, Any], extracted: Dict[str, Any]) -> None:
        """
        Log enrichment results at field level.
        
        Shows:
        - Fields that were extracted
        - Fields that were actually updated
        - Fields that were skipped/not valid
        """
        title = original_doc.get("title", "UNKNOWN")
        
        if patch:
            updated_fields = sorted(list(patch.keys()))
            logger.info(f"\n✅ ENRICHMENT SUCCESSFUL")
            logger.info(f"   Title: {title}")
            logger.info(f"   Updated {len(patch)} fields:")
            
            for field in updated_fields:
                value = patch[field]
                if isinstance(value, list):
                    logger.info(f"      ✓ {field}: {len(value)} items")
                elif isinstance(value, (int, float)):
                    logger.info(f"      ✓ {field}: {value}")
                else:
                    preview = str(value)[:50]
                    logger.info(f"      ✓ {field}: {preview}")
            
            # Show skipped fields
            skipped = [f for f in extracted if f not in patch]
            if skipped:
                logger.info(f"   Skipped {len(skipped)} fields (invalid/empty):")
                for field in skipped:
                    logger.info(f"      ✗ {field}: {extracted.get(field)}")
        else:
            logger.warning(f"⚠️  No valid fields to update for: {title}")
    
    # Remove the old _validate_extraction method - REPLACED with field-level cleaning
    # The system now persists ANY valid data, not all-or-nothing validation


def enrich_movie_document(db, collection, doc_id: str, doc_data: Dict[str, Any]) -> bool:
    """
    ENRICH a single movie document by calling TMDb API.
    
    Returns: True if DB was updated, False otherwise
    """
    title = doc_data.get("title", "unknown")
    
    # Check if enrichment needed
    needs_it, missing = needs_enrichment(doc_data)
    if not needs_it:
        logger.info(f"✓ {title}: No enrichment needed")
        return False
    
    logger.info(f"\n🔧 ENRICHING: {title}")
    logger.info(f"   Doc ID: {doc_id}")
    logger.info(f"   Missing: {missing}")
    
    # Call TMDb API with doc_id
    enricher = TMDbAPIEnricher()
    patch = enricher.enrich_movie(doc_data, doc_id=doc_id)
    
    if not patch:
        logger.warning(f"❌ {title}: Enrichment found no new data")
        return False
    
    # UPDATE DATABASE
    try:
        doc_ref = db.collection(collection).document(doc_id)
        doc_ref.update(patch)
        logger.info(f"✅ {title}: DB updated with {len(patch)} fields")
        logger.info(f"   Updated fields: {list(patch.keys())}")
        return True
    
    except Exception as e:
        logger.error(f"❌ {title}: Failed to update DB: {e}")
        return False


def test_single_movie(db, collection: str, movie_title: str = "Avengers: Doomsday") -> None:
    """
    TEST enrichment on a single movie FIRST.
    
    This verifies the system works before running full batch.
    """
    logger.info(f"\n\n{'#'*80}")
    logger.info(f"# SINGLE MOVIE TEST")
    logger.info(f"# Testing enrichment on: {movie_title}")
    logger.info(f"{'#'*80}\n")
    
    try:
        # Find the movie in DB
        query = db.collection(collection).where("title", "==", movie_title)
        docs = list(query.stream())
        
        if not docs:
            logger.error(f"❌ Movie '{movie_title}' not found in database")
            logger.info(f"   Searched in collection: {collection}")
            return
        
        doc = docs[0]
        doc_id = doc.id
        doc_data = doc.to_dict() or {}
        
        logger.info(f"✓ Found in DB: {doc_id}")
        logger.info(f"  Current data: {list(doc_data.keys())}")
        
        # Enrich it
        success = enrich_movie_document(db, collection, doc_id, doc_data)
        
        if success:
            logger.info(f"\n✅ TEST PASSED - Movie enriched successfully")
            
            # Show updated data
            updated = db.collection(collection).document(doc_id).get().to_dict()
            logger.info(f"\n📊 AFTER ENRICHMENT:")
            logger.info(f"   image_url: {updated.get('image_url', 'MISSING')[:50]}...")
            logger.info(f"   external_url: {updated.get('external_url', 'MISSING')}")
            logger.info(f"   rating: {updated.get('rating', 'MISSING')}")
            logger.info(f"   duration_ms: {updated.get('duration_ms', 'MISSING')}")
            logger.info(f"   genres: {updated.get('genres', 'MISSING')}")
            logger.info(f"   contributors: {len(updated.get('contributors', []))} cast members")
            logger.info(f"   creator: {updated.get('creator', 'MISSING')}")
        else:
            logger.error(f"\n❌ TEST FAILED - Movie not enriched")
    
    except Exception as e:
        logger.error(f"❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()








