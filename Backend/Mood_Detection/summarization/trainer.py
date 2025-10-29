import os
import torch
import numpy as np
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer,
    DataCollatorForSeq2Seq
)
from .config import Config
from .dataset_loader import SummarizationDatasetLoader

class SummarizationTrainer:
    def __init__(self):
        self.loader = SummarizationDatasetLoader()
        self.dataset = self.loader.create_dataset()
        self.tokenizer = AutoTokenizer.from_pretrained(Config.MODEL_NAME)
        self.model = None
        
    def setup_model(self):
        """Initialize BART model for summarization"""
        print(f"🤖 Loading {Config.MODEL_NAME}...")
        self.model = AutoModelForSeq2SeqLM.from_pretrained(Config.MODEL_NAME)
        
        # Resize token embeddings if needed
        if len(self.tokenizer) != self.model.config.vocab_size:
            self.model.resize_token_embeddings(len(self.tokenizer))
        
        print(f"✅ Model loaded successfully")
        print(f"📊 Model parameters: {self.model.num_parameters():,}")
        
    def setup_data_collator(self):
        """Setup data collator for Seq2Seq training"""
        return DataCollatorForSeq2Seq(
            tokenizer=self.tokenizer,
            model=self.model,
            padding=True,
            return_tensors="pt"
        )
    
    def compute_metrics(self, eval_pred):
        """Compute metrics for evaluation"""
        predictions, labels = eval_pred
        
        # Decode predictions
        decoded_preds = self.tokenizer.batch_decode(predictions, skip_special_tokens=True)
        
        # Replace -100 in labels with pad token id
        labels = np.where(labels != -100, labels, self.tokenizer.pad_token_id)
        decoded_labels = self.tokenizer.batch_decode(labels, skip_special_tokens=True)
        
        # Simple metrics (ROUGE will be computed in evaluator)
        metrics = {}
        
        # Calculate average length metrics
        pred_lengths = [len(pred.split()) for pred in decoded_preds]
        label_lengths = [len(label.split()) for label in decoded_labels]
        
        metrics["avg_pred_length"] = np.mean(pred_lengths)
        metrics["avg_label_length"] = np.mean(label_lengths)
        
        return metrics
    
    def setup_training_arguments(self):
        """Setup training arguments for Seq2SeqTrainer"""
        return Seq2SeqTrainingArguments(
            output_dir=Config.OUTPUT_DIR,
            eval_strategy="steps",
            eval_steps=Config.EVAL_STEPS,
            save_strategy="steps",
            save_steps=Config.SAVE_STEPS,
            logging_strategy="steps",
            logging_steps=Config.LOGGING_STEPS,
            logging_dir=Config.LOG_DIR,
            
            # Training parameters
            num_train_epochs=Config.EPOCHS,
            per_device_train_batch_size=Config.BATCH_SIZE,
            per_device_eval_batch_size=Config.BATCH_SIZE,
            gradient_accumulation_steps=Config.GRADIENT_ACCUMULATION_STEPS,
            learning_rate=Config.LEARNING_RATE,
            weight_decay=Config.WEIGHT_DECAY,
            warmup_steps=Config.WARMUP_STEPS,
            
            # Optimization
            fp16=Config.FP16,
            dataloader_drop_last=True,
            load_best_model_at_end=True,
            metric_for_best_model="eval_loss",
            greater_is_better=False,
            
            # Generation parameters
            predict_with_generate=True,
            
            # Other settings
            seed=Config.SEED,
            report_to=None,  # Disable wandb/tensorboard
            save_total_limit=3,
            remove_unused_columns=False,
        )
    
    def train(self):
        """Train the summarization model"""
        print("🚀 Starting BART summarization training...")
        print(f"📊 Training configuration:")
        print(f"   - Model: {Config.MODEL_NAME}")
        print(f"   - Device: {Config.DEVICE}")
        print(f"   - Epochs: {Config.EPOCHS}")
        print(f"   - Batch size: {Config.BATCH_SIZE}")
        print(f"   - Learning rate: {Config.LEARNING_RATE}")
        print(f"   - Max input length: {Config.MAX_INPUT_LENGTH}")
        print(f"   - Max summary length: {Config.MAX_SUMMARY_LENGTH}")
        
        # Setup model
        self.setup_model()
        
        # Setup data collator
        data_collator = self.setup_data_collator()
        
        # Setup training arguments
        training_args = self.setup_training_arguments()
        
        # Create trainer
        trainer = Seq2SeqTrainer(
            model=self.model,
            args=training_args,
            train_dataset=self.dataset["train"],
            eval_dataset=self.dataset["validation"],
            data_collator=data_collator,
            processing_class=self.tokenizer,
            compute_metrics=self.compute_metrics,
        )
        
        # Start training
        print("🔥 Training started...")
        trainer.train()
        
        # Save model
        print("💾 Saving model...")
        trainer.save_model(Config.OUTPUT_DIR)
        self.tokenizer.save_pretrained(Config.OUTPUT_DIR)
        
        print(f"✅ Training completed!")
        print(f"💾 Model saved to: {Config.OUTPUT_DIR}")
        
        return trainer
    
    def evaluate(self, trainer=None):
        """Evaluate the trained model"""
        if trainer is None:
            # Load trained model for evaluation
            self.setup_model()
            data_collator = self.setup_data_collator()
            training_args = self.setup_training_arguments()
            
            trainer = Seq2SeqTrainer(
                model=self.model,
                args=training_args,
                eval_dataset=self.dataset["test"],
                data_collator=data_collator,
                tokenizer=self.tokenizer,
                compute_metrics=self.compute_metrics,
            )
        
        print("🔍 Evaluating model on test set...")
        eval_results = trainer.evaluate()
        
        print("📊 Evaluation results:")
        for key, value in eval_results.items():
            print(f"   - {key}: {value:.4f}")
        
        return eval_results