# embeddings/embedder.py

from sentence_transformers import SentenceTransformer
import numpy as np
from .config import EmbeddingConfig

class Embedder:
    def __init__(self, model_path: str = None):
        # Load fine-tuned model if available, else load base
        self.model = SentenceTransformer(model_path or EmbeddingConfig.MODEL_NAME)

    def get_embedding(self, text: str) -> np.ndarray:
        """Return vector embedding for a given text"""
        return self.model.encode(text, convert_to_numpy=True)

    def get_batch_embeddings(self, texts: list) -> np.ndarray:
        """Return embeddings for a batch of texts"""
        return self.model.encode(texts, convert_to_numpy=True, batch_size=32)

# Example Usage
if __name__ == "__main__":
    embedder = Embedder()
    sample_text = "I feel happy today because I finished my project."
    vector = embedder.get_embedding(sample_text)
    print("Embedding shape:", vector.shape)
    print("First 5 dims:", vector[:5])
