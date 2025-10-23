import re
import torch
import numpy as np
from collections import Counter
from sklearn.metrics import accuracy_score, f1_score, hamming_loss, precision_recall_fscore_support
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from .config import Config

class SentenceLevelMoodEvaluator:
    def __init__(self, model_dir: str, labels: list, device: str = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = AutoModelForSequenceClassification.from_pretrained(model_dir).to(self.device)
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.labels = labels
        self.threshold = Config.PREDICTION_THRESHOLD

    def split_sentences(self, text: str):
        """Enhanced sentence splitting for better text processing"""
        # Split on sentence boundaries but preserve context
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text.strip()) if s.strip()]
        return sentences

    def predict_sentence(self, sentence: str):
        """Predict emotions for a single sentence"""
        inputs = self.tokenizer(sentence, return_tensors="pt", truncation=True, padding=True, max_length=Config.MAX_LENGTH).to(self.device)
        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.sigmoid(outputs.logits).cpu().numpy()[0]
        return probs

    def aggregate_sentence_probabilities(self, all_probs, mode="hybrid"):
        """
        Enhanced aggregation methods for better overlapping emotion detection
        """
        all_probs = torch.tensor(all_probs)
        
        if mode == "max":
            # Take maximum probability across sentences
            agg_probs = all_probs.max(dim=0).values.numpy()
        elif mode == "mean":
            # Take average probability across sentences
            agg_probs = all_probs.mean(dim=0).numpy()
        elif mode == "hybrid":
            # Combine mean and max for better overlapping emotion detection
            mean_probs = all_probs.mean(dim=0).numpy()
            max_probs = all_probs.max(dim=0).values.numpy()
            # Weighted combination: 70% mean, 30% max
            agg_probs = 0.7 * mean_probs + 0.3 * max_probs
        elif mode == "weighted_mean":
            # Weight sentences by their confidence (higher confidence = more weight)
            confidence_weights = all_probs.max(dim=1).values.unsqueeze(1)
            weighted_probs = all_probs * confidence_weights
            agg_probs = weighted_probs.sum(dim=0).numpy() / confidence_weights.sum().numpy()
        else:
            raise ValueError(f"Unknown aggregation mode: {mode}")

        return agg_probs

    def predict(self, text: str, threshold: float = None, mode: str = None):
        """
        Enhanced prediction with better sentence-level aggregation
        """
        if threshold is None:
            threshold = self.threshold
        if mode is None:
            mode = Config.DEFAULT_AGGREGATION_MODE
            
        sentences = self.split_sentences(text)
        if not sentences:
            # Return neutral probabilities if no sentences found
            return {label: 0.0 for label in self.labels}, [0] * len(self.labels)
            
        all_probs = []
        for sent in sentences:
            probs = self.predict_sentence(sent)
            all_probs.append(probs)

        # Aggregate sentence probabilities
        agg_probs = self.aggregate_sentence_probabilities(all_probs, mode)
        
        # Apply threshold for multi-label classification
        final_labels = [1 if p >= threshold else 0 for p in agg_probs]
        
        # Format results as requested
        prob_dict = {label: float(prob) for label, prob in zip(self.labels, agg_probs)}
        
        return prob_dict, final_labels

    def evaluate_aggregation_modes(self, dataset, threshold=None):
        """
        Evaluate different aggregation modes for sentence-level prediction
        """
        if threshold is None:
            threshold = self.threshold
            
        results = {}
        y_true = np.array(dataset["labels"])

        for mode in Config.AGGREGATION_MODES:
            y_pred = []
            y_prob = []
            
            for text in dataset["text"]:
                prob_dict, pred_labels = self.predict(text, threshold=threshold, mode=mode)
                y_pred.append(pred_labels)
                y_prob.append(list(prob_dict.values()))

            y_pred = np.array(y_pred)
            y_prob = np.array(y_prob)
            
            # Calculate metrics
            acc = accuracy_score(y_true, y_pred)
            f1_micro = f1_score(y_true, y_pred, average="micro", zero_division=0)
            f1_macro = f1_score(y_true, y_pred, average="macro", zero_division=0)
            f1_weighted = f1_score(y_true, y_pred, average="weighted", zero_division=0)
            hamming = hamming_loss(y_true, y_pred)
            
            # Calculate precision and recall
            precision, recall, _, _ = precision_recall_fscore_support(y_true, y_pred, average="micro", zero_division=0)

            results[mode] = {
                "accuracy": round(acc, 4),
                "f1_micro": round(f1_micro, 4),
                "f1_macro": round(f1_macro, 4),
                "f1_weighted": round(f1_weighted, 4),
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "hamming_loss": round(hamming, 4)
            }

        return results

    def evaluate_thresholds(self, dataset, thresholds=[0.1, 0.2, 0.3, 0.35, 0.4, 0.5]):
        """
        Evaluate different thresholds for multi-label classification
        """
        results = {}
        y_true = np.array(dataset["labels"])

        for threshold in thresholds:
            y_pred = []
            
            for text in dataset["text"]:
                _, pred_labels = self.predict(text, threshold=threshold)
                y_pred.append(pred_labels)

            y_pred = np.array(y_pred)
            
            acc = accuracy_score(y_true, y_pred)
            f1_micro = f1_score(y_true, y_pred, average="micro", zero_division=0)
            f1_macro = f1_score(y_true, y_pred, average="macro", zero_division=0)
            hamming = hamming_loss(y_true, y_pred)

            results[threshold] = {
                "accuracy": round(acc, 4),
                "f1_micro": round(f1_micro, 4),
                "f1_macro": round(f1_macro, 4),
                "hamming_loss": round(hamming, 4)
            }

        return results

    def get_emotion_analysis(self, text, threshold=None, mode=None):
        """
        Get detailed emotion analysis in the requested format
        """
        prob_dict, pred_labels = self.predict(text, threshold, mode)
        
        # Format output as requested
        analysis = {}
        for label, prob in prob_dict.items():
            analysis[label] = prob
            
        return analysis, pred_labels
