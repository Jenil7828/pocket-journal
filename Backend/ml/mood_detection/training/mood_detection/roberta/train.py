import os
from .trainer import SentenceTrainer
from .evaluator import SentenceLevelMoodEvaluator
from .config import Config


def main():
    print("🎭 Enhanced RoBERTa Mood Detection Training")
    print("=" * 60)

    # ===== SAFETY CHECK: DATA =====
    if not os.path.exists(Config.DATASET_DIR):
        print(f"❌ Dataset directory not found:")
        print(f"   {Config.DATASET_DIR}")
        print("Ensure data exists under Backend/data/mood_detection_data/")
        return

    # ===== TRAINING =====
    print("🚀 Initializing trainer...")
    trainer = SentenceTrainer()

    print(f"📊 Samples loaded: {len(trainer.dataset)}")
    print(f"🏷️  Labels: {trainer.labels}")
    print("⚙️  Training configuration:")
    print(f"   • Epochs: {Config.EPOCHS}")
    print(f"   • Batch size: {Config.BATCH_SIZE}")
    print(f"   • Learning rate: {Config.LEARNING_RATE}")
    print(f"   • Gradient accumulation: {Config.GRADIENT_ACCUMULATION_STEPS}")
    print(f"   • Threshold: {Config.PREDICTION_THRESHOLD}")
    print(f"   • Class weighting: {Config.USE_CLASS_WEIGHTING}")

    trainer.train()

    # ===== EVALUATION =====
    print("\n🔍 Running post-training evaluation...")
    evaluator = SentenceLevelMoodEvaluator(
        model_dir=Config.OUTPUT_DIR,
        labels=Config.LABELS
    )

    sample_texts = [
        "I'm so excited about my new job but also nervous about the challenges ahead!",
        "I feel angry and disappointed about what happened yesterday.",
        "I'm happy to see my family but sad that my friend couldn't make it."
    ]

    print("\n📝 Sample Predictions:")
    for i, text in enumerate(sample_texts, 1):
        print(f"\nText {i}: {text}")
        analysis, predictions = evaluator.get_emotion_analysis(text)

        for emotion, prob in analysis.items():
            print(f"  {emotion}: {prob:.6f}")

        active = [
            label for label, flag in zip(Config.LABELS, predictions) if flag
        ]
        print(f"  → Active emotions: {active}")

    print("\n✅ Training complete")
    print(f"📦 Model saved at: {Config.OUTPUT_DIR}")
    print("🎯 Optimized for overlapping / mixed emotions")


if __name__ == "__main__":
    main()
