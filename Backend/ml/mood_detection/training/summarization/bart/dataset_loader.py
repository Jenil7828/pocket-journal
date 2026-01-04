import pandas as pd
from datasets import Dataset
from transformers import AutoTokenizer
from .config import Config

class SummarizationDatasetLoader:
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained(Config.MODEL_NAME)

    def load_csv_data(self):
        df = pd.read_csv(Config.DATASET_PATH)
        text_col, summary_col = Config.TEXT_COLUMN, Config.SUMMARY_COLUMN

        df = df.dropna(subset=[text_col, summary_col])
        df = df[df[text_col].str.len() > 50]
        df = df[df[summary_col].str.len() > 10]

        return df[text_col].tolist(), df[summary_col].tolist()

    def tokenize(self, batch):
        inputs = self.tokenizer(
            batch["text"],
            max_length=Config.MAX_INPUT_LENGTH,
            truncation=True,
            padding="max_length",
        )
        labels = self.tokenizer(
            text_target=batch["summary"],
            max_length=Config.MAX_SUMMARY_LENGTH,
            truncation=True,
            padding="max_length",
        )
        labels["input_ids"] = [
            [(t if t != self.tokenizer.pad_token_id else -100) for t in seq]
            for seq in labels["input_ids"]
        ]
        inputs["labels"] = labels["input_ids"]
        return inputs

    def create_dataset(self):
        texts, summaries = self.load_csv_data()
        dataset = Dataset.from_dict({"text": texts, "summary": summaries})
        dataset = dataset.map(self.tokenize, batched=True, remove_columns=dataset.column_names)

        train_test = dataset.train_test_split(test_size=Config.TEST_SPLIT, seed=Config.SEED)
        train_val = train_test["train"].train_test_split(
            test_size=Config.VALIDATION_SPLIT, seed=Config.SEED
        )

        return {
            "train": train_val["train"],
            "validation": train_val["test"],
            "test": train_test["test"],
        }
