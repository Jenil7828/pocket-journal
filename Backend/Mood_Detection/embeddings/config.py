# embeddings/config.py

class EmbeddingConfig:
    # Base model (can be swapped for better accuracy)
    MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"

    # Training (optional fine-tuning)
    TRAIN_BATCH_SIZE = 16
    EVAL_BATCH_SIZE = 16
    NUM_EPOCHS = 3
    LEARNING_RATE = 2e-5

    # Paths
    OUTPUT_DIR = "outputs/models/embeddings_model"
