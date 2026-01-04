import os
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

try:
    from evaluate import load
    ROUGE_AVAILABLE = True
except Exception:
    ROUGE_AVAILABLE = False

from .config import Config


class SummarizationEvaluator:
    def __init__(self, model_dir=None):
        self.model_dir = model_dir or Config.OUTPUT_DIR
        self.device = Config.DEVICE

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_dir)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_dir)
        self.model.to(self.device)
        self.model.eval()

        self.rouge = load("rouge") if ROUGE_AVAILABLE else None

    def generate_summary(self, text):
        inputs = self.tokenizer(
            text,
            truncation=True,
            padding="max_length",
            max_length=Config.MAX_INPUT_LENGTH,
            return_tensors="pt"
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_length=Config.MAX_SUMMARY_LENGTH,
                min_length=Config.MIN_SUMMARY_LENGTH,
                num_beams=4,
                no_repeat_ngram_size=3,
            )

        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)

    def evaluate_dataset(self, dataset, max_samples=None):
        if max_samples:
            dataset = dataset.select(range(min(len(dataset), max_samples)))

        predictions, references = [], []

        for i, sample in enumerate(dataset):
            if i % 10 == 0:
                print(f"   Evaluating sample {i}/{len(dataset)}")

            predictions.append(self.generate_summary(sample["text"]))
            references.append(sample["summary"])

        metrics = {}

        if self.rouge:
            rouge_scores = self.rouge.compute(
                predictions=predictions,
                references=references
            )
            for k, v in rouge_scores.items():
                metrics[k] = v * 100

        pred_lens = [len(p.split()) for p in predictions]
        ref_lens = [len(r.split()) for r in references]

        metrics["avg_pred_length"] = np.mean(pred_lens)
        metrics["avg_ref_length"] = np.mean(ref_lens)
        metrics["length_ratio"] = metrics["avg_pred_length"] / metrics["avg_ref_length"]

        return metrics, predictions, references
