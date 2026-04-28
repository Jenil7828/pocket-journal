"""
Settings service for managing user feature toggles and system settings.

Controls:
- Mood tracking enabled/disabled
- Weekly insights enabled/disabled
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger()


def get_default_settings() -> Dict[str, bool]:
    """Get default settings structure."""
    return {
        "mood_tracking_enabled": True,
        "weekly_insights_enabled": True
    }


def validate_settings(settings: Dict[str, any]) -> tuple[bool, Optional[str]]:
    """
    Validate user settings.
    
    Args:
        settings: Settings dictionary to validate
        
    Returns:
        (is_valid, error_message)
    """
    if not isinstance(settings, dict):
        return False, "Settings must be a dictionary"
    
    # Validate mood_tracking_enabled
    if "mood_tracking_enabled" in settings:
        if not isinstance(settings["mood_tracking_enabled"], bool):
            return False, "mood_tracking_enabled must be boolean"
    
    # Validate weekly_insights_enabled
    if "weekly_insights_enabled" in settings:
        if not isinstance(settings["weekly_insights_enabled"], bool):
            return False, "weekly_insights_enabled must be boolean"
    
    return True, None


def merge_settings(existing: Dict[str, bool], incoming: Dict[str, any]) -> Dict[str, bool]:
    """
    Merge incoming settings with existing (shallow merge, incoming overwrites).
    
    Args:
        existing: Existing settings
        incoming: New settings to merge
        
    Returns:
        Merged settings
    """
    result = existing.copy() if existing else get_default_settings()
    
    if not isinstance(incoming, dict):
        return result
    
    for key in ["mood_tracking_enabled", "weekly_insights_enabled"]:
        if key in incoming and isinstance(incoming[key], bool):
            result[key] = incoming[key]
    
    return result


def get_user_settings(user_doc_dict: Dict[str, any]) -> Dict[str, bool]:
    """
    Extract settings from user document, with defaults for missing fields.
    
    Args:
        user_doc_dict: User document as dictionary
        
    Returns:
        Settings with all required fields
    """
    existing_settings = user_doc_dict.get("settings", {})
    defaults = get_default_settings()
    
    if not isinstance(existing_settings, dict):
        return defaults
    
    # Merge with defaults to ensure all fields present
    result = defaults.copy()
    for key in result.keys():
        if key in existing_settings and isinstance(existing_settings[key], bool):
            result[key] = existing_settings[key]
    
    return result

