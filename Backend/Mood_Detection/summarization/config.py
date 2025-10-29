import os
import torch
import pandas as pd

class Config:
    # Model settings
    MODEL_NAME = "facebook/bart-large-cnn"
    
    # Paths
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    OUTPUT_DIR = os.path.join(BASE_DIR, "Mood_Detection", "outputs", "models", "summarizer")
    DATASET_PATH = os.path.join(ROOT_DIR, "summary.csv")
    LOG_DIR = os.path.join(BASE_DIR, "Mood_Detection", "outputs", "logs")
    
    # Training settings
    TEST_SPLIT = 0.2
    VALIDATION_SPLIT = 0.1
    SEED = 42
    
    # Auto-detect batch size based on GPU memory
    @staticmethod
    def get_batch_size():
        if torch.cuda.is_available():
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9  # GB
            if gpu_memory >= 16:
                return 8
            elif gpu_memory >= 8:
                return 4
            elif gpu_memory >= 4:
                return 2
            else:
                return 1
        return 1
    
    BATCH_SIZE = get_batch_size()
    LEARNING_RATE = 3e-5
    EPOCHS = 3
    GRADIENT_ACCUMULATION_STEPS = 4
    FP16 = torch.cuda.is_available()
    WARMUP_STEPS = 100
    WEIGHT_DECAY = 0.01
    
    # Sequence lengths
    MAX_INPUT_LENGTH = 1024
    MAX_SUMMARY_LENGTH = 128
    MIN_SUMMARY_LENGTH = 20
    
    # Evaluation settings
    EVAL_STEPS = 500
    SAVE_STEPS = 500
    LOGGING_STEPS = 100
    
    # Device detection
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    
    # Column detection for CSV
    @staticmethod
    def detect_columns(csv_path):
        """Automatically detect text and summary columns in CSV"""
        try:
            df = pd.read_csv(csv_path)
            text_col = None
            summary_col = None
            
            # Look for common column names
            for col in df.columns:
                col_lower = col.lower()
                if any(keyword in col_lower for keyword in ['text', 'input', 'source', 'article', 'content', 'paragraph']):
                    text_col = col
                elif any(keyword in col_lower for keyword in ['summary', 'target', 'reference', 'abstract']):
                    summary_col = col
            
            # Fallback: use positional columns
            if text_col is None:
                text_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
            if summary_col is None:
                summary_col = df.columns[2] if len(df.columns) > 2 else df.columns[1]
            
            return text_col, summary_col
            
        except Exception as e:
            print(f"Error detecting columns: {e}")
            return "text", "summary"
    
    # Get detected columns
    TEXT_COLUMN, SUMMARY_COLUMN = detect_columns(DATASET_PATH)
