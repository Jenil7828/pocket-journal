"""
Notification service for managing user notification preferences.

Controls:
- Email notifications
- Push notifications
- Daily journal reminders (with time)
- Weekly insights notifications
- Media recommendation notifications
"""

import logging
import re
from typing import Dict, Optional

logger = logging.getLogger()


def get_default_notification_settings() -> Dict[str, any]:
    """Get default notification settings structure."""
    return {
        "email_notifications": True,
        "push_notifications": True,
        "daily_reminder": True,
        "reminder_time": "09:00",  # HH:mm format
        "weekly_insights": True,
        "media_recommendations": True
    }


def validate_reminder_time(reminder_time: str) -> tuple[bool, Optional[str]]:
    """
    Validate HH:mm time format.
    
    Args:
        reminder_time: Time string in HH:mm format
        
    Returns:
        (is_valid, error_message)
    """
    if not isinstance(reminder_time, str):
        return False, "reminder_time must be a string"
    
    # Check HH:mm format
    pattern = r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$"
    if not re.match(pattern, reminder_time):
        return False, "reminder_time must be in HH:mm format (00:00 - 23:59)"
    
    return True, None


def validate_notification_settings(notifications: Dict[str, any]) -> tuple[bool, Optional[str]]:
    """
    Validate user notification settings.
    
    Args:
        notifications: Notification settings dictionary to validate
        
    Returns:
        (is_valid, error_message)
    """
    if not isinstance(notifications, dict):
        return False, "Notification settings must be a dictionary"
    
    # Validate boolean fields
    bool_fields = [
        "email_notifications",
        "push_notifications",
        "daily_reminder",
        "weekly_insights",
        "media_recommendations"
    ]
    
    for field in bool_fields:
        if field in notifications and not isinstance(notifications[field], bool):
            return False, f"{field} must be boolean"
    
    # Validate reminder_time
    if "reminder_time" in notifications:
        is_valid, error_msg = validate_reminder_time(notifications["reminder_time"])
        if not is_valid:
            return False, error_msg
    
    return True, None


def merge_notification_settings(
    existing: Dict[str, any],
    incoming: Dict[str, any]
) -> Dict[str, any]:
    """
    Merge incoming notification settings with existing (shallow merge, incoming overwrites).
    
    Args:
        existing: Existing notification settings
        incoming: New notification settings to merge
        
    Returns:
        Merged notification settings
    """
    result = existing.copy() if existing else get_default_notification_settings()
    
    if not isinstance(incoming, dict):
        return result
    
    # Merge boolean fields
    bool_fields = [
        "email_notifications",
        "push_notifications",
        "daily_reminder",
        "weekly_insights",
        "media_recommendations"
    ]
    
    for field in bool_fields:
        if field in incoming and isinstance(incoming[field], bool):
            result[field] = incoming[field]
    
    # Merge reminder_time with validation
    if "reminder_time" in incoming and isinstance(incoming["reminder_time"], str):
        is_valid, _ = validate_reminder_time(incoming["reminder_time"])
        if is_valid:
            result["reminder_time"] = incoming["reminder_time"]
    
    return result


def get_user_notification_settings(user_doc_dict: Dict[str, any]) -> Dict[str, any]:
    """
    Extract notification settings from user document, with defaults for missing fields.
    
    Args:
        user_doc_dict: User document as dictionary
        
    Returns:
        Notification settings with all required fields
    """
    existing_notif = user_doc_dict.get("notification_settings", {})
    defaults = get_default_notification_settings()
    
    if not isinstance(existing_notif, dict):
        return defaults
    
    # Merge with defaults to ensure all fields present
    return merge_notification_settings(defaults, existing_notif)


def should_send_daily_reminder(notification_settings: Dict[str, any]) -> bool:
    """Check if daily reminders are enabled."""
    return notification_settings.get("daily_reminder", True) and notification_settings.get("email_notifications", True)


def should_send_weekly_insights(notification_settings: Dict[str, any]) -> bool:
    """Check if weekly insights notifications are enabled."""
    return notification_settings.get("weekly_insights", True) and notification_settings.get("email_notifications", True)


def should_send_media_recommendations(notification_settings: Dict[str, any]) -> bool:
    """Check if media recommendation notifications are enabled."""
    return notification_settings.get("media_recommendations", True) and notification_settings.get("email_notifications", True)


def can_push_notify(notification_settings: Dict[str, any]) -> bool:
    """Check if push notifications are enabled."""
    return notification_settings.get("push_notifications", True)

