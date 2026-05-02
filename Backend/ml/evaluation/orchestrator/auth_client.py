import time
import requests
import logging
from datetime import datetime

logger = logging.getLogger()

class AuthClient:
    """Handles login and token management for the evaluation pipeline.
    
    Firebase ID tokens expire after 60 minutes. This client tracks the acquisition
    time and automatically refreshes (re-logins) if the token is older than 55 minutes.
    """
    
    def __init__(self, base_url: str, email: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.password = password
        self.token = None
        self.token_acquired_at = 0

    def login(self) -> str:
        """Authenticate with the API and retrieve an ID token.
        
        POST /api/v1/auth/login
        """
        logger.info("[AUTH] Attempting login for %s", self.email)
        url = f"{self.base_url}/api/v1/auth/login"
        payload = {"email": self.email, "password": self.password}
        
        try:
            response = requests.post(url, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            self.token = data.get("id_token")
            if not self.token:
                raise RuntimeError("Login response missing id_token")
                
            self.token_acquired_at = time.time()
            logger.info("[AUTH] Login successful, token acquired.")
            return self.token
            
        except requests.exceptions.RequestException as e:
            logger.error("[AUTH] Login failed: %s", str(e))
            if hasattr(e, 'response') and e.response is not None:
                logger.error("[AUTH] Response body: %s", e.response.text)
            raise RuntimeError(f"Authentication failed: {str(e)}")

    def get_headers(self) -> dict:
        """Return headers required for authenticated API requests."""
        if not self.token:
            self.login()
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def refresh_if_expired(self):
        """Check if the current token is near expiration and refresh if necessary.
        
        Firebase tokens expire at 60 minutes. We refresh at 55 minutes.
        """
        if not self.token or (time.time() - self.token_acquired_at) > 3300: # 55 minutes
            logger.info("[AUTH] Token expired or near expiration, refreshing...")
            self.login()
