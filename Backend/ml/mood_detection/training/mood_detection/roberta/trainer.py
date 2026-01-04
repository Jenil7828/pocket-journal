import torch
import torch.nn as nn
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer
)
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

from .config import Config
from .dataset_loader import SentenceDatasetLoader

class SentenceTrainer:
    def __init__(self):
        self.loader = SentenceDatasetLoader()
        self.dataset, self.labels = self.loader.load_data()
        self.tokenizer = AutoTokenizer.from_pretrained(Config.MODEL_NAME)
        self.class_weights = self.loader.compute_class_weights(self.dataset["labels"])

    def tokenize(self, batch):
        return self.tokenizer(
            batch["text"],
            padding="max_length",
            truncation=True,
            max_length=Config.MAX_LENGTH
        )

    def compute_metrics(self, pred):
        probs = torch.sigmoid(torch.tensor(pred.predictions))
        preds = (probs > Config.PREDICTION_THRESHOLD).int().numpy()
        labels = pred.label_ids

        precision, recall, f1, _ = precision_recall_fscore_support(
            labels, preds, average="micro", zero_division=0
        )
        acc = accuracy_score(labels, preds)

        return {
            "accuracy": acc,
            "f1": f1,
            "precision": precision,
            "recall": recall
        }

    def train(self):
        dataset = self.dataset.map(self.tokenize, batched=True)
        dataset = dataset.train_test_split(
            test_size=Config.TEST_SPLIT, seed=Config.SEED
        )

        model = AutoModelForSequenceClassification.from_pretrained(
            Config.MODEL_NAME,
            problem_type="multi_label_classification",
            num_labels=Config.NUM_LABELS
        )

        training_args = TrainingArguments(
            output_dir=Config.OUTPUT_DIR,
            eval_strategy="epoch",
            save_strategy="epoch",
            learning_rate=Config.LEARNING_RATE,
            per_device_train_batch_size=Config.BATCH_SIZE,
            per_device_eval_batch_size=Config.BATCH_SIZE,
            gradient_accumulation_steps=Config.GRADIENT_ACCUMULATION_STEPS,
            num_train_epochs=Config.EPOCHS,
            fp16=Config.FP16,
            load_best_model_at_end=True,
            metric_for_best_model="f1",
            logging_dir=Config.LOG_DIR,
            save_total_limit=3,
        )

        class WeightedTrainer(Trainer):
            def compute_loss(self, model, inputs, return_outputs=False):
                labels = inputs.pop("labels")
                outputs = model(**inputs)
                logits = outputs.logits

                loss_fn = nn.BCEWithLogitsLoss(
                    weight=torch.tensor(self.class_weights).to(logits.device)
                    if self.class_weights else None
                )
                loss = loss_fn(logits, labels)
                return (loss, outputs) if return_outputs else loss

        trainer = WeightedTrainer(
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
