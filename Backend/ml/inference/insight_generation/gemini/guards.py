"""
Gemini environment setup and guards.
Checks for GEMINI_API_KEY and validates configuration.
"""

import os
import logging

logger = logging.getLogger()


def setup_gemini_env():
    """
    Check if Gemini is enabled and API key is available.
    Returns a dict with:
      - enabled: bool indicating if Gemini is configured
      - api_key: str with the API key if available
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    enabled = bool(api_key)
    
    if enabled:
        logger.info("Gemini environment configured with API key")
    else:
        logger.info("Gemini not configured - GEMINI_API_KEY not set")
    
    return {
        "enabled": enabled,
        "api_key": api_key if enabled else None,
    }

