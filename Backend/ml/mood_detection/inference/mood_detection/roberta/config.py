import os

class Config:
    # Model settings
    MODEL_NAME = "roberta-base"
    MAX_LENGTH = 128

    # Base directory = Backend/
    BASE_DIR = os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))
            )
        )
    )

    # Inference-only model path (mounted or baked explicitly)
    OUTPUT_DIR = os.path.join(
        BASE_DIR,
        "ml",
        "mood_detection",
        "models",
        "mood_detection",
        "roberta",
        "v1"
    )

    # Prediction config
    PREDICTION_THRESHOLD = 0.35

    # Labels
    LABELS = ["anger", "disgust", "fear", "happy", "neutral", "sad", "surprise"]
    NUM_LABELS = len(LABELS)