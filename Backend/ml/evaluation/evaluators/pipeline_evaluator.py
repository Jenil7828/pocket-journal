import logging
import time
import numpy as np
from typing import List, Dict, Any
from ml.inference.mood_detection.roberta.predictor import SentencePredictor
from ml.inference.summarization.bart.predictor import SummarizationPredictor
from utils import extract_dominant_mood

logger = logging.getLogger()

class PipelineEvaluator:
    def __init__(self, roberta: SentencePredictor, bart: SummarizationPredictor):
        self.roberta = roberta
        self.bart = bart
        self.labels = roberta.labels

    def evaluate(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run full pipeline evaluation (BART -> RoBERTa)."""
        if not data:
            return {}

        agreements = []
        drifts = []
        latencies = {
            "bart": [],
            "roberta": [],
            "full": []
        }

        for d in data:
            text = d["text"]
            
            # 1. RoBERTa on original text
            start_orig = time.time()
            try:
                res_orig = self.roberta.predict(text)
                end_orig = time.time()
                latencies["roberta"].append(end_orig - start_orig)
                probs_orig = res_orig["probabilities"]
                dom_orig = extract_dominant_mood(probs_orig)
            except Exception as e:
                logger.error("RoBERTa failed on original text: %s", str(e))
                continue

            # 2. BART Summarization
            start_bart = time.time()
            try:
                summary = self.bart.summarize(text)
                end_bart = time.time()
                latencies["bart"].append(end_bart - start_bart)
            except Exception as e:
                logger.error("BART failed: %s", str(e))
                continue

            # 3. RoBERTa on summary
            start_sum = time.time()
            try:
                res_sum = self.roberta.predict(summary)
                end_sum = time.time()
                latencies["full"].append((end_bart - start_bart) + (end_sum - start_sum))
                probs_sum = res_sum["probabilities"]
                dom_sum = extract_dominant_mood(probs_sum)
            except Exception as e:
                logger.error("RoBERTa failed on summary: %s", str(e))
                continue

            # Metrics
            # Agreement: does dominant emotion change?
            agreements.append(1 if dom_orig == dom_sum else 0)

            # Probability Drift: Mean Absolute Difference
            p_orig = np.array([probs_orig[l] for l in self.labels])
            p_sum = np.array([probs_sum[l] for l in self.labels])
            drift = np.mean(np.abs(p_orig - p_sum))
            drifts.append(drift)

        return {
            "emotion_agreement_rate": float(np.mean(agreements)) if agreements else 0.0,
            "avg_probability_drift": float(np.mean(drifts)) if drifts else 0.0,
            "latency_ms": {
                "bart_p50": float(np.percentile(latencies["bart"], 50) * 1000) if latencies["bart"] else 0,
                "bart_p90": float(np.percentile(latencies["bart"], 90) * 1000) if latencies["bart"] else 0,
                "bart_p99": float(np.percentile(latencies["bart"], 99) * 1000) if latencies["bart"] else 0,
                "roberta_p50": float(np.percentile(latencies["roberta"], 50) * 1000) if latencies["roberta"] else 0,
                "roberta_p90": float(np.percentile(latencies["roberta"], 90) * 1000) if latencies["roberta"] else 0,
                "roberta_p99": float(np.percentile(latencies["roberta"], 99) * 1000) if latencies["roberta"] else 0,
                "pipeline_p50": float(np.percentile(latencies["full"], 50) * 1000) if latencies["full"] else 0,
                "pipeline_p90": float(np.percentile(latencies["full"], 90) * 1000) if latencies["full"] else 0,
                "pipeline_p99": float(np.percentile(latencies["full"], 99) * 1000) if latencies["full"] else 0,
            }
        }
