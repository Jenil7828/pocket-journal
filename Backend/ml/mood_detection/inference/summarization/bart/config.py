import os
import sys
import torch

# Add Backend to path for config access
_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.join(_HERE, "..", "..", "..", "..")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from config_loader import get_config

_CFG = get_config()

class Config:
    # Base model (used only if fine-tuned model missing)
    MODEL_NAME = str(_CFG["ml"]["summarization"]["model_name"])

    # Backend/
    BASE_DIR = os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))
            )
        )
    )

    # Inference-only model directory
    OUTPUT_DIR = os.path.join(
        BASE_DIR,
        "ml",
        "mood_detection",
        "models",
        "summarization",
        "bart",
        "v1"
    )

    # Generation defaults (from config)
    MAX_INPUT_LENGTH = int(_CFG["ml"]["summarization"]["max_input_length"])
    MAX_SUMMARY_LENGTH = int(_CFG["ml"]["summarization"]["max_summary_length"])
    MIN_SUMMARY_LENGTH = int(_CFG["ml"]["summarization"]["min_summary_length"])
    NUM_BEAMS = int(_CFG["ml"]["summarization"]["num_beams"])

    # Device policy (hard-safe for prod)
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
