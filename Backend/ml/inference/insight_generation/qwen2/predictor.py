import os
import logging
import torch
from config_loader import get_config
from services.utils.suppression import suppress_hf

logger = logging.getLogger("pocket_journal.insights.predictor")


class InsightsPredictor:
    """
    Qwen2-1.5B-Instruct predictor for journal insights generation.
    Loaded at startup alongside BART and RoBERTa.
    Stored at Backend/ml/models/insight_generation/qwen2/v1/
    Falls back to downloading from HuggingFace if local model not found.
    """

    def __init__(self, model_path: str = None):
        cfg = get_config()["ml"]["insight_generation"]
        if model_path is None:
            # File is at Backend/ml/inference/insight_generation/qwen2/predictor.py
            # Walk up 5 levels to Backend/
            _here = os.path.dirname(os.path.abspath(__file__))
            _backend_dir = os.path.dirname(
                os.path.dirname(
                    os.path.dirname(
                        os.path.dirname(
                            os.path.dirname(_here)
                        )
                    )
                )
            )
            
            # Check if custom models directory is configured
            ml_cfg = get_config()["ml"]
            _custom_models_dir = ml_cfg.get("models_base_dir", "").strip()
            if _custom_models_dir:
                # Custom external models directory
                if os.path.isabs(_custom_models_dir):
                    _models_base = _custom_models_dir
                else:
                    # Relative to Backend/
                    _models_base = os.path.join(_backend_dir, _custom_models_dir)
            else:
                # Default: Backend/ml/models/
                _models_base = os.path.join(_backend_dir, "ml", "models")
            
            model_path = os.path.join(
                _models_base, cfg["hf_model_dir"].replace("ml/models/", "")
            )
        self.model_path = model_path
        self.model_name = cfg["hf_model_name"]
        self.max_new_tokens = int(cfg["max_new_tokens"])
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        if self.device == "cpu":
            logger.warning("CUDA not available — Qwen2 insights will run on CPU and be slow")
        self._pipeline = None
        self._load_model()

    def _load_model(self):
        from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

        model_exists = (
            os.path.exists(self.model_path)
            and os.path.exists(os.path.join(self.model_path, "config.json"))
        )
        load_from = self.model_path if model_exists else self.model_name

        if model_exists:
            logger.info("Loading Qwen2 insights model from local path=%s", self.model_path)
        else:
            logger.warning(
                "Local Qwen2 model not found at %s — downloading from HuggingFace model=%s",
                self.model_path, self.model_name
            )

        with suppress_hf():
            tokenizer = AutoTokenizer.from_pretrained(load_from)
            model = AutoModelForCausalLM.from_pretrained(
                load_from,
                torch_dtype=torch.float16,
                low_cpu_mem_usage=True,
            )
            if not model_exists:
                os.makedirs(self.model_path, exist_ok=True)
                logger.info("Saving Qwen2 model to local path=%s", self.model_path)
                model.save_pretrained(self.model_path)
                tokenizer.save_pretrained(self.model_path)
                logger.info("Qwen2 model saved locally — subsequent startups will load from disk")
            model = model.to(self.device)
            self._pipeline = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
                device=0 if self.device == "cuda" else -1,
            )

        try:
            device_name = torch.cuda.get_device_name(0) if self.device == "cuda" else "CPU"
            logger.info(
                "Qwen2 insights loaded successfully device=%s dtype=float16 hardware=%s",
                self.device, device_name
            )
        except Exception:
            logger.info("Qwen2 insights loaded successfully device=%s dtype=float16", self.device)

    def generate(self, prompt: str) -> str:
        if self._pipeline is None:
            raise RuntimeError("InsightsPredictor pipeline not loaded")
        tokenizer = self._pipeline.tokenizer
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant that analyzes journal entries and returns insights as JSON. "
                    "Always return valid JSON with all fields filled. Never return empty strings or empty lists. "
                    "Never use markdown code blocks. Return only the raw JSON object."
                )
            },
            {"role": "user", "content": prompt}
        ]
        formatted = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        with suppress_hf():
            output = self._pipeline(
                formatted,
                max_new_tokens=self.max_new_tokens,
                do_sample=True,
                temperature=0.8,
                top_p=0.9,
                repetition_penalty=1.15,
                pad_token_id=tokenizer.eos_token_id,
            )
        generated = output[0]["generated_text"]
        if generated.startswith(formatted):
            generated = generated[len(formatted):]
        return generated.strip()

    def generate_field(self, entries_text: str, field: str, instruction: str) -> str:
        """Generate a single insight field with a focused prompt."""
        if self._pipeline is None:
            raise RuntimeError("InsightsPredictor pipeline not loaded")
        tokenizer = self._pipeline.tokenizer
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an empathetic personal journal coach. "
                    "Analyze the journal entries and respond with exactly what is asked. "
                    "Be specific, detailed, and reference actual events from the entries. "
                    "Write in second person. Never be generic."
                )
            },
            {
                "role": "user",
                "content": (
                    f"JOURNAL ENTRIES:\n{entries_text}\n\n"
                    f"TASK: {instruction}\n\n"
                    f"Write your response now (plain text only, no JSON, no labels):"
                )
            }
        ]
        formatted = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        with suppress_hf():
            output = self._pipeline(
                formatted,
                max_new_tokens=512,
                do_sample=True,
                temperature=0.8,
                top_p=0.9,
                repetition_penalty=1.15,
                pad_token_id=tokenizer.eos_token_id,
            )
        generated = output[0]["generated_text"]
        if generated.startswith(formatted):
            generated = generated[len(formatted):]
        return generated.strip()



