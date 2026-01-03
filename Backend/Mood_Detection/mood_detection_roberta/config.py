import os

class Config:
    # Model settings
    MODEL_NAME = "roberta-base"
    MAX_LENGTH = 128

    # Paths (absolute paths)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    OUTPUT_DIR = os.path.join(BASE_DIR, "Mood_Detection", "outputs", "models", "mood_detector")
    DATASET_DIR = os.path.join(BASE_DIR, "Mood_Detection", "outputs", "datasets", "mood_dataset_sentence")
    LOG_DIR = os.path.join(BASE_DIR, "Mood_Detection", "outputs", "logs")

    # Enhanced training settings for better overlapping emotion learning
    TEST_SPLIT = 0.2
    SEED = 42
    BATCH_SIZE = 2  # Reduced for 4GB Virtual RAM
    EPOCHS = 8  # Reduced for faster training
    LEARNING_RATE = 2e-5
    GRADIENT_ACCUMULATION_STEPS = 8  # Increased to maintain effective batch size
    FP16 = True  # use mixed precision for memory efficiency
    
    # Class weighting for imbalanced datasets
    USE_CLASS_WEIGHTING = True
    
    # Prediction threshold for multi-label classification
    PREDICTION_THRESHOLD = 0.35
    
    # Sentence aggregation modes
    AGGREGATION_MODES = ["mean", "max", "hybrid"]
    DEFAULT_AGGREGATION_MODE = "hybrid"  # Combines mean and max for better overlapping emotion detection

    # Labels (7 emotions)
    LABELS = ["anger", "disgust", "fear", "happy", "neutral", "sad", "surprise"]
    NUM_LABELS = len(LABELS)
