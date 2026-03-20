# services/embedding_service.py
import logging
import os
import traceback
from typing import List, Optional

import numpy as np

# Ensure HF opt-out set before any HF-related imports
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

from config_loader import get_config
from services.suppression import suppress_hf

logger = logging.getLogger("pocket_journal.embedding_service")

_CFG = get_config()


# Lazy import heavy deps inside the class to avoid import-time side-effects
try:
    import torch
except Exception:
    torch = None


class EmbeddingService:
    """Centralized embedding service using sentence-transformers.

    - Uses model "all-mpnet-base-v2" by default.
    - Detects CUDA availability and uses it when present; falls back to CPU.
    - Loads model once per process.
    - Provides helpers to embed text(s), normalize vectors and compute cosine similarity.
    """

    def __init__(self, model_name: Optional[str] = None):
        if model_name is None:
            model_name = str(_CFG["embedding"]["model_name"])

        # Import SentenceTransformer lazily inside constructor so HF env flags are effective
        try:
            with suppress_hf():
                from sentence_transformers import SentenceTransformer
        except Exception:
            SentenceTransformer = None

        if SentenceTransformer is None:
            raise RuntimeError("sentence-transformers is not installed or failed to import")

        # Determine device
        device = "cpu"
        try:
            if torch is not None and torch.cuda.is_available():
                device = "cuda"
        except Exception:
            device = "cpu"

        self.device = device
        logger.info("EmbeddingService using device=%s", self.device)

        # Load the model onto the chosen device once, suppressing HF chatter
        try:
            with suppress_hf():
                # SentenceTransformer accepts a device string like 'cpu' or 'cuda'
                self.model = SentenceTransformer(model_name, device=self.device)
        except Exception as e:
            logger.warning("Failed to load embedding model: %s", str(e))
            logger.debug(traceback.format_exc())
            raise

    @staticmethod
    def _to_float32(vec: np.ndarray) -> np.ndarray:
        if vec.dtype != np.float32:
            return vec.astype(np.float32)
        return vec

    @staticmethod
    def normalize(vec: np.ndarray) -> np.ndarray:
        """Return a float32 L2-normalized copy of vec. If norm is zero, returns vec of zeros."""
        if vec is None:
            return None
        vec = np.asarray(vec)
        if vec.size == 0:
            return vec.astype(np.float32)
        vec = vec.astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm == 0 or np.isnan(norm):
            return np.zeros_like(vec, dtype=np.float32)
        return (vec / norm).astype(np.float32)

    def embed_text(self, text: str) -> np.ndarray:
        """Embed a single piece of text and return a normalized float32 vector."""
        if not text:
            return np.array([], dtype=np.float32)
        try:
            # Suppress potential materialization/progress output during encode
            with suppress_hf():
                arr = self.model.encode([text], normalize_embeddings=False)
        except Exception as e:
            logger.warning("Embedding failed for input (len=%d): %s", len(str(text) or ""), str(e))
            logger.debug(traceback.format_exc())
            return np.array([], dtype=np.float32)
        vec = np.asarray(arr[0])
        vec = self._to_float32(vec)
        vec = self.normalize(vec)
        # Log concise embedding creation info (do not log vector contents)
        try:
            dim = int(vec.shape[-1]) if hasattr(vec, "shape") else None
            logger.info("Created embedding (text_len=%d) dim=%s", len(str(text or "")), dim)
        except Exception:
            logger.info("Created embedding (could not infer dim)")
        return vec

    def embed_texts(self, texts: List[str]) -> List[np.ndarray]:
        """Embed multiple texts and return list of normalized float32 vectors."""
        if not texts:
            return []
        try:
            with suppress_hf():
                arrs = self.model.encode(texts, normalize_embeddings=False)
        except Exception as e:
            logger.warning("Batch embedding failed for %d texts: %s", len(texts), str(e))
            logger.debug(traceback.format_exc())
            return []
        results = []
        for row in arrs:
            vec = np.asarray(row)
            vec = self._to_float32(vec)
            vec = self.normalize(vec)
            results.append(vec)
        logger.info("Created %d embeddings (batch)", len(results))
        return results

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> Optional[float]:
        """Compute cosine similarity between two vectors. Expect normalized vectors for best result."""
        if a is None or b is None:
            return None
        a = np.asarray(a, dtype=np.float32)
        b = np.asarray(b, dtype=np.float32)
        if a.size == 0 or b.size == 0:
            return None
        # Ensure both are normalized
        an = a / (np.linalg.norm(a) + 1e-12)
        bn = b / (np.linalg.norm(b) + 1e-12)
        sim = float(np.dot(an, bn))
        logger.info("Cosine similarity computed (sim=%.6f)", sim)
        return sim


# Module-level singleton helper
_singleton: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    global _singleton
    if _singleton is None:
        _singleton = EmbeddingService()
    return _singleton

