import os
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from .config import Config
from services.utils.suppression import suppress_hf
import logging

logger = logging.getLogger()


class SummarizationPredictor:
    def __init__(self, model_path: str | None = None):
        self.model_path = model_path or Config.OUTPUT_DIR
        self.device = Config.DEVICE
        self._use_onnx = False

        self._load_model()

    def _load_model(self):
        model_exists = (
            os.path.exists(self.model_path)
            and os.path.exists(os.path.join(self.model_path, "config.json"))
        )
        load_from = self.model_path if model_exists else Config.MODEL_NAME

        if model_exists:
            logger.info("Loading BART summarizer from %s", self.model_path)
        else:
            logger.warning(
                "Fine-tuned BART not found at %s — using base model %s",
                self.model_path, Config.MODEL_NAME
            )

        with suppress_hf():
            self.tokenizer = AutoTokenizer.from_pretrained(load_from)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                load_from,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            )

        self.model.to(self.device)
        self.model.eval()
        self._use_onnx = False

        gen_cfg = self.model.generation_config
        if gen_cfg.length_penalty is None:
            gen_cfg.length_penalty = 1.0
        if gen_cfg.num_beams is None or gen_cfg.num_beams < 1:
            gen_cfg.num_beams = 4
        if gen_cfg.early_stopping is None:
            gen_cfg.early_stopping = True
        if self.model.config.forced_bos_token_id is None:
            self.model.config.forced_bos_token_id = 0

        logger.info(
            "BART loaded successfully device=%s dtype=%s",
            self.device,
            "float16" if self.device == "cuda" else "float32"
        )


    def _prepare_input_text(self, text: str) -> tuple[str, dict]:
        """Preserve narrative beginning and ending when input exceeds model limit."""
        clean = text.strip()
        meta = {
            "input_chars": len(clean),
            "input_tokens": 0,
            "truncated": False,
            "strategy": "full",
            "head_preview": clean[:200],
            "tail_preview": clean[-200:] if len(clean) > 200 else clean,
        }
        if not clean:
            return clean, meta

        token_ids = self.tokenizer.encode(clean, add_special_tokens=False)
        meta["input_tokens"] = len(token_ids)
        # Reserve space for BOS/EOS during tokenization.
        token_budget = max(32, Config.MAX_INPUT_LENGTH - 2)
        if len(token_ids) <= token_budget:
            return clean, meta

        half = token_budget // 2
        head_text = self.tokenizer.decode(token_ids[:half], skip_special_tokens=True)
        tail_text = self.tokenizer.decode(token_ids[-half:], skip_special_tokens=True)
        prepared = f"{head_text}\n...\n{tail_text}"
        meta.update({
            "truncated": True,
            "strategy": "head_tail",
            "head_chars": len(head_text),
            "tail_chars": len(tail_text),
            "prepared_chars": len(prepared),
            "prepared_tokens": len(self.tokenizer.encode(prepared, add_special_tokens=False)),
        })
        return prepared, meta

    def summarize(
        self,
        text: str,
        max_length: int | None = None,
        min_length: int | None = None,
        num_beams: int | None = None,
    ) -> str:
        if not text or len(text.strip()) < 50:
            return text

        max_length = max_length or Config.MAX_SUMMARY_LENGTH
        min_length = min_length or Config.MIN_SUMMARY_LENGTH
        if num_beams is None:
            if self.device == "cuda":
                num_beams = Config.NUM_BEAMS_GPU
            elif self.device == "cpu":
                num_beams = Config.NUM_BEAMS_CPU
            else:
                num_beams = Config.NUM_BEAMS

        prepared_text, input_meta = self._prepare_input_text(text)
        logger.info(
            "[PERF][summarizer] event=summary_input "
            "input_chars=%s input_tokens=%s truncated=%s strategy=%s "
            "max_input_length=%s max_summary_length=%s min_summary_length=%s num_beams=%s "
            "head_preview=%r tail_preview=%r",
            input_meta["input_chars"],
            input_meta["input_tokens"],
            input_meta["truncated"],
            input_meta["strategy"],
            Config.MAX_INPUT_LENGTH,
            max_length,
            min_length,
            num_beams,
            input_meta["head_preview"],
            input_meta["tail_preview"],
        )

        inputs = self.tokenizer(
            prepared_text,
            max_length=Config.MAX_INPUT_LENGTH,
            truncation=True,
            padding=False,
            return_tensors="pt",
        )

        if not self._use_onnx:
            inputs = inputs.to(self.device)

        with torch.no_grad():
            output_ids = self.model.generate(
                **inputs,
                num_beams=num_beams,
                length_penalty=1.0,
                max_length=max_length,
                min_length=min_length,
                no_repeat_ngram_size=3,
                early_stopping=True,
            )

        summary = self.tokenizer.decode(output_ids[0], skip_special_tokens=True).strip()
        logger.info(
            "[PERF][summarizer] event=summary_output "
            "summary_chars=%s summary_tokens=%s truncated_input=%s",
            len(summary),
            len(self.tokenizer.encode(summary, add_special_tokens=False)),
            input_meta["truncated"],
        )
        return summary

    def summarize_batch(self, texts: list[str]) -> list[str]:
        return [self.summarize(t) for t in texts]






