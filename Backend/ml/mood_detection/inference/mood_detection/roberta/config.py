import os
import sys

# Add Backend to path for config access
_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.join(_HERE, "..", "..", "..", "..")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from config_loader import get_config

_CFG = get_config()

class Config:
    # Model settings (from config)
    MODEL_NAME = str(_CFG["ml"]["mood_detection"]["model_name"])
    MAX_LENGTH = int(_CFG["ml"]["mood_detection"]["max_length"])

    # Base directory = Backend/
    BASE_DIR = os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))
            )
        )
    )

    # Inference-only model path (mounted or baked explicitly)
    _version = _CFG["ml"]["mood_detection"].get("model_version", "v1")
    OUTPUT_DIR = os.path.join(
        BASE_DIR,
        "ml",
        "mood_detection",
        "models",
        "mood_detection",
        "roberta",
        _version
    )

    # Prediction config (from config)
    PREDICTION_THRESHOLD = float(_CFG["ml"]["mood_detection"]["prediction_threshold"])

    # Labels (from config)
    LABELS = list(_CFG["ml"]["mood_detection"]["labels"])
    NUM_LABELS = len(LABELS)

