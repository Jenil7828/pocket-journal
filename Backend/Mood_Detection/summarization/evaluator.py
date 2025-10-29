import os
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
try:
    from evaluate import load
except ImportError:
    load = None
from .config import Config

class SummarizationEvaluator:
    def __init__(self, model_dir=None):
        self.model_dir = model_dir or Config.OUTPUT_DIR
        self.device = Config.DEVICE
        
        # Load model and tokenizer
        if os.path.exists(self.model_dir) and os.path.exists(os.path.join(self.model_dir, "config.json")):
            print(f"📁 Loading trained model from {self.model_dir}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_dir)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_dir)
        else:
            print(f"⚠️ Trained model not found at {self.model_dir}, using base model")
            self.tokenizer = AutoTokenizer.from_pretrained(Config.MODEL_NAME)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(Config.MODEL_NAME)
        
        self.model.to(self.device)
        self.model.eval()
        print(f"🔧 Evaluator using device: {self.device}")
        
        # Load ROUGE metric
        if load is not None:
            try:
                self.rouge = load("rouge")
                print("✅ ROUGE metric loaded successfully")
            except Exception as e:
                print(f"⚠️ Could not load ROUGE metric: {e}")
                self.rouge = None
        else:
            print("⚠️ Evaluate library not installed, ROUGE metrics unavailable")
            self.rouge = None
    
    def generate_summary(self, text, max_length=None, min_length=None, num_beams=4):
        """Generate summary for a single text"""
        if max_length is None:
            max_length = Config.MAX_SUMMARY_LENGTH
        if min_length is None:
            min_length = Config.MIN_SUMMARY_LENGTH
        
        # Tokenize input
        inputs = self.tokenizer(
            text,
            max_length=Config.MAX_INPUT_LENGTH,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        ).to(self.device)
        
        # Generate summary
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_length=max_length or 80,        # allow longer summaries
                min_length=min_length or 25,        # ensure minimum length
                num_beams=6,                        # better beam search
                early_stopping=False,               # prevents premature cutoff
                do_sample=False,
                length_penalty=2.0,                 # encourages fuller outputs
                repetition_penalty=1.1,             # avoids word repetition
                no_repeat_ngram_size=3,             # prevents looping phrases
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )
        
        # Decode summary
        summary = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return summary
    
    def evaluate_rouge(self, predictions, references):
        """Evaluate ROUGE scores"""
        if self.rouge is None:
            print("⚠️ ROUGE metric not available")
            return {}
        
        try:
            # Compute ROUGE scores
            results = self.rouge.compute(
                predictions=predictions,
                references=references,
                rouge_types=["rouge1", "rouge2", "rougeL", "rougeLsum"]
            )
            
            # Format results
            rouge_scores = {}
            for metric, scores in results.items():
                if hasattr(scores, 'precision'):
                    rouge_scores[f"{metric}_precision"] = scores.precision * 100
                    rouge_scores[f"{metric}_recall"] = scores.recall * 100
                    rouge_scores[f"{metric}_fmeasure"] = scores.fmeasure * 100
                else:
                    # Handle different result formats
                    rouge_scores[metric] = scores * 100 if isinstance(scores, (int, float)) else scores
            
            return rouge_scores
            
        except Exception as e:
            print(f"❌ Error computing ROUGE scores: {e}")
            return {}
    
    def evaluate_dataset(self, dataset, max_samples=None):
        """Evaluate model on a dataset"""
        print(f"🔍 Evaluating model on dataset with {len(dataset)} samples")
        
        if max_samples:
            dataset = dataset.select(range(min(max_samples, len(dataset))))
            print(f"📊 Limited evaluation to {len(dataset)} samples")
        
        predictions = []
        references = []
        
        print("🔄 Generating predictions...")
        for i, sample in enumerate(dataset):
            if i % 50 == 0:
                print(f"   Progress: {i}/{len(dataset)}")
            
            # Generate prediction
            pred = self.generate_summary(sample["text"])
            predictions.append(pred)
            
            # Get reference
            ref = sample["summary"]
            references.append(ref)
        
        print("📊 Computing ROUGE scores...")
        rouge_scores = self.evaluate_rouge(predictions, references)
        
        # Calculate additional metrics
        metrics = {}
        
        # Length statistics
        pred_lengths = [len(pred.split()) for pred in predictions]
        ref_lengths = [len(ref.split()) for ref in references]
        
        metrics["avg_pred_length"] = np.mean(pred_lengths)
        metrics["avg_ref_length"] = np.mean(ref_lengths)
        metrics["length_ratio"] = metrics["avg_pred_length"] / metrics["avg_ref_length"]
        
        # Combine all metrics
        all_metrics = {**rouge_scores, **metrics}
        
        return all_metrics, predictions, references
    
    def print_evaluation_results(self, metrics):
        """Print evaluation results in a formatted way"""
        print("\n📊 Evaluation Results:")
        print("=" * 50)
        
        # ROUGE scores
        rouge_metrics = {k: v for k, v in metrics.items() if k.startswith("rouge")}
        if rouge_metrics:
            print("\n🎯 ROUGE Scores:")
            for metric, value in rouge_metrics.items():
                if isinstance(value, float):
                    print(f"   {metric}: {value:.4f}")
        
        # Length metrics
        length_metrics = {k: v for k, v in metrics.items() if "length" in k}
        if length_metrics:
            print("\n📏 Length Statistics:")
            for metric, value in length_metrics.items():
                if isinstance(value, float):
                    print(f"   {metric}: {value:.2f}")
        
        print("=" * 50)
    
    def compare_with_baseline(self, dataset, max_samples=100):
        """Compare model with extractive baseline"""
        print("🔄 Comparing with extractive baseline...")
        
        # Limit dataset for comparison
        if len(dataset) > max_samples:
            dataset = dataset.select(range(max_samples))
        
        # Generate predictions
        model_predictions = []
        baseline_predictories = []
        references = []
        
        for sample in dataset:
            # Model prediction
            model_pred = self.generate_summary(sample["text"])
            model_predictions.append(model_pred)
            
            # Simple extractive baseline (first sentence)
            text_sentences = sample["text"].split(". ")
            baseline_pred = text_sentences[0] + "." if text_sentences else sample["text"][:100]
            baseline_predictories.append(baseline_pred)
            
            # Reference
            references.append(sample["summary"])
        
        # Evaluate both
        model_rouge = self.evaluate_rouge(model_predictions, references)
        baseline_rouge = self.evaluate_rouge(baseline_predictories, references)
        
        print("\n📊 Model vs Baseline Comparison:")
        print("=" * 50)
        
        for metric in ["rouge1_fmeasure", "rouge2_fmeasure", "rougeL_fmeasure"]:
            if metric in model_rouge and metric in baseline_rouge:
                model_score = model_rouge[metric]
                baseline_score = baseline_rouge[metric]
                improvement = ((model_score - baseline_score) / baseline_score) * 100
                
                print(f"{metric}:")
                print(f"   Model: {model_score:.4f}")
                print(f"   Baseline: {baseline_score:.4f}")
                print(f"   Improvement: {improvement:+.2f}%")
                print()
        
        return model_rouge, baseline_rouge
