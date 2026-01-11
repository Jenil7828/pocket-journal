#!/usr/bin/env python3
"""
Evaluation script for trained summarization model
Evaluates model performance using ROUGE metrics
"""

import argparse
import os
import sys

# Handle both module and direct script execution
try:
    from .evaluator import SummarizationEvaluator
    from .dataset_loader import SummarizationDatasetLoader
    from .config import Config
except ImportError:
    # When running as script, add current directory to path
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    try:
        from .evaluator import SummarizationEvaluator
        from .dataset_loader import SummarizationDatasetLoader
        from .config import Config
    except ImportError:
        from evaluator import SummarizationEvaluator
        from dataset_loader import SummarizationDatasetLoader
        from config import Config

def main():
    parser = argparse.ArgumentParser(description="Evaluate summarization model")
    parser.add_argument("--model-dir", default=None, help="Path to trained model directory")
    parser.add_argument("--max-samples", type=int, default=None, help="Maximum samples to evaluate")
    parser.add_argument("--compare-baseline", action="store_true", help="Compare with extractive baseline")
    
    args = parser.parse_args()
    
    print("🔍 Loading evaluator...")
    evaluator = SummarizationEvaluator(model_dir=args.model_dir)
    
    print("📊 Loading test dataset...")
    loader = SummarizationDatasetLoader()
    dataset = loader.create_dataset()["test"]
    
    print(f"🧪 Evaluating on {len(dataset)} test samples...")
    metrics, predictions, references = evaluator.evaluate_dataset(
        dataset, 
        max_samples=args.max_samples
    )
    
    # Print results
    evaluator.print_evaluation_results(metrics)
    
    # Compare with baseline if requested
    if args.compare_baseline:
        print("\n📊 Comparing with baseline...")
        evaluator.compare_with_baseline(dataset, max_samples=args.max_samples or 100)
    
    print("\n✅ Evaluation complete!")

if __name__ == "__main__":
    main()
