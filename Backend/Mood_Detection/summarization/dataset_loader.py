import os
import glob
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer
from datasets import Dataset
import json
from .config import DATA_DIR

class SummarizationDatasetLoader:
    def __init__(self, root_dir=DATA_DIR):
        self.root_dir = root_dir

    def get_pseudo_summary(self, text, sentence_count=1):
        """
        Generates a simple extractive pseudo-summary using LexRank.
        """
        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        summarizer = LexRankSummarizer()
        summary_sentences = summarizer(parser.document, sentence_count)
        return " ".join([str(sentence) for sentence in summary_sentences])

    def load_data(self):
        """
        Loads folder/subfolder text data, generates pseudo summaries,
        and returns a HuggingFace Dataset.
        """
        texts, summaries = [], []

        for folder in os.listdir(self.root_dir):
            folder_path = os.path.join(self.root_dir, folder)
            if os.path.isdir(folder_path):
                for file_path in glob.glob(os.path.join(folder_path, "*.txt")):
                    with open(file_path, "r", encoding="utf-8") as f:
                        text = f.read().strip()
                        texts.append(text)
                        summaries.append(self.get_pseudo_summary(text))

        # Save as JSONL for HuggingFace Dataset
        dataset_file = os.path.join(self.root_dir, "summarization_dataset.jsonl")
        with open(dataset_file, "w", encoding="utf-8") as f:
            for t, s in zip(texts, summaries):
                f.write(json.dumps({"text": t, "summary": s}) + "\n")

        return Dataset.from_json(dataset_file)
