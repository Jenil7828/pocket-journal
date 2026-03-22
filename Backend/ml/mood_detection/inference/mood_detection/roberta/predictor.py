import os
import torch
import numpy as np
import logging
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from services.suppression import suppress_hf
from .config import Config

logger = logging.getLogger("pocket_journal.roberta.predictor")


class SentencePredictor:
    def __init__(self, model_path: str = Config.OUTPUT_DIR):
        self.labels = Config.LABELS
        self.threshold = Config.PREDICTION_THRESHOLD
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info("RoBERTa mood predictor using device=%s", self.device)

        if os.path.exists(model_path) and os.path.exists(os.path.join(model_path, "config.json")):
            # suppress materialization output during local model load
            with suppress_hf():
                self.tokenizer = AutoTokenizer.from_pretrained(model_path)
                self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
        else:
            # fallback to base model
            with suppress_hf():
                self.tokenizer = AutoTokenizer.from_pretrained(Config.MODEL_NAME)
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    Config.MODEL_NAME,
                    num_labels=Config.NUM_LABELS,
                    problem_type="multi_label_classification",
                )

        if self.device == "cuda":
            self.model = self.model.half()
        self.model.to(self.device)
        self.model.eval()

    def predict(self, text: str, threshold: float | None = None) -> dict:
        threshold = threshold or self.threshold

        tokens = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=Config.MAX_LENGTH,
        )

        tokens = {k: v.to(self.device) for k, v in tokens.items()}

        with torch.no_grad():
            logits = self.model(**tokens).logits.cpu().numpy()[0]

        probs = 1 / (1 + np.exp(-logits))
        preds = (probs >= threshold).astype(int)

        return {
            "probabilities": {l: float(p) for l, p in zip(self.labels, probs)},
            "predictions": {l: bool(p) for l, p in zip(self.labels, preds)},
            "threshold": threshold,
        }

    def predict_batch(self, texts: list[str], threshold: float | None = None) -> list[dict]:
        return [self.predict(t, threshold) for t in texts]

    def get_emotion_probabilities(self, text: str, threshold: float | None = None) -> dict:
        return self.predict(text, threshold)["probabilities"]
