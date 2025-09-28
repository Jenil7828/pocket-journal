import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from .config_sentence import Config

class SentencePredictor:
    def __init__(self, model_path=Config.OUTPUT_DIR):
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
        self.labels = Config.LABELS

    def predict(self, text):
        tokens = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=Config.MAX_LENGTH)
        with torch.no_grad():
            outputs = self.model(**tokens)
            probs = torch.sigmoid(outputs.logits).cpu().numpy()[0]

        results = {label: float(prob) for label, prob in zip(self.labels, probs)}
        return results
