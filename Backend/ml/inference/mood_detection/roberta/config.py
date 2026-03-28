import os
import sys

# Add Backend to path for config access
_HERE = os.path.dirname(os.path.abspath(__file__))
# Walk up: roberta → mood_detection → inference → ml → Backend
_BACKEND_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(_HERE)
            )
        )
    )
)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from config_loader import get_config

_CFG = get_config()

class Config:
    # Model settings (from config)
    MODEL_NAME = str(_CFG["ml"]["mood_detection"]["model_name"])
    MAX_LENGTH = int(_CFG["ml"]["mood_detection"]["max_length"])

    # Base directory = Backend/
    BASE_DIR = _BACKEND_DIR

    # Determine model base directory
    # If ML_MODELS_BASE_DIR is set in config, use that; otherwise use Backend/ml/models/
    _custom_models_dir = _CFG["ml"].get("models_base_dir", "").strip()
    if _custom_models_dir:
        # Custom external models directory
        if os.path.isabs(_custom_models_dir):
            _models_base = _custom_models_dir
        else:
            # Relative to Backend/
            _models_base = os.path.join(BASE_DIR, _custom_models_dir)
    else:
        # Default: Backend/ml/models/
        _models_base = os.path.join(BASE_DIR, "ml", "models")

    # Inference-only model path
    _version = _CFG["ml"]["mood_detection"].get("model_version", "v1")
    OUTPUT_DIR = os.path.join(
        _models_base,
        "mood_detection",
        "roberta",
        _version
    )

    # Prediction config (from config)
    PREDICTION_THRESHOLD = float(_CFG["ml"]["mood_detection"]["prediction_threshold"])

    # Labels (from config)
    LABELS = list(_CFG["ml"]["mood_detection"]["labels"])
    NUM_LABELS = len(LABELS)


