import time
import requests
import logging
from typing import Dict, List, Any, Optional
from .auth_client import AuthClient

logger = logging.getLogger()

class APIClient:
    """Wrapper for all API calls required for system evaluation.
    
    Each method ensures valid authentication via AuthClient and handles
    logging and error reporting.
    """
    
    def __init__(self, base_url: str, auth_client: AuthClient, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.auth_client = auth_client
        self.timeout = timeout

    def _request(self, method: str, path: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Internal helper for making authenticated requests."""
        self.auth_client.refresh_if_expired()
        url = f"{self.base_url}{path}"
        headers = self.auth_client.get_headers()
        
        try:
            response = requests.request(method, url, headers=headers, timeout=self.timeout, **kwargs)
            if not response.ok:
                logger.warning("[API] %s %s failed (Status %d): %s", 
                               method, path, response.status_code, response.text[:200])
                return None
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.warning("[API] Network error during %s %s: %s", method, path, str(e))
            raise

    def create_journal_entry(self, entry_text: str, title: str = None) -> Dict[str, Any]:
        """POST /api/v1/journal - Create a new entry and get analysis."""
        payload = {"entry_text": entry_text}
        if title:
            payload["title"] = title
            
        logger.info("[API] Creating journal entry...")
        result = self._request("POST", "/api/v1/journal", json=payload)
        if result is None:
            raise RuntimeError("Critical API Failure: Could not create journal entry")
        return result

    def get_entry_analysis(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """GET /api/v1/journal/{entry_id}/analysis - Retrieve existing analysis."""
        return self._request("GET", f"/api/v1/journal/{entry_id}/analysis")

    def get_movie_recommendations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """GET /api/v1/movies/recommend - Retrieve movie recommendations."""
        result = self._request("GET", "/api/v1/movies/recommend", params={"limit": limit})
        return result.get("results", []) if result and isinstance(result, dict) else []

    def get_song_recommendations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """GET /api/v1/songs/recommend - Retrieve song recommendations."""
        result = self._request("GET", "/api/v1/songs/recommend", params={"limit": limit})
        return result.get("results", []) if result and isinstance(result, dict) else []

    def get_book_recommendations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """GET /api/v1/books/recommend - Retrieve book recommendations."""
        result = self._request("GET", "/api/v1/books/recommend", params={"limit": limit})
        return result.get("results", []) if result and isinstance(result, dict) else []

    def generate_insights(self, start_date: str, end_date: str) -> Optional[Dict[str, Any]]:
        """POST /api/v1/insights/generate - Trigger insights generation."""
        payload = {"start_date": start_date, "end_date": end_date}
        return self._request("POST", "/api/v1/insights/generate", json=payload)

    def delete_journal_entry(self, entry_id: str) -> bool:
        """DELETE /api/v1/journal/{entry_id} - Clean up evaluation data."""
        self.auth_client.refresh_if_expired()
        url = f"{self.base_url}/api/v1/journal/{entry_id}"
        headers = self.auth_client.get_headers()
        
        try:
            response = requests.delete(url, headers=headers, timeout=self.timeout)
            if response.status_code == 200:
                logger.info("[API] Successfully deleted entry %s", entry_id)
                return True
            logger.warning("[API] Delete failed for entry %s: %s", entry_id, response.text)
            return False
        except Exception as e:
            logger.warning("[API] Error deleting entry %s: %s", entry_id, str(e))
            return False
