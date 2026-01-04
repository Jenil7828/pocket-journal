"""
Training package for RoBERTa-based mood detection.

This module contains:
- Dataset loading
- Training logic
- Evaluation utilities

⚠️ IMPORTANT:
- This package is for OFFLINE TRAINING ONLY
- Do NOT import this package inside Flask / inference code
- Do NOT bake this into Docker images
"""

from .config import Config
from .dataset_loader import SentenceDatasetLoader
from .trainer import SentenceTrainer
from .evaluator import SentenceLevelMoodEvaluator

__all__ = [
    "Config",
    "SentenceDatasetLoader",
    "SentenceTrainer",
    "SentenceLevelMoodEvaluator",
]
