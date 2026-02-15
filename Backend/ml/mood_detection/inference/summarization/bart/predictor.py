import os
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from .config import Config
from services.suppression import suppress_hf
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
            with suppress_hf():
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
                self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_path)
        else:
            logger.warning(
                "Fine-tuned summarizer not found at %s, using base model %s",
                self.model_path,
                Config.MODEL_NAME,
            )
            with suppress_hf():
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
