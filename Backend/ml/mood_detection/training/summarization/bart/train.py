#!/usr/bin/env python3
"""
BART-based text summarization training script
PRINTS evaluation metrics to logs after training
"""

import os
from datasets import Dataset

from .trainer import SummarizationTrainer
from .evaluator import SummarizationEvaluator
from .dataset_loader import SummarizationDatasetLoader
from .config import Config


def main():
    print("📝 BART Text Summarization Training")
    print("=" * 60)

    # ------------------ DATA CHECK ------------------
    if not os.path.exists(Config.DATASET_PATH):
        raise FileNotFoundError(f"Dataset not found: {Config.DATASET_PATH}")

    # ------------------ TRAIN ------------------
    trainer = SummarizationTrainer()
    hf_trainer = trainer.train()

    # ------------------ EVALUATE ------------------
    print("\n🔍 STARTING EVALUATION (LOGGING ENABLED)")
    print("=" * 60)

    evaluator = SummarizationEvaluator()

    loader = SummarizationDatasetLoader()
    texts, summaries, _, _ = loader.load_csv_data()

    eval_dataset = Dataset.from_dict({
        "text": texts[:100],
        "summary": summaries[:100]
    })

    metrics, _, _ = evaluator.evaluate_dataset(
        eval_dataset,
        max_samples=100
    )

    # 🔥 THIS IS WHAT YOU WERE MISSING
    print("\n📊 EVALUATION METRICS")
    print("=" * 60)
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"{key:<30}: {value:.4f}")
        else:
            print(f"{key:<30}: {value}")

    print("\n✅ TRAINING + EVALUATION COMPLETE")
    print(f"💾 Model saved at: {Config.OUTPUT_DIR}")


if __name__ == "__main__":
    main()
