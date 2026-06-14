"""Deprecated local Qwen2 predictor stub.

This module remains present for historical reference only. The project no
longer ships or initializes a local Qwen2 model. Attempting to instantiate
the InsightsPredictor will raise a RuntimeError with guidance on supported
alternatives (Gemini or Ollama).
"""

from typing import Any


class InsightsPredictor:
    """Stub replacement for removed Qwen2 predictor.

    Instantiating this class will raise a RuntimeError to prevent accidental
    usage of the removed local Qwen2 model artifacts.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise RuntimeError(
            "Local Qwen2 predictor is deprecated and removed from this build. "
            "Use the cloud Gemini backend (set ml.insight_generation.use_gemini=true) "
            "or run an Ollama server and configure ml.insight_generation.backend=ollama. "
            "See Documentation/Project/CONFIGURATION.md for details."
        )

