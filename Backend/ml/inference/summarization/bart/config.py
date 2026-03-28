import os
import sys
import torch

# Add Backend to path for config access
_HERE = os.path.dirname(os.path.abspath(__file__))
# Walk up: bart → summarization → inference → ml → Backend
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
    # Base model (used only if fine-tuned model missing)
    MODEL_NAME = str(_CFG["ml"]["summarization"]["model_name"])

    # Backend/
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

    # Inference-only model directory
    _version = _CFG["ml"]["summarization"].get("model_version", "v1")
    OUTPUT_DIR = os.path.join(
        _models_base,
        "summarization",
        "bart",
        _version
    )

    # Generation defaults (from config)
    MAX_INPUT_LENGTH = int(_CFG["ml"]["summarization"]["max_input_length"])
    MAX_SUMMARY_LENGTH = int(_CFG["ml"]["summarization"]["max_summary_length"])
    MIN_SUMMARY_LENGTH = int(_CFG["ml"]["summarization"]["min_summary_length"])
    NUM_BEAMS = int(_CFG["ml"]["summarization"]["num_beams"])

    # Device policy (hard-safe for prod)
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


