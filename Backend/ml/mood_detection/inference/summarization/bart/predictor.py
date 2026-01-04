import os
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from .config import Config
import logging

logger = logging.getLogger("pocket_journal.summarizer")


class SummarizationPredictor:
    def __init__(self, model_path: str | None = None):
        self.model_path = model_path or Config.OUTPUT_DIR
        self.device = Config.DEVICE

        self._load_model()

    def _load_model(self):
        if os.path.exists(self.model_path) and os.path.exists(
            os.path.join(self.model_path, "config.json")
        ):
            logger.info("Loading fine-tuned BART summarizer from %s", self.model_path)
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_path)
        else:
            logger.warning(
                "Fine-tuned summarizer not found at %s, using base model %s",
                self.model_path,
                Config.MODEL_NAME,
            )
            self.tokenizer = AutoTokenizer.from_pretrained(Config.MODEL_NAME)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(Config.MODEL_NAME)

        self.model.to(self.device)
        self.model.eval()
        # ---- HARDEN GENERATION CONFIG (HF v4/v5 safe) ----
        gen_cfg = self.model.generation_config

        if gen_cfg.length_penalty is None:
            gen_cfg.length_penalty = 1.0

        if gen_cfg.num_beams is None or gen_cfg.num_beams < 1:
            gen_cfg.num_beams = 4

        if gen_cfg.early_stopping is None:
            gen_cfg.early_stopping = True

        if self.model.config.forced_bos_token_id is None:
            self.model.config.forced_bos_token_id = 0


    def summarize(
        self,
        text: str,
        max_length: int | None = None,
        min_length: int | None = None,
        num_beams: int = 4,
    ) -> str:
        if not text or len(text.strip()) < 50:
            return text

        max_length = max_length or Config.MAX_SUMMARY_LENGTH
        min_length = min_length or Config.MIN_SUMMARY_LENGTH

        inputs = self.tokenizer(
            text,
            max_length=Config.MAX_INPUT_LENGTH,
            truncation=True,
            padding="max_length",
            return_tensors="pt",
        ).to(self.device)

        with torch.no_grad():
            output_ids = self.model.generate(
                **inputs,
                num_beams=num_beams,
                length_penalty=1.0,
                max_length=max_length,
                min_length=min_length,
                # num_beams=num_beams,
                no_repeat_ngram_size=3,
                early_stopping=True,
            )

        return self.tokenizer.decode(output_ids[0], skip_special_tokens=True).strip()

    def summarize_batch(self, texts: list[str]) -> list[str]:
        return [self.summarize(t) for t in texts]

# import os
# import torch
# from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
# from .config import Config
# import logging

# logger = logging.getLogger("pocket_journal.summarizer")

# class SummarizationPredictor:
#     def __init__(self, model_path=None):
#         self.model_path = model_path or Config.OUTPUT_DIR
#         # Use Config for device detection only - handles CPU/GPU automatically
#         self.device = Config.DEVICE
        
#         # Load model and tokenizer
#         self._load_model()
        
#     def _load_model(self):
#         """Load the trained model or fallback to base model"""
#         if os.path.exists(self.model_path) and os.path.exists(os.path.join(self.model_path, "config.json")):
#             logger.info("Loading trained summarizer from %s", self.model_path)
#             self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
#             self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_path)
#         else:
#             logger.warning("Trained summarizer not found at %s; falling back to base model %s", self.model_path, Config.MODEL_NAME)
#             self.tokenizer = AutoTokenizer.from_pretrained(Config.MODEL_NAME)
#             self.model = AutoModelForSeq2SeqLM.from_pretrained(Config.MODEL_NAME)
        
#         # Fix BART configuration warning
#         # Set a compatible forced_bos_token_id only if tokenizer provides a bos token id
#         try:
#             bos_id = getattr(self.tokenizer, "bos_token_id", None)
#             if hasattr(self.model.config, 'forced_bos_token_id') and self.model.config.forced_bos_token_id is None and bos_id is not None:
#                 self.model.config.forced_bos_token_id = bos_id
#                 # Persist updated config to model path when possible
#                 try:
#                     if os.path.exists(self.model_path):
#                         self.model.config.save_pretrained(self.model_path)
#                 except Exception as _:
#                     logger.debug("Could not save updated model config to %s", self.model_path)
#         except Exception:
#             logger.debug("Error while normalizing model config; continuing without forced_bos changes")
        
#         # Move model to device (CPU or GPU based on Config)
#         try:
#             self.model.to(self.device)
#             self.model.eval()
#             logger.info("Model loaded on %s", self.device)
#         except Exception as e:
#             # Fallback to CPU if device error occurs
#             if self.device != "cpu":
#                 logger.warning("Error loading model on %s, falling back to CPU: %s", self.device, e)
#                 self.device = "cpu"
#                 self.model.to(self.device)
#                 self.model.eval()
#                 logger.info("Model loaded on %s", self.device)
#             else:
#                 raise
    
#     def summarize(self, text, max_length=None, min_length=None, num_beams=4, do_sample=False, temperature=1.0):
#         """
#         Generate summary for input text
        
#         Args:
#             text (str): Input text to summarize
#             max_length (int): Maximum length of summary
#             min_length (int): Minimum length of summary
#             num_beams (int): Number of beams for beam search
#             do_sample (bool): Whether to use sampling
#             temperature (float): Temperature for sampling
        
#         Returns:
#             str: Generated summary
#         """
#         if max_length is None:
#             max_length = Config.MAX_SUMMARY_LENGTH
#         if min_length is None:
#             min_length = Config.MIN_SUMMARY_LENGTH
        
