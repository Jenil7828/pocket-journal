# LOCAL MODEL INSIGHTS ANALYZER
# Used when insights.use_gemini=false in config.yml (default)
# Uses Qwen2-1.5B-Instruct via HuggingFace (preferred) or Ollama
# To switch to Gemini: set insights.use_gemini=true in config.yml

import os
import re
import json
import logging
from typing import Dict

import requests as _requests
from config_loader import get_config
from services.utils.suppression import suppress_hf

from persistence.db_manager import DBManager

logger = logging.getLogger()


class LocalLLM:
    """
    Wraps InsightsPredictor (HuggingFace) or Ollama.
    If predictor is provided (pre-loaded at startup), uses it directly — zero startup cost.
    Otherwise tries Ollama, then loads HuggingFace in-process as last resort.
    """

    def __init__(self, predictor=None, ollama_model=None, ollama_base_url=None):
        self.logger = logging.getLogger()
        self._predictor = predictor
        self._ollama_model = ollama_model
        self._ollama_base_url = (ollama_base_url or "").rstrip("/")
        self._backend = get_config()["ml"]["insight_generation"].get("backend", "huggingface")

        if self._predictor is not None:
            self.logger.info("LocalLLM using pre-loaded InsightsPredictor (HuggingFace)")
        elif self._backend == "ollama":
            self.logger.info("LocalLLM using Ollama backend model=%s", self._ollama_model)
        else:
            self.logger.warning("No pre-loaded predictor — will load HuggingFace on first invoke")

    def _invoke_ollama(self, prompt: str) -> str:
        payload = {
            "model": self._ollama_model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.7, "num_predict": 1024}
        }
        resp = _requests.post(
            f"{self._ollama_base_url}/api/generate",
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("response", "")

    def _load_predictor_fallback(self):
        self.logger.warning("Loading InsightsPredictor in-process as last resort")
        from ml.inference.insight_generation.qwen2.predictor import InsightsPredictor
        self._predictor = InsightsPredictor()

    def invoke(self, prompt: str) -> str:
        # Preferred: use pre-loaded predictor (already on GPU from startup)
        if self._predictor is not None:
            return self._predictor.generate(prompt)

        # Ollama backend
        if self._backend == "ollama":
            try:
                return self._invoke_ollama(prompt)
            except Exception as e:
                self.logger.warning("Ollama failed error=%s — loading HuggingFace fallback", str(e))

        # Last resort: load in-process
        self._load_predictor_fallback()
        return self._predictor.generate(prompt)


class InsightsGenerator:
    def __init__(
        self,
        db: DBManager,
        model_name=None,
        temperature=None,
        batch_size=None,
        insights_predictor=None,
    ):
        self.db = db
        cfg = get_config()["ml"]["insight_generation"]
        self.batch_size = batch_size or int(cfg["batch_size"])

        self.llm = LocalLLM(
            predictor=insights_predictor,
            ollama_model=cfg["ollama_model"],
            ollama_base_url=cfg["ollama_base_url"],
        )

        prompt_path = os.path.join(
            os.path.dirname(__file__), "prompts", "journal_insights.txt"
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.prompt_template = f.read()

    @staticmethod
    def parse_gemini_response(raw_text: str) -> Dict:
        """
        Defensive JSON extractor for model responses.
        Never raises. Never trusts the model.
        """
        if not raw_text or not isinstance(raw_text, str):
            return {}

        # Remove markdown fences if model adds them
        cleaned = re.sub(r"```(?:json)?", "", raw_text, flags=re.IGNORECASE)
        cleaned = re.sub(r"```", "", cleaned)
        cleaned = cleaned.strip()

        # Extract the first JSON object found (greedy match to get full JSON)
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if not match:
            return {}

        json_str = match.group(0)

        try:
            parsed = json.loads(json_str)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}


    def generate_insights(self, uid: str, start_date: str = None, end_date: str = None) -> Dict:
        entries = self.db.fetch_entries_with_analysis(uid, start_date, end_date)

        combined = {
            "goals": [],
            "progress": "",
            "negative_behaviors": "",
            "remedies": "",
            "appreciation": "",
            "conflicts": "",
        }

        entry_ids_for_insight = [e["id"] for e in entries]

        if not entries:
            self.db.insert_insights(
                uid=uid, start_date=start_date, end_date=end_date,
                goals=combined["goals"], progress=combined["progress"],
                negative_behaviors=combined["negative_behaviors"],
                remedies=combined["remedies"], appreciation=combined["appreciation"],
                conflicts=combined["conflicts"],
                raw_response=json.dumps(combined, ensure_ascii=False),
                entry_ids=entry_ids_for_insight,
            )
            return combined

        # Build consolidated entries text from all entries
        all_entries_text = "\n\n".join(
            e.get('entry_text', '')
            for e in entries
            if e.get('entry_text', '').strip()
        )

        # Check if predictor supports per-field generation (HuggingFace path)
        predictor = getattr(self.llm, '_predictor', None)
        use_per_field = predictor is not None and hasattr(predictor, 'generate_field')

        if use_per_field:
            logger.info("Using per-field generation for %d entries", len(entries))

            field_instructions = {
                "progress": (
                    "Write 5-6 sentences about the specific positive steps, growth moments, and achievements "
                    "visible in these journal entries. Mention specific events, conversations, and accomplishments "
                    "by name. Explain what these moments reveal about this person's character and growth."
                ),
                "negative_behaviors": (
                    "Write 5-6 sentences identifying the specific recurring negative patterns, avoidance behaviors, "
                    "and unhealthy habits visible across these journal entries. Name each behavior specifically "
                    "and explain what situations trigger it and how these patterns connect to each other."
                ),
                "remedies": (
                    "Write 6 numbered actionable steps to address the specific problems mentioned in these entries. "
                    "Each step must reference a specific situation, habit, or event from the entries. "
                    "Make each step practical and immediately actionable."
                ),
                "appreciation": (
                    "Write 4-5 sentences genuinely appreciating the specific moments of courage, vulnerability, "
                    "self-awareness, and resilience visible in these entries. Name specific examples and explain "
                    "why each moment demonstrates strength."
                ),
                "conflicts": (
                    "Write 5-6 sentences describing the main internal and external conflicts visible across these "
                    "entries in detail. Include academic pressure, relationship tensions, financial stress, "
                    "and internal emotional struggles with specific examples from the entries."
                ),
                "goals": (
                    "Write exactly 4 goals for this person based on the entries. "
                    "For each goal write: TITLE: [short title] then DESCRIPTION: [2-3 sentence specific description]. "
                    "Separate goals with ---. Base each goal on specific patterns or needs visible in the entries."
                ),
            }

            for field, instruction in field_instructions.items():
                try:
                    raw = predictor.generate_field(all_entries_text, field, instruction)
                    if field == "goals":
                        goals = []
                        blocks = re.split(r'---', raw)
                        for block in blocks:
                            block = block.strip()
                            if not block:
                                continue
                            title_match = re.search(r'TITLE:\s*(.+)', block, re.IGNORECASE)
                            desc_match = re.search(r'DESCRIPTION:\s*(.+?)(?=TITLE:|$)', block, re.IGNORECASE | re.DOTALL)
                            if title_match and desc_match:
                                goals.append({
                                    "title": title_match.group(1).strip(),
                                    "description": desc_match.group(1).strip()
                                })
                        combined["goals"] = goals[:4] if goals else [{"title": "Personal growth", "description": raw[:300]}]
                    else:
                        combined[field] = raw
                    logger.info("Generated field=%s length=%d", field, len(raw))
                except Exception as e:
                    logger.error("Failed to generate field=%s error=%s", field, str(e))

        else:
            # Fallback: original batch approach for Ollama backend
            logger.info("Using batch prompt generation for %d entries", len(entries))
            for i in range(0, len(entries), self.batch_size):
                batch = entries[i: i + self.batch_size]
                batch_text = "\n".join(
                    f"Date: {e['created_at']}\nEntry: {e.get('entry_text', '')}\nAnalysis: {e.get('analysis', {}).get('summary', '')}"
                    for e in batch
                )
                prompt = self.prompt_template.replace("{entries}", batch_text)
                raw_text = self.llm.invoke(prompt)
                insights = self.parse_gemini_response(raw_text)
                if isinstance(insights.get("goals"), list):
                    combined["goals"].extend(insights["goals"])
                for key in ["progress", "negative_behaviors", "remedies", "appreciation", "conflicts"]:
                    if isinstance(insights.get(key), str):
                        combined[key] = f"{combined[key]}\n\n{insights[key]}" if combined[key] else insights[key]

            seen = set()
            unique_goals = []
            for g in combined["goals"]:
                title = g.get("title")
                if title and title not in seen:
                    seen.add(title)
                    unique_goals.append(g)
            combined["goals"] = unique_goals[:4]

        self.db.insert_insights(
            uid=uid, start_date=start_date, end_date=end_date,
            goals=combined["goals"], progress=combined["progress"],
            negative_behaviors=combined["negative_behaviors"],
            remedies=combined["remedies"], appreciation=combined["appreciation"],
            conflicts=combined["conflicts"],
            raw_response=json.dumps(combined, ensure_ascii=False),
            entry_ids=entry_ids_for_insight,
        )

        return combined




