import logging
import time
import numpy as np
from typing import List, Dict, Any
from ml.inference.summarization.bart.predictor import SummarizationPredictor
from services.embeddings.embedding_service import EmbeddingService

logger = logging.getLogger()

class BartEvaluator:
    def __init__(self, predictor: SummarizationPredictor, embedding_service: EmbeddingService):
        self.predictor = predictor
        self.embedding_service = embedding_service
        try:
            from rouge_score import rouge_scorer
            self.scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
        except ImportError:
            logger.error("rouge-score library not found. ROUGE metrics will be skipped.")
            self.scorer = None

    def evaluate(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run full BART evaluation on provided data."""
        if not data:
            return {}

        results = []
        compression_ratios = []
        summary_lengths = []
        semantic_similarities = []
        rouge_scores = {'rouge1': [], 'rouge2': [], 'rougeL': []}
        
        inference_times = []

        for d in data:
            text = d["text"]
            ref_summary = d.get("reference_summary", "")
            
            start = time.time()
            try:
                summary = self.predictor.summarize(text)
            except Exception as e:
                logger.error("Summarization failed. Error: %s", str(e))
                continue
            inference_times.append(time.time() - start)

            # 1. Length and Compression
            text_tokens = text.split()
            summary_tokens = summary.split()
            
            ratio = len(summary_tokens) / len(text_tokens) if len(text_tokens) > 0 else 0
            compression_ratios.append(ratio)
            summary_lengths.append(len(summary_tokens))

            # 2. Semantic Similarity
            try:
                emb_text = self.embedding_service.embed_text(text)
                emb_sum = self.embedding_service.embed_text(summary)
                similarity = self.embedding_service.cosine_similarity(emb_text, emb_sum)
                if similarity is not None:
                    semantic_similarities.append(similarity)
            except Exception as e:
                logger.warning("Failed to compute semantic similarity: %s", str(e))

            # 3. ROUGE Scores (if reference exists)
            if self.scorer and ref_summary:
                scores = self.scorer.score(ref_summary, summary)
                rouge_scores['rouge1'].append(scores['rouge1'].fmeasure)
                rouge_scores['rouge2'].append(scores['rouge2'].fmeasure)
                rouge_scores['rougeL'].append(scores['rougeL'].fmeasure)

        # Compute averages
        avg_rouge1 = float(np.mean(rouge_scores['rouge1'])) if rouge_scores['rouge1'] else 0.0
        avg_rouge2 = float(np.mean(rouge_scores['rouge2'])) if rouge_scores['rouge2'] else 0.0
        avg_rougeL = float(np.mean(rouge_scores['rougeL'])) if rouge_scores['rougeL'] else 0.0
        
        return {
            "rouge1": avg_rouge1,
            "rouge2": avg_rouge2,
            "rougeL": avg_rougeL,
            "avg_compression_ratio": float(np.mean(compression_ratios)) if compression_ratios else 0.0,
            "avg_summary_length_tokens": int(np.mean(summary_lengths)) if summary_lengths else 0,
            "avg_semantic_similarity": float(np.mean(semantic_similarities)) if semantic_similarities else 0.0,
            "compression_ratios": compression_ratios, # For histogram
            "latency_stats": {
                "p50": float(np.percentile(inference_times, 50) * 1000) if inference_times else 0,
                "p90": float(np.percentile(inference_times, 90) * 1000) if inference_times else 0,
                "p99": float(np.percentile(inference_times, 99) * 1000) if inference_times else 0,
            }
        }
