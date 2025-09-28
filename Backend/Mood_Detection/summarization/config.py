import os
import torch

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT_DIR, "../data")
OUTPUT_DIR = os.path.join(ROOT_DIR, "../outputs/summarizer")

# Summarization specific
NUM_EPOCHS = 3
BATCH_SIZE = 2               # smaller because BART is bigger
LEARNING_RATE = 3e-5
MAX_INPUT_LENGTH = 1024
MAX_SUMMARY_LENGTH = 128
MIN_SUMMARY_LENGTH = 20
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# import os
# import torch
#
# ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
# DATA_DIR = os.path.join(ROOT_DIR, "data")
# OUTPUTS_DIR = os.path.join(ROOT_DIR, "outputs")
#
# # Mood Detection
# MOOD_MODEL_DIR = os.path.join(OUTPUTS_DIR, "mood_model")
#
# # Summarization
# SUMMARIZER_MODEL_DIR = os.path.join(OUTPUTS_DIR, "summarizer")
#
# # Training Hyperparameters
# TRAIN_EPOCHS = 3
# BATCH_SIZE = 2
# LEARNING_RATE = 3e-5
# MAX_INPUT_LENGTH = 1024
# MAX_SUMMARY_LENGTH = 128
# MIN_SUMMARY_LENGTH = 20
# DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
