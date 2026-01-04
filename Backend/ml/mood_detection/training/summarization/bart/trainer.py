import numpy as np
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
    DataCollatorForSeq2Seq
)

from .config import Config
from .dataset_loader import SummarizationDatasetLoader


class SummarizationTrainer:
    def __init__(self):
        self.loader = SummarizationDatasetLoader()
        self.dataset = self.loader.create_dataset()
        self.tokenizer = AutoTokenizer.from_pretrained(Config.MODEL_NAME)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(Config.MODEL_NAME)

        if len(self.tokenizer) != self.model.config.vocab_size:
            self.model.resize_token_embeddings(len(self.tokenizer))

    def compute_metrics(self, eval_pred):
        predictions, labels = eval_pred
        decoded_preds = self.tokenizer.batch_decode(predictions, skip_special_tokens=True)

        labels = np.where(labels != -100, labels, self.tokenizer.pad_token_id)
        decoded_labels = self.tokenizer.batch_decode(labels, skip_special_tokens=True)

        return {
            "avg_pred_length": np.mean([len(p.split()) for p in decoded_preds]),
            "avg_label_length": np.mean([len(l.split()) for l in decoded_labels]),
        }

    def train(self):
        args = Seq2SeqTrainingArguments(
            output_dir=Config.OUTPUT_DIR,
            evaluation_strategy="steps",
            save_strategy="steps",
            eval_steps=Config.EVAL_STEPS,
            save_steps=Config.SAVE_STEPS,
            logging_steps=Config.LOGGING_STEPS,
            num_train_epochs=Config.EPOCHS,
            per_device_train_batch_size=Config.BATCH_SIZE,
            per_device_eval_batch_size=Config.BATCH_SIZE,
            gradient_accumulation_steps=Config.GRADIENT_ACCUMULATION_STEPS,
            learning_rate=Config.LEARNING_RATE,
            warmup_steps=Config.WARMUP_STEPS,
            weight_decay=Config.WEIGHT_DECAY,
            fp16=Config.FP16,
            load_best_model_at_end=True,
            save_total_limit=3,
            predict_with_generate=True,
            report_to=None,
            remove_unused_columns=False,
            seed=Config.SEED,
        )

        trainer = Seq2SeqTrainer(
            model=self.model,
            args=args,
            train_dataset=self.dataset["train"],
            eval_dataset=self.dataset["validation"],
            tokenizer=self.tokenizer,
            data_collator=DataCollatorForSeq2Seq(self.tokenizer, self.model),
            compute_metrics=self.compute_metrics,
        )

        trainer.train()
        trainer.save_model(Config.OUTPUT_DIR)
        self.tokenizer.save_pretrained(Config.OUTPUT_DIR)

        return trainer
