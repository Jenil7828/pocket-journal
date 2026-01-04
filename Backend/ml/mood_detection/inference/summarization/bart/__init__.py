# BART-based text summarization module
from .config import Config
from .predictor import SummarizationPredictor

__all__ = [
    "Config",
    "SummarizationPredictor"
]
