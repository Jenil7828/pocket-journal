from transformers import BartTokenizer, BartForConditionalGeneration, Trainer, TrainingArguments
from datasets import load_dataset
from .dataset_loader import SummarizationDatasetLoader
from .config import OUTPUT_DIR, NUM_EPOCHS, BATCH_SIZE, LEARNING_RATE, DEVICE
import os

class SummarizationTrainer:
    def __init__(self, model_name="facebook/bart-large-cnn"):
        self.model_name = model_name
        self.device = DEVICE

    def train(self):
        # 1️⃣ Load dataset
        loader = SummarizationDatasetLoader()
        loader.load_data()
        dataset_file = "data/summarization_dataset.jsonl"
        dataset = load_dataset("json", data_files=dataset_file, split="train")

        # 2️⃣ Load tokenizer
        tokenizer = BartTokenizer.from_pretrained(self.model_name)

        # 3️⃣ Tokenization
        def tokenize(batch):
            inputs = tokenizer(batch["text"], truncation=True, padding="max_length", max_length=1024)
            targets = tokenizer(batch["summary"], truncation=True, padding="max_length", max_length=128)
            batch["input_ids"] = inputs["input_ids"]
            batch["attention_mask"] = inputs["attention_mask"]
            batch["labels"] = targets["input_ids"]
            return batch

        dataset = dataset.map(tokenize, batched=True)
        dataset.set_format(type="torch", columns=["input_ids", "attention_mask", "labels"])

        # 4️⃣ Load model
        model = BartForConditionalGeneration.from_pretrained(self.model_name).to(self.device)

        # 5️⃣ Training arguments
        training_args = TrainingArguments(
            output_dir=OUTPUT_DIR,
            num_train_epochs=NUM_EPOCHS,
            per_device_train_batch_size=BATCH_SIZE,
            per_device_eval_batch_size=BATCH_SIZE,
            learning_rate=LEARNING_RATE,
            save_strategy="epoch",
            eval_strategy="epoch",
            logging_dir=os.path.join(OUTPUT_DIR, "logs"),
            save_total_limit=2,
        )

        # 6️⃣ Trainer
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=dataset,
            eval_dataset=dataset,  # you can later split 10% for validation
        )

        # 7️⃣ Train & save
        trainer.train()
        trainer.save_model(OUTPUT_DIR)
        tokenizer.save_pretrained(OUTPUT_DIR)