#         # Preprocess text
#         text = str(text).strip()
#         if len(text) < 50:
#             return text  # Return original if too short
        
#         # Tokenize input
#         inputs = self.tokenizer(
#             text,
#             max_length=Config.MAX_INPUT_LENGTH,
#             padding="max_length",
#             truncation=True,
#             return_tensors="pt"
#         ).to(self.device)
        
#         # Generate summary - optimize parameters based on device (CPU vs GPU)
#         with torch.no_grad():
#             # Adjust generation parameters for CPU (faster) vs GPU (better quality)
#             is_cpu = self.device == "cpu"
            
#             # Use generation config to avoid deprecation warnings
#             generation_config = self.model.generation_config
#             generation_config.max_length = max_length or 80
#             generation_config.min_length = min_length or 25
#             # Reduce beams for CPU (faster inference), keep higher for GPU (better quality)
#             generation_config.num_beams = num_beams if not is_cpu else min(num_beams, 4)
#             generation_config.early_stopping = False
#             generation_config.do_sample = do_sample
#             generation_config.length_penalty = 2.0
#             generation_config.repetition_penalty = 1.1
#             generation_config.no_repeat_ngram_size = 3
#             generation_config.pad_token_id = self.tokenizer.pad_token_id
#             generation_config.eos_token_id = self.tokenizer.eos_token_id
            
#             outputs = self.model.generate(
#                 **inputs,
#                 generation_config=generation_config
#             )
        
#         # Decode summary
#         summary = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
#         return summary.strip()
    
#     def summarize_batch(self, texts, **kwargs):
#         """
#         Generate summaries for multiple texts
        
#         Args:
#             texts (list): List of input texts
#             **kwargs: Additional arguments for summarize method
        
#         Returns:
#             list: List of generated summaries
#         """
#         summaries = []
#         for i, text in enumerate(texts):
#             try:
#                 summary = self.summarize(text, **kwargs)
#                 summaries.append(summary)
#             except Exception as e:
#                 logger.warning("Error summarizing text %s: %s", i, e)
#                 summaries.append(text[:100] + "...")  # Fallback
        
#         return summaries
    
#     def get_summary_with_confidence(self, text, num_return_sequences=3):
#         """
#         Generate multiple summaries and return confidence scores
        
#         Args:
#             text (str): Input text
#             num_return_sequences (int): Number of summaries to generate
        
#         Returns:
#             dict: Summary with confidence score
#         """
#         summaries = []
        
#         for _ in range(num_return_sequences):
#             summary = self.summarize(text, do_sample=True, temperature=0.8)
#             summaries.append(summary)
        
#         # Calculate confidence based on consistency
#         unique_summaries = list(set(summaries))
#         confidence = len(unique_summaries) / len(summaries)
        
#         # Return most common summary
#         most_common = max(set(summaries), key=summaries.count)
        
#         return {
#             "summary": most_common,
#             "confidence": confidence,
#             "all_summaries": summaries
#         }
    
#     def summarize_with_length_control(self, text, target_length="medium"):
#         """
#         Generate summary with specific length control
        
#         Args:
#             text (str): Input text
#             target_length (str): "short", "medium", or "long"
        
#         Returns:
#             str: Generated summary
#         """
#         length_mapping = {
#             "short": (20, 40),
#             "medium": (40, 80),
#             "long": (80, 120)
#         }
        
#         if target_length not in length_mapping:
#             target_length = "medium"
        
#         min_len, max_len = length_mapping[target_length]
        
#         # Optimize num_beams based on device (CPU uses fewer beams for speed)
#         optimal_beams = 4 if self.device == "cpu" else 6
        
#         return self.summarize(
#             text,
#             min_length=min_len,
#             max_length=max_len,
#             num_beams=optimal_beams
#         )
    
#     def interactive_summarize(self):
#         """Interactive summarization mode"""
#         print("🤖 Interactive Summarization Mode")
#         print("Type 'quit' to exit")
#         print("=" * 50)
        
#         while True:
#             try:
#                 text = input("\n📝 Enter text to summarize: ").strip()
                
#                 if text.lower() in ['quit', 'exit', 'q']:
#                     print("👋 Goodbye!")
#                     break
                
#                 if len(text) < 20:
#                     print("⚠️ Text too short. Please enter longer text.")
#                     continue
                
#                 print("🔄 Generating summary...")
#                 summary = self.summarize(text)
                
#                 print(f"\n📋 Summary:")
#                 print(f"   {summary}")
                
#                 # Show length info
#                 print(f"\n📏 Length: {len(summary.split())} words")
                
#             except KeyboardInterrupt:
#                 print("\n👋 Goodbye!")
#                 break
#             except Exception as e:
#                 print(f"❌ Error: {e}")
    
#     def evaluate_sample(self, text, reference_summary=None):
#         """
#         Evaluate summary quality for a single sample
        
#         Args:
#             text (str): Input text
#             reference_summary (str): Reference summary for comparison
        
#         Returns:
#             dict: Evaluation results
#         """
#         generated_summary = self.summarize(text)
        
#         results = {
#             "text": text,
#             "generated_summary": generated_summary,
#             "summary_length": len(generated_summary.split()),
#             "compression_ratio": len(generated_summary.split()) / len(text.split())
#         }
        
#         if reference_summary:
#             results["reference_summary"] = reference_summary
#             results["reference_length"] = len(reference_summary.split())
            
#             # Simple overlap metric
#             gen_words = set(generated_summary.lower().split())
#             ref_words = set(reference_summary.lower().split())
#             overlap = len(gen_words.intersection(ref_words))
#             results["word_overlap"] = overlap / len(ref_words) if ref_words else 0
        
#         return results
