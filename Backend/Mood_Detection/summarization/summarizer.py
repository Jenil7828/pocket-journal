from transformers import BartTokenizer, BartForConditionalGeneration
from .config import OUTPUT_DIR, DEVICE
import torch

class Summarizer:
    def __init__(self):
        self.device = DEVICE
        self.tokenizer = BartTokenizer.from_pretrained(OUTPUT_DIR)
        self.model = BartForConditionalGeneration.from_pretrained(OUTPUT_DIR).to(self.device)

    def summarize(self, text, max_len=120, min_len=20):
        """
        Summarizes a single text entry.
        """
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=1024).to(self.device)
        summary_ids = self.model.generate(
            inputs["input_ids"],
            num_beams=4,
            length_penalty=2.0,
            max_length=max_len,
            min_length=min_len,
            early_stopping=True
        )
        return self.tokenizer.decode(summary_ids[0], skip_special_tokens=True)
