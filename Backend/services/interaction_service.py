"""
Interaction Service - Phase 4: Personalization Feedback Loop

Handles user interaction events (clicks, saves, skips) and stores them
in Firestore for the taste vector learning system.

No external API calls. Pure data storage and validation.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from firebase_admin import firestore

logger = logging.getLogger("pocket_journal.interaction_service")

# Signal to weight mapping
SIGNAL_WEIGHTS = {
    "click": 0.02,
    "save": 0.05,
    "skip": -0.01,
}

# Valid media types
VALID_MEDIA_TYPES = {"songs", "movies", "books", "podcasts"}

# Valid signals
VALID_SIGNALS = set(SIGNAL_WEIGHTS.keys())

# Valid contexts
VALID_CONTEXTS = {"recommendation", "search"}


class InteractionService:
    """
    Stores and manages user interaction events.
    Validates all inputs before persisting.
    """

    def __init__(self, db):
        """
        Args:
            db: Firebase Firestore client
        """
        self.db = db

    def validate_interaction(
        self,
        media_type: str,
        item_id: str,
        signal: str,
        context: str,
    ) -> tuple[bool, Optional[str]]:
        """
        Validate interaction parameters.

        Returns:
            (is_valid, error_message)
        """
        if not media_type:
            return False, "media_type is required"

        if media_type.lower() not in VALID_MEDIA_TYPES:
            return False, f"Invalid media_type: {media_type}. Must be one of: {', '.join(VALID_MEDIA_TYPES)}"

        if not item_id or not isinstance(item_id, str):
            return False, "item_id must be a non-empty string"

        if not signal:
            return False, "signal is required"

        if signal.lower() not in VALID_SIGNALS:
            return False, f"Invalid signal: {signal}. Must be one of: {', '.join(VALID_SIGNALS)}"

        if context and context.lower() not in VALID_CONTEXTS:
            return False, f"Invalid context: {context}. Must be one of: {', '.join(VALID_CONTEXTS)}"

        return True, None

    def store_interaction(
        self,
        uid: str,
        media_type: str,
        item_id: str,
        signal: str,
        context: str = "recommendation",
    ) -> Dict[str, Any]:
        """
        Store a single interaction event in Firestore.

        Collection path: user_interactions/{uid}/events/{auto_id}

        Document structure:
        {
            "media_type": str,
            "item_id": str,
            "signal": str,
            "weight": float,
            "context": str,
            "timestamp": Firestore timestamp
        }

        Args:
            uid: User ID
            media_type: One of: songs, movies, books, podcasts
            item_id: Media item ID from cache
            signal: One of: click, save, skip
            context: One of: recommendation, search (default: recommendation)

        Returns:
            Dict with stored event metadata
        """
        # Normalize inputs
        media_type = media_type.lower().strip()
        item_id = item_id.strip()
        signal = signal.lower().strip()
        context = (context or "recommendation").lower().strip()

        # Validate
        is_valid, error_msg = self.validate_interaction(media_type, item_id, signal, context)
        if not is_valid:
            logger.warning(
                "pocket_journal.interaction: validation_failed uid=%s error=%s",
                uid,
                error_msg,
            )
            raise ValueError(error_msg)

        # Get weight for signal
        weight = SIGNAL_WEIGHTS[signal]

        # Build event document
        event_doc = {
            "media_type": media_type,
            "item_id": item_id,
            "signal": signal,
            "weight": weight,
            "context": context,
            "timestamp": firestore.SERVER_TIMESTAMP,
        }

        try:
            # Store in user_interactions/{uid}/events
            collection_ref = self.db.collection("user_interactions").document(uid).collection("events")
            doc_ref = collection_ref.document()  # Auto-generate ID
            doc_ref.set(event_doc)

            event_id = doc_ref.id

            logger.info(
                "pocket_journal.interaction: event_stored uid=%s event_id=%s media_type=%s signal=%s weight=%.2f",
                uid,
                event_id,
                media_type,
                signal,
                weight,
            )

            return {
                "status": "ok",
                "event_id": event_id,
                "media_type": media_type,
                "item_id": item_id,
                "signal": signal,
                "weight": weight,
                "context": context,
            }

        except Exception as e:
            logger.error(
                "pocket_journal.interaction: store_failed uid=%s media_type=%s error=%s",
                uid,
                media_type,
                str(e),
            )
            raise

    def count_interactions_in_period(
        self,
        uid: str,
        media_type: str,
        hours: int = 1,
    ) -> int:
        """
        Count interaction events for a user in a given time period.

        Used for rate limiting.

        Args:
            uid: User ID
            media_type: Media type to filter
            hours: Time window in hours (default: 1)

        Returns:
            Count of events
        """
        try:
            # Calculate cutoff time
            now = datetime.now(timezone.utc)
            cutoff = now.timestamp() - (hours * 3600)

            # Query events collection
            collection_ref = self.db.collection("user_interactions").document(uid).collection("events")
            query = collection_ref.where("media_type", "==", media_type.lower())

            events = list(query.stream())
            count = 0

            for event_doc in events:
                event_data = event_doc.to_dict() or {}
                ts = event_data.get("timestamp")

                # Handle Firestore timestamp
                if hasattr(ts, "timestamp"):
                    event_timestamp = ts.timestamp()
                else:
                    event_timestamp = ts

                if event_timestamp and event_timestamp >= cutoff:
                    count += 1

            logger.debug(
                "pocket_journal.interaction: count_in_period uid=%s media_type=%s hours=%d count=%d",
                uid,
                media_type,
                hours,
                count,
            )

            return count

        except Exception as e:
            logger.error(
                "pocket_journal.interaction: count_failed uid=%s media_type=%s error=%s",
                uid,
                media_type,
                str(e),
            )
            return 0

