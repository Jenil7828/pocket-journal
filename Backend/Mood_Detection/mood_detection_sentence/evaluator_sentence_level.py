import re
import torch
import numpy as np
from collections import Counter
from sklearn.metrics import accuracy_score, f1_score, hamming_loss
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from datasets import load_from_disk


class SentenceLevelMoodEvaluator:
    def __init__(self, model_dir: str, labels: list, device: str = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = AutoModelForSequenceClassification.from_pretrained(model_dir).to(self.device)
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.labels = labels

    def split_sentences(self, text: str):
        return [s for s in re.split(r'(?<=[.!?])\s+', text.strip()) if s]

    def predict(self, text: str, threshold: float = 0.35, mode: str = "max"):
        sentences = self.split_sentences(text)
        all_probs = []

        for sent in sentences:
            inputs = self.tokenizer(sent, return_tensors="pt", truncation=True, padding=True).to(self.device)
            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = torch.sigmoid(outputs.logits).cpu().numpy()[0]
            all_probs.append(probs)

        all_probs = torch.tensor(all_probs)

        if mode == "max":
            agg_probs = all_probs.max(dim=0).values.numpy()
        elif mode == "mean":
            agg_probs = all_probs.mean(dim=0).numpy()
        elif mode == "vote":
            preds = all_probs.argmax(dim=1).numpy()
            counts = Counter(preds)
            agg_probs = np.zeros(len(self.labels))
            agg_probs[counts.most_common(1)[0][0]] = 1.0
        elif mode == "hybrid":
            mean_probs = all_probs.mean(dim=0).numpy()
            max_probs = all_probs.max(dim=0).values.numpy()
            agg_probs = 0.7 * mean_probs + 0.3 * max_probs
        else:
            raise ValueError(f"Unknown mode: {mode}")

        final_labels = [1 if p >= threshold else 0 for p in agg_probs]
        return dict(zip(self.labels, agg_probs.tolist())), final_labels

    def evaluate(self, dataset, threshold=0.35):
        strategies = ["max", "mean", "vote", "hybrid"]
        results = {}
        y_true = np.array(dataset["label"])

        for mode in strategies:
            y_pred = []
            for text, labels in zip(dataset["text"], dataset["label"]):
                _, pred_labels = self.predict(text, threshold=threshold, mode=mode)
                y_pred.append(pred_labels)

            y_pred = np.array(y_pred)
            acc = accuracy_score(y_true, y_pred)
            f1 = f1_score(y_true, y_pred, average="weighted", zero_division=0)
            hamming = hamming_loss(y_true, y_pred)

            results[mode] = {"accuracy": round(acc, 4), "f1": round(f1, 4), "hamming_loss": round(hamming, 4)}

        return results
