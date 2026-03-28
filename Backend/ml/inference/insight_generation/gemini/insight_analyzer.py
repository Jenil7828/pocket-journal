# GEMINI INSIGHTS ANALYZER
# Used when insights.use_gemini=true in config.yml
# Requires GEMINI_API_KEY in .env and active Google Cloud billing
# To switch to local model: set insights.use_gemini=false in config.yml

import os
import re
import json
import logging
from typing import Dict

from langchain_google_genai import ChatGoogleGenerativeAI
from ml.inference.insight_generation.gemini.guards import setup_gemini_env
from config_loader import get_config
from persistence.db_manager import DBManager

logger = logging.getLogger("pocket_journal.insights.gemini")


class InsightsGenerator:
    """
    Gemini-backed insights generator.
    Used when insights.use_gemini=true in config.yml.
    Requires GEMINI_API_KEY and active Google Cloud billing.
    """

    def __init__(self, db: DBManager, model_name=None, temperature=None, batch_size=None, insights_predictor=None):
        self.db = db
        cfg = get_config()["ml"]["insight_generation"]
        self.batch_size = batch_size or int(cfg["batch_size"])

        gemini = setup_gemini_env()
        if not gemini["enabled"]:
            raise RuntimeError(
                "Gemini is disabled or missing API key. "
                "Set GEMINI_API_KEY in .env or set insights.use_gemini=false in config.yml to use local model."
            )
        self.llm = ChatGoogleGenerativeAI(
            model=model_name or cfg["gemini_model_name"],
            temperature=temperature or float(cfg.get("temperature", 0.7)),
            max_retries=int(cfg["gemini_max_retries"]),
            google_api_key=gemini["api_key"],
        )

        prompt_path = os.path.join(
            os.path.dirname(__file__), "prompts", "journal_insights.txt"
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.prompt_template = f.read()

        logger.info("Gemini InsightsGenerator initialized model=%s", model_name or "gemini-2.0-flash")

    @staticmethod
    def parse_response(raw_text: str) -> Dict:
        """Defensive JSON extractor. Never raises."""
        if not raw_text or not isinstance(raw_text, str):
            return {}
        cleaned = re.sub(r"```(?:json)?", "", raw_text, flags=re.IGNORECASE)
        cleaned = re.sub(r"```", "", cleaned).strip()
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if not match:
            return {}
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}

    def generate_insights(self, uid: str, start_date: str = None, end_date: str = None) -> Dict:
        entries = self.db.fetch_entries_with_analysis(uid, start_date, end_date)

        combined = {
            "goals": [], "progress": "", "negative_behaviors": "",
            "remedies": "", "appreciation": "", "conflicts": "",
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

        all_entries_text = "\n\n".join(
            e.get("entry_text", "")
            for e in entries
            if e.get("entry_text", "").strip()
        )

        prompt = self.prompt_template.replace("{entries}", all_entries_text)
        response = self.llm.invoke(prompt)
        raw_text = response.content if hasattr(response, "content") else str(response)
        logger.info("Gemini response received length=%d", len(raw_text or ""))

        insights = self.parse_response(raw_text)
        if isinstance(insights.get("goals"), list):
            combined["goals"] = insights["goals"][:4]
        for key in ["progress", "negative_behaviors", "remedies", "appreciation", "conflicts"]:
            if isinstance(insights.get(key), str) and insights[key].strip():
                combined[key] = insights[key]

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



