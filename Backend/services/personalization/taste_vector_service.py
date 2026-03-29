"""
Taste Vector Service - Phase 4: Personalization Feedback Loop

Manages user taste vectors (domain-specific preference embeddings).
Updates vectors based on interaction weights.

Core algorithm:
  new_vec = current_vec + weight * item_vec
  new_vec = normalize(new_vec)
"""

import logging
from typing import Optional, Dict, Any

import numpy as np
from firebase_admin import firestore

from services.embeddings.embedding_service import EmbeddingService

logger = logging.getLogger("pocket_journal.taste_vector_service")

# Media type to vector key mapping
MEDIA_TYPE_TO_VECTOR_KEY = {
    "songs": "songs_vector",
    "song": "songs_vector",
    "movies": "movies_vector",
    "movie": "movies_vector",
    "books": "books_vector",
    "book": "books_vector",
    "podcasts": "podcasts_vector",
    "podcast": "podcasts_vector",
}


class TasteVectorService:
    """
    Updates user taste vectors based on interaction signals.
    Implements the feedback loop learning mechanism.
    """

    def __init__(self, db):
        """
        Args:
            db: Firebase Firestore client
        """
        self.db = db

    def item_exists_in_cache(self, media_type: str, item_id: str) -> bool:
        """
        Check if an item exists in the media cache.

        Used to validate items before storing interactions.

        Args:
            media_type: One of: songs, movies, books, podcasts
            item_id: Item ID to check

        Returns:
            True if item exists in cache, False otherwise
        """
        try:
            media_type_lower = media_type.lower().strip()
            cache_collection = f"media_cache_{media_type_lower}"

            doc = self.db.collection(cache_collection).document(item_id).get()

            exists = doc.exists

            if not exists:
                logger.debug(
                    "pocket_journal.taste_vector: item_not_in_cache media_type=%s item_id=%s",
                    media_type,
                    item_id,
                )
            else:
                logger.debug(
                    "pocket_journal.taste_vector: item_found_in_cache media_type=%s item_id=%s",
                    media_type,
                    item_id,
                )

            return exists

        except Exception as e:
            logger.error(
                "pocket_journal.taste_vector: cache_check_failed media_type=%s item_id=%s error=%s",
                media_type,
                item_id,
                str(e),
            )
            # Return False on error (item not found)
            return False

    def get_item_embedding(self, media_type: str, item_id: str) -> Optional[np.ndarray]:
        """
        Fetch item from media cache and return its embedding as numpy array.

        Cache collection: media_cache_{media_type}

        Args:
            media_type: One of: songs, movies, books, podcasts
            item_id: Item ID in cache

        Returns:
            Normalized numpy array or None if not found
        """
        try:
            media_type_lower = media_type.lower().strip()
            cache_collection = f"media_cache_{media_type_lower}"

            doc = self.db.collection(cache_collection).document(item_id).get()

            if not doc.exists:
                logger.debug(
                    "pocket_journal.taste_vector: item_not_found media_type=%s item_id=%s",
                    media_type,
                    item_id,
                )
                return None

            data = doc.to_dict() or {}
            embedding = data.get("embedding")

            if not embedding:
                logger.debug(
                    "pocket_journal.taste_vector: item_has_no_embedding media_type=%s item_id=%s",
                    media_type,
                    item_id,
                )
                return None

            # Convert to numpy array
            arr = np.asarray(embedding, dtype=np.float32)

            # Normalize
            norm = np.linalg.norm(arr)
            if norm > 0:
                arr = arr / norm

            logger.debug(
                "pocket_journal.taste_vector: item_embedding_fetched media_type=%s item_id=%s dim=%d",
                media_type,
                item_id,
                len(arr),
            )

            return arr

        except Exception as e:
            logger.error(
                "pocket_journal.taste_vector: item_fetch_failed media_type=%s item_id=%s error=%s",
                media_type,
                item_id,
                str(e),
            )
            return None

    def get_user_vector(self, uid: str, media_type: str) -> Optional[np.ndarray]:
        """
        Fetch user's current taste vector for a media type.

        Collection: user_vectors/{uid}
        Fields: {media_type}_vector (e.g., "songs_vector")

        Returns:
            Numpy array or None if not found
        """
        try:
            media_type_lower = media_type.lower().strip()
            vector_key = MEDIA_TYPE_TO_VECTOR_KEY.get(media_type_lower)

            if not vector_key:
                logger.warning(
                    "pocket_journal.taste_vector: unsupported_media_type uid=%s media_type=%s",
                    uid,
                    media_type,
                )
                return None

            doc = self.db.collection("user_vectors").document(uid).get()

            if not doc.exists:
                logger.debug(
                    "pocket_journal.taste_vector: user_vector_not_found uid=%s",
                    uid,
                )
                return None

            data = doc.to_dict() or {}
            vector_data = data.get(vector_key)

            if not vector_data:
                logger.debug(
                    "pocket_journal.taste_vector: user_vector_missing uid=%s key=%s",
                    uid,
                    vector_key,
                )
                return None

            arr = np.asarray(vector_data, dtype=np.float32)

            logger.debug(
                "pocket_journal.taste_vector: user_vector_fetched uid=%s key=%s dim=%d",
                uid,
                vector_key,
                len(arr),
            )

            return arr

        except Exception as e:
            logger.error(
                "pocket_journal.taste_vector: user_vector_fetch_failed uid=%s media_type=%s error=%s",
                uid,
                media_type,
                str(e),
            )
            return None

    def update_taste_vector(
        self,
        uid: str,
        media_type: str,
        item_id: str,
        weight: float,
    ) -> Dict[str, Any]:
        """
        Update user's taste vector based on interaction.

        Algorithm:
          1. Fetch item embedding from cache
          2. Fetch user's current vector from user_vectors
          3. Apply update: new_vec = current_vec + weight * item_vec
          4. Normalize: new_vec = new_vec / ||new_vec||
          5. Store back to Firestore

        Edge cases:
          - Item not found in cache → skip
          - User vector missing → initialize from item embedding
          - Normalization can fail → handled gracefully

        Args:
            uid: User ID
            media_type: One of: songs, movies, books, podcasts
            item_id: Item ID in cache
            weight: Weight from signal (e.g., 0.02 for click, 0.05 for save)

        Returns:
            Dict with update status and metadata
        """

        media_type_lower = media_type.lower().strip()
        vector_key = MEDIA_TYPE_TO_VECTOR_KEY.get(media_type_lower)

        if not vector_key:
            logger.warning(
                "pocket_journal.taste_vector: unsupported_media_type uid=%s media_type=%s",
                uid,
                media_type,
            )
            return {
                "status": "skipped",
                "reason": "unsupported_media_type",
                "updated": False,
            }

        # Step 1: Fetch item embedding
        item_embedding = self.get_item_embedding(media_type, item_id)

        if item_embedding is None:
            logger.debug(
                "pocket_journal.taste_vector: item_embedding_missing uid=%s media_type=%s item_id=%s",
                uid,
                media_type,
                item_id,
            )
            return {
                "status": "skipped",
                "reason": "item_not_found",
                "updated": False,
            }

        try:
            # Step 2: Fetch current user vector
            current_vector = self.get_user_vector(uid, media_type)

            # Step 3: Apply update
            if current_vector is not None:
                # Update: new = current + weight * item
                new_vector = current_vector + weight * item_embedding
            else:
                # Initialize: new = weight * item
                new_vector = weight * item_embedding

            # Step 4: Normalize
            norm = np.linalg.norm(new_vector)
            if norm > 1e-8:
                new_vector = new_vector / norm
            else:
                # Fallback to uniform vector if norm is too small
                new_vector = np.ones_like(new_vector) / np.sqrt(len(new_vector))

            # Step 5: Store back
            new_vector_list = new_vector.tolist()

            update_data = {
                vector_key: new_vector_list,
                "updated_at": firestore.SERVER_TIMESTAMP,
            }

            self.db.collection("user_vectors").document(uid).set(update_data, merge=True)

            logger.info(
                "pocket_journal.taste_vector: update_success uid=%s media_type=%s item_id=%s weight=%.4f dim=%d",
                uid,
                media_type,
                item_id,
                weight,
                len(new_vector),
            )

            return {
                "status": "ok",
                "updated": True,
                "media_type": media_type,
                "item_id": item_id,
                "weight": weight,
                "vector_dim": len(new_vector),
            }

        except Exception as e:
            logger.error(
                "pocket_journal.taste_vector: update_failed uid=%s media_type=%s item_id=%s error=%s",
                uid,
                media_type,
                item_id,
                str(e),
            )
            return {
                "status": "error",
                "reason": str(e),
                "updated": False,
            }


