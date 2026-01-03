# import numpy as np
import torch
import torch.nn as nn
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer
)
from sklearn.metrics import accuracy_score, precision_recall_fscore_support # ,f1_score
from .config import Config
from .dataset_loader import SentenceDatasetLoader

class SentenceTrainer:
    def __init__(self):
        self.loader = SentenceDatasetLoader()
        self.dataset, self.labels = self.loader.load_data()
        self.tokenizer = AutoTokenizer.from_pretrained(Config.MODEL_NAME)
        self.class_weights = self.loader.compute_class_weights(self.dataset["labels"])

    def tokenize(self, batch):
        return self.tokenizer(batch["text"], padding="max_length", truncation=True, max_length=Config.MAX_LENGTH)

    def compute_metrics(self, pred):
        probs = torch.sigmoid(torch.tensor(pred.predictions))
        preds = (probs > Config.PREDICTION_THRESHOLD).int().numpy()
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
        
        if self.class_weights:
            print(f"Using class weights: {self.class_weights}")

        # Tokenize and preprocess dataset
        dataset = self.dataset.map(self.tokenize, batched=True)
        dataset = dataset.map(self.set_labels_to_float, batched=True)
        dataset = dataset.train_test_split(test_size=Config.TEST_SPLIT, seed=Config.SEED)

        model = AutoModelForSequenceClassification.from_pretrained(
            Config.MODEL_NAME,
            problem_type="multi_label_classification",
            num_labels=Config.NUM_LABELS
        ).to(device)

        # Enhanced training arguments for better convergence
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
            fp16=Config.FP16,
            warmup_steps=100,  # Add warmup for better convergence
            logging_steps=50,   # More frequent logging
            save_total_limit=3, # Keep only the best 3 models
            dataloader_drop_last=True,  # For consistent batch sizes
        )

        # Custom trainer with class weighting
        class WeightedTrainer(Trainer):
            def __init__(self, class_weights, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.class_weights = class_weights

            def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
                labels = inputs.get("labels")
                outputs = model(**inputs)
                logits = outputs.get("logits")
                
                if self.class_weights is not None:
                    # Apply class weights to BCE loss
                    loss_fct = nn.BCEWithLogitsLoss(
                        weight=torch.tensor(self.class_weights, dtype=torch.float32).to(logits.device)
                    )
                else:
                    loss_fct = nn.BCEWithLogitsLoss()
                
                loss = loss_fct(logits, labels)
                return (loss, outputs) if return_outputs else loss

        trainer = WeightedTrainer(
            class_weights=self.class_weights,
            model=model,
            args=training_args,
            train_dataset=dataset["train"],
            eval_dataset=dataset["test"],
            tokenizer=self.tokenizer,
            compute_metrics=self.compute_metrics,
        )

        print("🚀 Starting enhanced training for overlapping emotions...")
        print(f"📊 Training for {epochs} epochs with batch size {batch_size}")
        print(f"🎯 Using threshold {Config.PREDICTION_THRESHOLD} for multi-label classification")
        
        trainer.train()
        trainer.save_model(Config.OUTPUT_DIR)
        self.tokenizer.save_pretrained(Config.OUTPUT_DIR)

        print("✅ Enhanced Sentence-level Multilabel Training Complete!")
        print(f"💾 Model saved at: {Config.OUTPUT_DIR}")
        print("🎭 Optimized for overlapping/mixed emotions detection")
