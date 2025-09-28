import os

class Config:
    # Model settings
    MODEL_NAME = "roberta-base"
    MAX_LENGTH = 128

    # Paths
    OUTPUT_DIR = os.path.join("outputs", "models", "mood_sentence_roberta")
    DATASET_DIR = os.path.join("outputs", "datasets", "mood_dataset_sentence")
    LOG_DIR = os.path.join("outputs", "logs")

    # Training settings
    TEST_SPLIT = 0.2
    SEED = 42
    BATCH_SIZE = 2
    EPOCHS = 5
    LEARNING_RATE = 2e-5
    GRADIENT_ACCUMULATION_STEPS = 8  # simulate bigger batch
    FP16 = True  # use mixed precision

    # Labels (7 emotions)
    LABELS = ["anger", "disgust", "fear", "happy", "neutral", "sad", "surprise"]
    NUM_LABELS = len(LABELS)
