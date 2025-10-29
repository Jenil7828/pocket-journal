#!/usr/bin/env python3
"""
BART-based text summarization training script
Fine-tunes facebook/bart-large-cnn on local CSV dataset
"""

import os
import sys
import torch

# Handle both module and direct script execution
try:
    from .trainer import SummarizationTrainer
    from .evaluator import SummarizationEvaluator
    from .predictor import SummarizationPredictor
    from .dataset_loader import SummarizationDatasetLoader
    from .config import Config
except ImportError:
    # When running as script, add current directory to path
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    try:
        from .trainer import SummarizationTrainer
        from .evaluator import SummarizationEvaluator
        from .predictor import SummarizationPredictor
        from .dataset_loader import SummarizationDatasetLoader
        from .config import Config
    except ImportError:
        from trainer import SummarizationTrainer
        from evaluator import SummarizationEvaluator
        from predictor import SummarizationPredictor
        from dataset_loader import SummarizationDatasetLoader
        from config import Config

def main():
    print("📝 BART Text Summarization Training")
    print("=" * 50)
    
    # Check if dataset exists
    if not os.path.exists(Config.DATASET_PATH):
        print(f"❌ Dataset not found: {Config.DATASET_PATH}")
        print("Please ensure your CSV dataset is available")
        return
    
    # Display dataset statistics
    print("📊 Dataset Information:")
    loader = SummarizationDatasetLoader()
    stats = loader.get_data_statistics()
    
    if stats:
        print(f"   - Total samples: {stats['total_samples']}")
        print(f"   - Text length: {stats['text_length_stats']['mean']:.1f} ± {stats['text_length_stats']['std']:.1f} chars")
        print(f"   - Summary length: {stats['summary_length_stats']['mean']:.1f} ± {stats['summary_length_stats']['std']:.1f} chars")
    
    print(f"\n⚙️ Training Configuration:")
    print(f"   - Model: {Config.MODEL_NAME}")
    print(f"   - Device: {Config.DEVICE}")
    print(f"   - Epochs: {Config.EPOCHS}")
    print(f"   - Batch size: {Config.BATCH_SIZE}")
    print(f"   - Learning rate: {Config.LEARNING_RATE}")
    print(f"   - Max input length: {Config.MAX_INPUT_LENGTH}")
    print(f"   - Max summary length: {Config.MAX_SUMMARY_LENGTH}")
    print(f"   - Text column: '{Config.TEXT_COLUMN}'")
    print(f"   - Summary column: '{Config.SUMMARY_COLUMN}'")
    
    # Initialize trainer
    print("\n🚀 Initializing trainer...")
    trainer = SummarizationTrainer()
    
    # Start training
    print("\n🔥 Starting training...")
    trained_trainer = trainer.train()
    
    # Evaluate model
    print("\n🔍 Evaluating trained model...")
    evaluator = SummarizationEvaluator()
    
    # Load test dataset for evaluation
    loader = SummarizationDatasetLoader()
    texts, summaries, text_col, summary_col = loader.load_csv_data()
    
    # Create HuggingFace Dataset for evaluation
    from datasets import Dataset
    test_dataset = Dataset.from_dict({
        "text": texts[:100],  # First 100 samples
        "summary": summaries[:100]
    })
    
    metrics, predictions, references = evaluator.evaluate_dataset(test_dataset, max_samples=100)
    
    # Print evaluation results
    evaluator.print_evaluation_results(metrics)
    
    # Compare with baseline
    print("\n📊 Comparing with baseline...")
    evaluator.compare_with_baseline(test_dataset, max_samples=50)
    
    # Test predictions
    print("\n🧪 Testing predictions...")
    predictor = SummarizationPredictor()
    
    # Sample journal entries for testing
    test_texts = [
        "This morning began with an unplanned detour that turned into a surprisingly meaningful experience, yaar. I had set out early for my usual morning jog but somehow ended up taking a wrong turn near the lake road. Instead of heading back, I decided to explore, and soon found myself in a quiet, old neighborhood filled with charming, slightly decaying houses. An elderly man was sitting outside, painting the sunrise. We exchanged a few words, and he told me he paints every morning, no matter the weather, just to remind himself that each day can start differently. That simple line struck a deep chord. We spoke for maybe ten minutes, but the calmness in his voice stayed with me for hours afterward. When I finally reached home, I felt oddly peaceful — as though that short interaction re-centered my perspective. Sometimes, wrong turns are exactly what we need, no tension.",
        
        "The entire afternoon was dominated by chaos at work. Our client presentation, which we'd been preparing for over a week, was suddenly rescheduled two hours earlier without warning. My manager was panicking, the design lead hadn't finalized the visuals, and the meeting link kept failing. It was one of those moments where your patience and adaptability are tested to the limit. I somehow managed to stitch together the last few slides while simultaneously answering messages from the client team. When we finally began, my heart was racing, but surprisingly, the presentation flowed smoothly. The client even praised the clarity of the financial models — something I'd rushed through at the last moment. After the call, everyone let out a collective sigh of relief, and we ended up ordering chai and samosas for the entire team. Exhausting? Absolutely. But the sense of shared survival made it weirdly satisfying, touchwood.",
        
        "Today's highlight was an unexpected visit from my college friend, Rashi, whom I hadn't seen in nearly five years. She was in town for a seminar and decided to drop by without warning. The moment she stepped in, the years melted away instantly. We spent hours reminiscing about our hostel life — those late-night Maggi sessions, petty fights, random crying over exams — and laughed until our cheeks hurt. What amazed me most was how, despite so much time and change, the comfort level remained untouched. We talked about careers, relationships, and the odd feeling of growing older but not necessarily wiser. As evening set in, we took a short walk to our old tea stall near the corner, which, unbelievably, still existed. That nostalgic chai felt like a time machine. When she finally left, I felt warm yet slightly hollow — a reminder of how fleeting, yet precious, human connections can be."
    ]
    
    print("\n📝 Sample Summaries:")
    for i, text in enumerate(test_texts, 1):
        print(f"\n--- Sample {i} ---")
        print(f"Original: {text}...")
        
        summary = predictor.summarize(text)
        print(f"Summary: {summary}")
        
        # Show length info
        print(f"Length: {len(summary.split())} words (compression: {len(summary.split())/len(text.split()):.2f})")
    
    print(f"\n✅ Training and evaluation complete!")
    print(f"💾 Model saved to: {Config.OUTPUT_DIR}")
    print(f"📊 Final ROUGE-1 F1: {metrics.get('rouge1_fmeasure', 'N/A')}")
    print(f"📊 Final ROUGE-2 F1: {metrics.get('rouge2_fmeasure', 'N/A')}")
    print(f"📊 Final ROUGE-L F1: {metrics.get('rougeL_fmeasure', 'N/A')}")
    
    print("\n🎯 Model is ready for inference!")
    print("Use SummarizationPredictor to generate summaries for new texts.")

if __name__ == "__main__":
    main()
