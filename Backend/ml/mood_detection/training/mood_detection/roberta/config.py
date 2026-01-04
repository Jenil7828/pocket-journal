import os

class Config:
    MODEL_NAME = "roberta-base"
    MAX_LENGTH = 128

    # Backend/ml/mood_detection
    ML_ROOT = os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))
            )
        )
    )

    # Backend/
    BACKEND_ROOT = os.path.dirname(ML_ROOT)

    # Backend/data
    DATA_ROOT = os.path.join(BACKEND_ROOT, "data")

    # Mood detection dataset
    DATASET_DIR = os.path.join(DATA_ROOT, "mood_detection_data")

    # Model output (NOT baked into docker)
    OUTPUT_DIR = os.path.join(
        ML_ROOT, "models", "mood_detection", "roberta", "v1"
    )

    LOG_DIR = os.path.join(ML_ROOT, "training_logs")

    TEST_SPLIT = 0.2
    SEED = 42
    BATCH_SIZE = 2
    EPOCHS = 8
    LEARNING_RATE = 2e-5
    GRADIENT_ACCUMULATION_STEPS = 8
    FP16 = True

    USE_CLASS_WEIGHTING = True
    # ======== Inference settings ========
    PREDICTION_THRESHOLD = 0.35

    AGGREGATION_MODES = ["mean", "max", "hybrid"]
    DEFAULT_AGGREGATION_MODE = "hybrid"

    LABELS = ["anger", "disgust", "fear", "happy", "neutral", "sad", "surprise"]
    NUM_LABELS = len(LABELS)
