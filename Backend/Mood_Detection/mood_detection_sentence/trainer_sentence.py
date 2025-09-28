import numpy as np
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer
)
from sklearn.metrics import f1_score, accuracy_score, precision_recall_fscore_support
from .config_sentence import Config
from .dataset_loader import SentenceDatasetLoader

class SentenceTrainer:
    def __init__(self):
        self.loader = SentenceDatasetLoader()
        self.dataset, self.labels = self.loader.load_data()
        self.tokenizer = AutoTokenizer.from_pretrained(Config.MODEL_NAME)

    def tokenize(self, batch):
        return self.tokenizer(batch["text"], padding="max_length", truncation=True, max_length=Config.MAX_LENGTH)

    def compute_metrics(self, pred):
        probs = torch.sigmoid(torch.tensor(pred.predictions))
        preds = (probs > 0.1).int().numpy()
        labels = pred.label_ids

        precision, recall, f1, _ = precision_recall_fscore_support(labels, preds, average="micro", zero_division=0)
        acc = accuracy_score(labels, preds)
        return {"accuracy": acc, "f1": f1, "precision": precision, "recall": recall}

    def set_labels_to_float(self, batch):
        batch["labels"] = [list(map(float, lbl)) for lbl in batch["labels"]]
        return batch

    def train(self, epochs=Config.EPOCHS, batch_size=Config.BATCH_SIZE, lr=Config.LEARNING_RATE):
        # Detect GPU
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Training on {device.upper()}")

        # Tokenize and preprocess dataset
        dataset = self.dataset.map(self.tokenize, batched=True)
        dataset = dataset.map(self.set_labels_to_float, batched=True)
        dataset = dataset.train_test_split(test_size=Config.TEST_SPLIT, seed=Config.SEED)

        model = AutoModelForSequenceClassification.from_pretrained(
            Config.MODEL_NAME,
            problem_type="multi_label_classification",
            num_labels=Config.NUM_LABELS
        ).to(device)

        training_args = TrainingArguments(
            output_dir=Config.OUTPUT_DIR,
            eval_strategy="epoch",
            save_strategy="epoch",
            learning_rate=lr,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            gradient_accumulation_steps=Config.GRADIENT_ACCUMULATION_STEPS,
            num_train_epochs=epochs,
            weight_decay=0.01,
            load_best_model_at_end=True,
            metric_for_best_model="f1",
            logging_dir=Config.LOG_DIR,
            fp16=Config.FP16
        )

        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=dataset["train"],
            eval_dataset=dataset["test"],
            tokenizer=self.tokenizer,
            compute_metrics=self.compute_metrics,
        )

        trainer.train()
        trainer.save_model(Config.OUTPUT_DIR)
        self.tokenizer.save_pretrained(Config.OUTPUT_DIR)

        print("✅ Sentence-level Multilabel Training Complete! Saved at:", Config.OUTPUT_DIR)
