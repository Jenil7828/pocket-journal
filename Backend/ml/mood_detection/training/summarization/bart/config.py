import os
import torch
import pandas as pd

class Config:
    """
    Configuration for BART summarization TRAINING ONLY.
    This file must NEVER be imported by Flask or inference code.
    """

    # =========================
    # Model
    # =========================
    MODEL_NAME = "facebook/bart-large-cnn"

    # =========================
    # Paths
    # =========================
    # bart/
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

    # training/
    TRAINING_DIR = os.path.dirname(CURRENT_DIR)

    # summarization/
    SUMMARIZATION_DIR = os.path.dirname(TRAINING_DIR)

    # ml/
    ML_DIR = os.path.dirname(SUMMARIZATION_DIR)

    # Backend/
    BACKEND_DIR = os.path.dirname(ML_DIR)

    # data/ (same level as ml/)
    DATA_DIR = os.path.join(BACKEND_DIR, "data", "summarization_data")

    DATASET_PATH = os.path.join(DATA_DIR, "summary.csv")

    OUTPUT_DIR = os.path.join(
        BACKEND_DIR,
        "ml",
        "models",
        "summarization",
        "bart",
        "v1"
    )

    LOG_DIR = os.path.join(OUTPUT_DIR, "logs")

    # =========================
    # Training
    # =========================
    TEST_SPLIT = 0.2
    VALIDATION_SPLIT = 0.1
    SEED = 42

    LEARNING_RATE = 3e-5
    EPOCHS = 3
    GRADIENT_ACCUMULATION_STEPS = 4
    WEIGHT_DECAY = 0.01
    WARMUP_STEPS = 100

    # =========================
    # Sequence Lengths
    # =========================
    MAX_INPUT_LENGTH = 1024
    MAX_SUMMARY_LENGTH = 128
    MIN_SUMMARY_LENGTH = 20

    # =========================
    # Device / Performance
    # =========================
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    FP16 = torch.cuda.is_available()

    @staticmethod
    def get_batch_size():
        if not torch.cuda.is_available():
            return 1

        gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1e9
        if gpu_mem >= 16:
            return 8
        if gpu_mem >= 8:
            return 4
        if gpu_mem >= 4:
            return 2
        return 1

    BATCH_SIZE = get_batch_size()

    # =========================
    # CSV Column Detection
    # =========================
    @staticmethod
    def detect_columns(csv_path):
        try:
            df = pd.read_csv(csv_path)
            text_col, summary_col = None, None

            for col in df.columns:
                cl = col.lower()
                if any(k in cl for k in ["text", "content", "article", "entry"]):
                    text_col = col
                elif any(k in cl for k in ["summary", "abstract", "target"]):
                    summary_col = col

            if text_col is None:
                text_col = df.columns[0]
            if summary_col is None:
                summary_col = df.columns[1]

            return text_col, summary_col
        except Exception:
            return "text", "summary"

    TEXT_COLUMN, SUMMARY_COLUMN = detect_columns(DATASET_PATH)
