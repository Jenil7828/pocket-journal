import logging
import time
import numpy as np
from typing import List, Dict, Any, Tuple
from ml.inference.mood_detection.roberta.predictor import SentencePredictor
from utils import extract_dominant_mood

logger = logging.getLogger()

class RobertaEvaluator:
    def __init__(self, predictor: SentencePredictor):
        self.predictor = predictor
        self.labels = predictor.labels
        self.num_labels = len(self.labels)

    def evaluate(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run full RoBERTa evaluation on provided data."""
        if not data:
            return {}

        texts = [d["text"] for d in data]
        y_true = np.array([[d["labels"].get(l, 0) for l in self.labels] for d in data])
        
        all_probs = []
        inference_times = []

        for text in texts:
            start = time.time()
            try:
                result = self.predictor.predict(text)
                probs = [result["probabilities"][l] for l in self.labels]
                all_probs.append(probs)
            except Exception as e:
                logger.error("Inference failed for text: %s. Error: %s", text[:50], str(e))
                # Append zeros if failed to keep shapes consistent, but we should ideally skip
                all_probs.append([0.0] * self.num_labels)
            inference_times.append(time.time() - start)

        y_prob = np.array(all_probs)
        
        # 1. Per-emotion metrics (using default threshold)
        threshold = self.predictor.threshold
        y_pred = (y_prob >= threshold).astype(int)
        
        per_emotion = {}
        for i, label in enumerate(self.labels):
            per_emotion[label] = self._compute_binary_metrics(y_true[:, i], y_pred[:, i], y_prob[:, i])

        # 2. Macro and Weighted averages
        macro_avg = self._compute_averages(per_emotion, "macro")
        weighted_avg = self._compute_averages(per_emotion, "weighted", y_true)

        # 3. Confusion Matrix (using dominant emotion)
        cm = self._compute_confusion_matrix(y_true, y_prob)

        # 4. Threshold sensitivity sweep
        thresholds = [0.25, 0.30, 0.35, 0.40, 0.45]
        threshold_sweep = {}
        for t in thresholds:
            y_pred_t = (y_prob >= t).astype(int)
            f1s = []
            for i in range(self.num_labels):
                p, r, f1 = self._precision_recall_f1(y_true[:, i], y_pred_t[:, i])
                f1s.append(f1)
            threshold_sweep[f"{t:.2f}"] = float(np.mean(f1s))

        # 5. Calibration check
        calibration = self._compute_calibration(y_true, y_prob)

        return {
            "per_emotion": per_emotion,
            "macro_avg": macro_avg,
            "weighted_avg": weighted_avg,
            "threshold_sweep": threshold_sweep,
            "confusion_matrix": cm.tolist(),
            "calibration": calibration,
            "latency_stats": {
                "p50": float(np.percentile(inference_times, 50) * 1000),
                "p90": float(np.percentile(inference_times, 90) * 1000),
                "p99": float(np.percentile(inference_times, 99) * 1000),
            }
        }

    def _compute_binary_metrics(self, y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray) -> Dict[str, float]:
        p, r, f1 = self._precision_recall_f1(y_true, y_pred)
        auc = self._compute_auc_roc(y_true, y_prob)
        return {
            "precision": float(p),
            "recall": float(r),
            "f1": float(f1),
            "auc_roc": float(auc)
        }

    def _precision_recall_f1(self, y_true: np.ndarray, y_pred: np.ndarray) -> Tuple[float, float, float]:
        tp = np.sum((y_true == 1) & (y_pred == 1))
        fp = np.sum((y_true == 0) & (y_pred == 1))
        fn = np.sum((y_true == 1) & (y_pred == 0))
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        
        return precision, recall, f1

    def _compute_auc_roc(self, y_true: np.ndarray, y_prob: np.ndarray) -> float:
        """Compute AUC-ROC using the trapezoidal rule."""
        if len(np.unique(y_true)) < 2:
            return 0.5 # Undefined for single class
            
        # Sort by probabilities
        desc_score_indices = np.argsort(y_prob)[::-1]
        y_prob = y_prob[desc_score_indices]
        y_true = y_true[desc_score_indices]
        
        distinct_value_indices = np.where(np.diff(y_prob))[0]
        threshold_indices = np.r_[distinct_value_indices, y_true.size - 1]
        
        tps = np.cumsum(y_true)[threshold_indices]
        fps = 1 + threshold_indices - tps
        
        # Add point (0,0)
        tps = np.r_[0, tps]
        fps = np.r_[0, fps]
        
        if fps[-1] <= 0 or tps[-1] <= 0:
            return 0.0
            
        tpr = tps / tps[-1]
        fpr = fps / fps[-1]
        
        # Area under curve using trapezoidal rule
        # Use np.trapezoid (NumPy 2.0+) or fallback to np.trapz
        if hasattr(np, "trapezoid"):
            return float(np.trapezoid(tpr, fpr))
        return float(np.trapz(tpr, fpr))

    def _compute_averages(self, per_emotion: Dict[str, Dict[str, float]], type: str, y_true: np.ndarray = None) -> Dict[str, float]:
        metrics = ["precision", "recall", "f1", "auc_roc"]
        results = {}
        
        if type == "macro":
            for m in metrics:
                results[m] = float(np.mean([per_emotion[l][m] for l in self.labels]))
        elif type == "weighted" and y_true is not None:
            weights = np.sum(y_true, axis=0)
            total_weight = np.sum(weights)
            if total_weight == 0:
                return {m: 0.0 for m in metrics}
            for m in metrics:
                results[m] = float(np.average([per_emotion[l][m] for l in self.labels], weights=weights))
        
        return results

    def _compute_confusion_matrix(self, y_true: np.ndarray, y_prob: np.ndarray) -> np.ndarray:
        """Compute 7x7 confusion matrix based on dominant emotion."""
        cm = np.zeros((self.num_labels, self.num_labels), dtype=int)
        
        # Actual dominant emotion (from ground truth)
        actual_idx = np.argmax(y_true, axis=1)
        
        # Predicted dominant emotion
        # Note: we use extract_dominant_mood logic via argmax here
        predicted_idx = np.argmax(y_prob, axis=1)
        
        for a, p in zip(actual_idx, predicted_idx):
            cm[a, p] += 1
            
        return cm

    def _compute_calibration(self, y_true: np.ndarray, y_prob: np.ndarray) -> List[Dict[str, float]]:
        """Compute mean predicted prob vs actual positive rate per emotion."""
        calibration = []
        for i, label in enumerate(self.labels):
            mean_prob = float(np.mean(y_prob[:, i]))
            actual_rate = float(np.mean(y_true[:, i]))
            calibration.append({
                "emotion": label,
                "mean_predicted_prob": mean_prob,
                "actual_positive_rate": actual_rate,
                "difference": mean_prob - actual_rate
            })
        return calibration
