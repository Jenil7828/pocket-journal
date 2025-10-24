import os
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from config import Config

class SentencePredictor:
    def __init__(self, model_path=Config.OUTPUT_DIR):
        # Check if model exists, otherwise use base model
        if os.path.exists(model_path) and os.path.exists(os.path.join(model_path, "config.json")):
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
        else:
            print(f"⚠️ Model not found at {model_path}, using base RoBERTa model")
            self.tokenizer = AutoTokenizer.from_pretrained(Config.MODEL_NAME)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                Config.MODEL_NAME, 
                num_labels=Config.NUM_LABELS,
                problem_type="multi_label_classification"
            )
        
        self.labels = Config.LABELS
        self.threshold = Config.PREDICTION_THRESHOLD
        
        # Safe device detection - always use CPU to avoid GPU issues
        self.device = "cpu"
        self.model.to(self.device)
        print(f"Using device: {self.device}")

    def predict(self, text, threshold=None):
        """
        Predict emotions for a single text with configurable threshold
        Returns numpy arrays instead of tensors for better compatibility
        """
        if threshold is None:
            threshold = self.threshold
            
        try:
            # Tokenize text
            tokens = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=Config.MAX_LENGTH)
            
            # Ensure tokens are on CPU (no device mismatch issues)
            tokens = {k: v.cpu() for k, v in tokens.items()}
            
            with torch.no_grad():
                outputs = self.model(**tokens)
                # Convert to numpy array immediately
                logits = outputs.logits.cpu().numpy()[0]
                probs = 1 / (1 + np.exp(-logits))  # Sigmoid using numpy
            
            # Apply threshold for multi-label classification
            binary_preds = (probs >= threshold).astype(int)
            
            results = {
                "probabilities": {label: float(prob) for label, prob in zip(self.labels, probs)},
                "predictions": {label: bool(pred) for label, pred in zip(self.labels, binary_preds)},
                "threshold": threshold
            }
            return results
            
        except Exception as e:
            print(f"Error in prediction: {e}")
            # Return neutral predictions on error
            neutral_probs = np.array([0.5] * len(self.labels))
            binary_preds = (neutral_probs >= threshold).astype(int)
            
            return {
                "probabilities": {label: float(prob) for label, prob in zip(self.labels, neutral_probs)},
                "predictions": {label: bool(pred) for label, pred in zip(self.labels, binary_preds)},
                "threshold": threshold
            }

    def predict_batch(self, texts, threshold=None):
        """
        Predict emotions for multiple texts using numpy arrays
        """
        if threshold is None:
            threshold = self.threshold
            
        results = []
        for text in texts:
            try:
                result = self.predict(text, threshold)
                results.append(result)
            except Exception as e:
                print(f"Error processing text '{text[:50]}...': {e}")
                # Add neutral result for failed predictions
                neutral_probs = np.array([0.5] * len(self.labels))
                binary_preds = (neutral_probs >= threshold).astype(int)
                results.append({
                    "probabilities": {label: float(prob) for label, prob in zip(self.labels, neutral_probs)},
                    "predictions": {label: bool(pred) for label, pred in zip(self.labels, binary_preds)},
                    "threshold": threshold
                })
        return results

    def get_emotion_probabilities(self, text, threshold=None):
        """
        Get emotion probabilities in the specified format:
        anger: 0.04053952172398567
        disgust: 0.01377052627503872
        etc.
        """
        result = self.predict(text, threshold)
        return result["probabilities"]
