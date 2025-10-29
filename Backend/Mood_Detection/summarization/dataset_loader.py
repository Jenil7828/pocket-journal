import os
import pandas as pd
import numpy as np
from datasets import Dataset
from transformers import AutoTokenizer
from .config import Config

class SummarizationDatasetLoader:
    def __init__(self, csv_path=None):
        self.csv_path = csv_path or Config.DATASET_PATH
        self.tokenizer = AutoTokenizer.from_pretrained(Config.MODEL_NAME)
        
    def load_csv_data(self):
        """Load and preprocess CSV data with automatic column detection"""
        try:
            # Load CSV
            df = pd.read_csv(self.csv_path)
            print(f"📊 Loaded CSV with {len(df)} rows and {len(df.columns)} columns")
            print(f"📋 Columns: {list(df.columns)}")
            
            # Detect text and summary columns
            text_col, summary_col = Config.detect_columns(self.csv_path)
            print(f"🔍 Detected text column: '{text_col}'")
            print(f"🔍 Detected summary column: '{summary_col}'")
            
            # Validate columns exist
            if text_col not in df.columns:
                raise ValueError(f"Text column '{text_col}' not found in CSV")
            if summary_col not in df.columns:
                raise ValueError(f"Summary column '{summary_col}' not found in CSV")
            
            # Clean and filter data
            df = df.dropna(subset=[text_col, summary_col])
            df = df[df[text_col].str.len() > 50]  # Filter very short texts
            df = df[df[summary_col].str.len() > 10]  # Filter very short summaries
            
            print(f"✅ After cleaning: {len(df)} valid samples")
            
            # Convert to lists
            texts = df[text_col].astype(str).tolist()
            summaries = df[summary_col].astype(str).tolist()
            
            return texts, summaries, text_col, summary_col
            
        except Exception as e:
            print(f"❌ Error loading CSV data: {e}")
            raise
    
    def preprocess_text(self, text, max_length=None):
        """Preprocess text for BART model"""
        if max_length is None:
            max_length = Config.MAX_INPUT_LENGTH
            
        # Basic cleaning
        text = str(text).strip()
        
        # Truncate if too long
        if len(text) > max_length * 4:  # Rough character to token ratio
            text = text[:max_length * 4]
            
        return text
    
    def preprocess_summary(self, summary, max_length=None):
        """Preprocess summary for BART model"""
        if max_length is None:
            max_length = Config.MAX_SUMMARY_LENGTH
            
        # Basic cleaning
        summary = str(summary).strip()
        
        # Ensure minimum length
        if len(summary) < Config.MIN_SUMMARY_LENGTH:
            return None
            
        return summary
    
    def tokenize_function(self, examples):
        """Tokenize texts and summaries for Seq2Seq training"""
        # Preprocess texts
        texts = [self.preprocess_text(text) for text in examples["text"]]
        summaries = [self.preprocess_summary(summary) for summary in examples["summary"]]
        
        # Filter out invalid summaries
        valid_indices = [i for i, s in enumerate(summaries) if s is not None]
        texts = [texts[i] for i in valid_indices]
        summaries = [summaries[i] for i in valid_indices]
        
        # Tokenize inputs
        model_inputs = self.tokenizer(
            texts,
            max_length=Config.MAX_INPUT_LENGTH,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        )
        
        # Tokenize targets
        labels = self.tokenizer(
            text_target=summaries,
            max_length=Config.MAX_SUMMARY_LENGTH,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        )
        
        # Replace padding token ids with -100 for loss calculation
        labels["input_ids"] = labels["input_ids"].masked_fill(
            labels["input_ids"] == self.tokenizer.pad_token_id, -100
        )
        
        model_inputs["labels"] = labels["input_ids"]
        
        return model_inputs
    
    def create_dataset(self):
        """Create HuggingFace Dataset from CSV data"""
        # Load data
        texts, summaries, text_col, summary_col = self.load_csv_data()
        
        # Create dataset dictionary
        dataset_dict = {
            "text": texts,
            "summary": summaries
        }
        
        # Create HuggingFace Dataset
        dataset = Dataset.from_dict(dataset_dict)
        
        # Tokenize dataset
        print("🔄 Tokenizing dataset...")
        tokenized_dataset = dataset.map(
            self.tokenize_function,
            batched=True,
            remove_columns=dataset.column_names
        )
        
        # Split dataset
        train_test_split = tokenized_dataset.train_test_split(
            test_size=Config.TEST_SPLIT,
            seed=Config.SEED
        )
        
        train_val_split = train_test_split["train"].train_test_split(
            test_size=Config.VALIDATION_SPLIT,
            seed=Config.SEED
        )
        
        final_dataset = {
            "train": train_val_split["train"],
            "validation": train_val_split["test"],
            "test": train_test_split["test"]
        }
        
        print(f"📊 Dataset splits:")
        print(f"   - Train: {len(final_dataset['train'])} samples")
        print(f"   - Validation: {len(final_dataset['validation'])} samples")
        print(f"   - Test: {len(final_dataset['test'])} samples")
        
        return final_dataset
    
    def get_data_statistics(self):
        """Get statistics about the dataset"""
        try:
            df = pd.read_csv(self.csv_path)
            text_col, summary_col = Config.detect_columns(self.csv_path)
            
            text_lengths = df[text_col].str.len()
            summary_lengths = df[summary_col].str.len()
            
            stats = {
                "total_samples": len(df),
                "text_length_stats": {
                    "mean": text_lengths.mean(),
                    "std": text_lengths.std(),
                    "min": text_lengths.min(),
                    "max": text_lengths.max(),
                    "median": text_lengths.median()
                },
                "summary_length_stats": {
                    "mean": summary_lengths.mean(),
                    "std": summary_lengths.std(),
                    "min": summary_lengths.min(),
                    "max": summary_lengths.max(),
                    "median": summary_lengths.median()
                }
            }
            
            return stats
            
        except Exception as e:
            print(f"Error getting statistics: {e}")
            return None