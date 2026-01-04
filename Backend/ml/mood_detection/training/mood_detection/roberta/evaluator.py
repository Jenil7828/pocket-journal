import re
import torch
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    hamming_loss,
    precision_recall_fscore_support
)
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from .config import Config


class SentenceLevelMoodEvaluator:
    """
    Sentence-level evaluator for multi-label emotion classification.
    Used ONLY in training / experimentation.
    """

    def __init__(self, model_dir: str, labels: list, device: str = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_dir
        ).to(self.device)

        self.model.eval()
        self.labels = labels
        self.threshold = Config.PREDICTION_THRESHOLD

    # ---------- TEXT PROCESSING ----------

    @staticmethod
    def split_sentences(text: str):
        """Robust sentence splitting"""
        return [
            s.strip()
            for s in re.split(r"(?<=[.!?])\s+", text.strip())
            if s.strip()
        ]

    def predict_sentence(self, sentence: str):
        inputs = self.tokenizer(
            sentence,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=Config.MAX_LENGTH
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.sigmoid(outputs.logits).cpu().numpy()[0]

        return probs

    # ---------- AGGREGATION ----------

    def aggregate_sentence_probabilities(self, all_probs, mode="hybrid"):
        all_probs = torch.tensor(all_probs)

        if mode == "max":
            return all_probs.max(dim=0).values.numpy()

        if mode == "mean":
            return all_probs.mean(dim=0).numpy()

        if mode == "hybrid":
            mean_probs = all_probs.mean(dim=0).numpy()
            max_probs = all_probs.max(dim=0).values.numpy()
            return 0.7 * mean_probs + 0.3 * max_probs

        raise ValueError(f"Unknown aggregation mode: {mode}")

    # ---------- PREDICTION ----------

    def predict(self, text: str, threshold=None, mode=None):
        threshold = threshold or self.threshold
        mode = mode or Config.DEFAULT_AGGREGATION_MODE

        sentences = self.split_sentences(text)
        if not sentences:
            return {label: 0.0 for label in self.labels}, [0] * len(self.labels)

        all_probs = [self.predict_sentence(s) for s in sentences]
        agg_probs = self.aggregate_sentence_probabilities(all_probs, mode)

        predictions = [1 if p >= threshold else 0 for p in agg_probs]
        prob_dict = dict(zip(self.labels, agg_probs.tolist()))

        return prob_dict, predictions

    # ---------- EVALUATION ----------

    def evaluate_aggregation_modes(self, dataset):
        results = {}
        y_true = np.array(dataset["labels"])

        for mode in Config.AGGREGATION_MODES:
            y_pred = []

            for text in dataset["text"]:
                _, preds = self.predict(text, mode=mode)
                y_pred.append(preds)

            y_pred = np.array(y_pred)

            precision, recall, f1, _ = precision_recall_fscore_support(
                y_true, y_pred, average="micro", zero_division=0
            )

            results[mode] = {
                "accuracy": accuracy_score(y_true, y_pred),
                "f1_micro": f1,
                "precision": precision,
                "recall": recall,
                "hamming_loss": hamming_loss(y_true, y_pred),
            }

        return results

    def evaluate_thresholds(self, dataset, thresholds=None):
        thresholds = thresholds or [0.1, 0.2, 0.3, 0.35, 0.4, 0.5]
        results = {}
        y_true = np.array(dataset["labels"])

        for threshold in thresholds:
            y_pred = []

            for text in dataset["text"]:
                _, preds = self.predict(text, threshold=threshold)
                y_pred.append(preds)

            y_pred = np.array(y_pred)

            results[threshold] = {
                "accuracy": accuracy_score(y_true, y_pred),
                "f1_micro": f1_score(y_true, y_pred, average="micro", zero_division=0),
                "hamming_loss": hamming_loss(y_true, y_pred),
            }

        return results

    # ---------- PUBLIC API ----------

    def get_emotion_analysis(self, text, threshold=None, mode=None):
        return self.predict(text, threshold, mode)
