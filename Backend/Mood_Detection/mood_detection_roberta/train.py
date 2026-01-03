#!/usr/bin/env python3
"""
Enhanced RoBERTa-based mood detection training script
Optimized for overlapping/mixed emotions detection
"""

import os
# import sys
# import torch
from .trainer import SentenceTrainer
from .evaluator import SentenceLevelMoodEvaluator
# from .predictor import SentencePredictor
from .config import Config

def main():
    print("🎭 Enhanced RoBERTa Mood Detection Training")
    print("=" * 50)
    
    # Check if data directory exists
    data_dir = "../data"  # Path to Mood_Detection/data
    if not os.path.exists(data_dir):
        print(f"❌ Data directory not found: {data_dir}")
        print("Please ensure your emotion-labeled data is in the '../data' directory")
        return
    
    # Initialize trainer
    print("🚀 Initializing enhanced trainer...")
    trainer = SentenceTrainer()
    
    # Start training
    print(f"📊 Dataset loaded: {len(trainer.dataset)} samples")
    print(f"🏷️  Labels: {trainer.labels}")
    print(f"⚙️  Configuration:")
    print(f"   - Epochs: {Config.EPOCHS}")
    print(f"   - Batch size: {Config.BATCH_SIZE}")
    print(f"   - Learning rate: {Config.LEARNING_RATE}")
    print(f"   - Prediction threshold: {Config.PREDICTION_THRESHOLD}")
    print(f"   - Class weighting: {Config.USE_CLASS_WEIGHTING}")
    
    # Train the model
    trainer.train()
    
    print("\n🔍 Evaluating model performance...")
    
    # Load the trained model for evaluation
    evaluator = SentenceLevelMoodEvaluator(
        model_dir=Config.OUTPUT_DIR,
        labels=Config.LABELS
    )
    
    # Test with sample text
    sample_texts = [
        "I'm so excited about my new job but also nervous about the challenges ahead!",
        "I feel angry and disappointed about what happened yesterday.",
        "I'm happy to see my family but sad that my friend couldn't make it."
    ]
    
    print("\n📝 Sample predictions:")
    for i, text in enumerate(sample_texts, 1):
        print(f"\nText {i}: {text}")
        analysis, predictions = evaluator.get_emotion_analysis(text)
        
        print("Emotion probabilities:")
        for emotion, prob in analysis.items():
            print(f"{emotion}: {prob:.6f}")
        
        active_emotions = [emotion for emotion, pred in zip(Config.LABELS, predictions) if pred]
        print(f"Active emotions: {active_emotions}")
    
    print(f"\n✅ Training complete! Model saved to: {Config.OUTPUT_DIR}")
    print("🎯 Model optimized for overlapping/mixed emotions detection")

if __name__ == "__main__":
    main()
