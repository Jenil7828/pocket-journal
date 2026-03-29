import os
import torch
import numpy as np
import logging
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from services.utils.suppression import suppress_hf
from .config import Config

logger = logging.getLogger("pocket_journal.roberta.predictor")


class SentencePredictor:
    def __init__(self, model_path: str = Config.OUTPUT_DIR):
        self.labels = Config.LABELS
        self.threshold = Config.PREDICTION_THRESHOLD
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._use_onnx = False
        logger.info("RoBERTa mood predictor using device=%s", self.device)

        self.model_path = model_path
        self._load_model()

    def _load_model(self):
        model_exists = (
            os.path.exists(self.model_path)
            and os.path.exists(os.path.join(self.model_path, "config.json"))
        )
        load_from = self.model_path if model_exists else Config.MODEL_NAME

        if model_exists:
            logger.info("Loading RoBERTa via PyTorch from %s", self.model_path)
        else:
            logger.warning(
                "RoBERTa model not found at %s — loading base model %s",
                self.model_path, Config.MODEL_NAME
            )

        with suppress_hf():
            self.tokenizer = AutoTokenizer.from_pretrained(load_from)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                load_from,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            )

        self.model.to(self.device)
        self.model.eval()
        self._use_onnx = False
        logger.info(
            "RoBERTa loaded successfully device=%s dtype=%s",
            self.device,
            "float16" if self.device == "cuda" else "float32"
        )

    def predict(self, text: str, threshold: float | None = None) -> dict:
        threshold = threshold or self.threshold

        tokens = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=Config.MAX_LENGTH,
        )

        if not self._use_onnx:
            tokens = {k: v.to(self.device) for k, v in tokens.items()}

        with torch.no_grad():
            logits = self.model(**tokens).logits
            if hasattr(logits, "cpu"):
                logits = logits.cpu()
            logits = logits.float().numpy()[0]

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


