# GEMINI INSIGHTS ANALYZER
# Used when insights.use_gemini=true in config.yml
# Requires GEMINI_API_KEY in .env and active Google Cloud billing
# To switch to local model: set insights.use_gemini=false in config.yml

import os
import re
import json
import logging
import time
from datetime import datetime
from typing import Dict

from langchain_google_genai import ChatGoogleGenerativeAI
from ml.inference.insight_generation.gemini.guards import setup_gemini_env
from config_loader import get_config
from persistence.db_manager import DBManager

logger = logging.getLogger()


def fallback_insight(uid, start_date, end_date):
    return {
        "insights": [
            {
                "insight_id": "fallback",
                "appreciation": "You're beginning to reflect on your patterns more consistently.",
                "negative_behaviors": [],
                "conflicts": [],
                "goals": [],
                "created_at": datetime.now().isoformat(),
            }
        ]
    }


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
            raise RuntimeError("Gemini is required. Fallback models are disabled.")
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

        logger.info("Gemini InsightsGenerator initialized model=%s", model_name or "gemini-2.5-flash")

    @staticmethod
    def parse_response(raw_text: str) -> Dict:
        """Extract, clean, and normalize LLM output. Never raises."""
        if not raw_text or not isinstance(raw_text, str):
            return InsightsGenerator._empty_insights()
        
        # Extract JSON
        cleaned = re.sub(r"```(?:json)?", "", raw_text, flags=re.IGNORECASE)
        cleaned = re.sub(r"```", "", cleaned).strip()
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if not match:
            return InsightsGenerator._empty_insights()
        
        try:
            parsed = json.loads(match.group(0))
            if not isinstance(parsed, dict):
                return InsightsGenerator._empty_insights()
        except Exception:
            return InsightsGenerator._empty_insights()
        
        # Normalize stringified JSON fields
        for field in ["progress", "negative_behaviors", "remedies", "appreciation", "conflicts"]:
            if field in parsed and isinstance(parsed[field], str):
                try:
                    parsed[field] = json.loads(parsed[field])
                except (json.JSONDecodeError, TypeError):
                    pass
        
        # Normalize language: replace "user"/"the user" with "you"
        normalize_text = lambda text: re.sub(
            r"\b(?:the\s+)?user\b", "you", 
            text if isinstance(text, str) else "", 
            flags=re.IGNORECASE
        ) if isinstance(text, str) else text
        
        # Apply normalization to string fields
        parsed["progress"] = normalize_text(parsed.get("progress", ""))
        parsed["negative_behaviors"] = normalize_text(parsed.get("negative_behaviors", ""))
        parsed["remedies"] = normalize_text(parsed.get("remedies", ""))
        parsed["appreciation"] = normalize_text(parsed.get("appreciation", ""))
        parsed["conflicts"] = normalize_text(parsed.get("conflicts", ""))
        
        # Handle goals: ensure list, max 4, fill missing fields
        goals = parsed.get("goals", [])
        if not isinstance(goals, list):
            goals = []
        goals = goals[:4]
        for goal in goals:
            if not isinstance(goal, dict):
                goal = {}
            goal.setdefault("title", "")
            goal.setdefault("description", "")
            goal.setdefault("status", "")
            goal.setdefault("evidence", "")
            goal.setdefault("next_step", "")
            # Normalize language in goal descriptions
            goal["description"] = normalize_text(goal.get("description", ""))
            goal["evidence"] = normalize_text(goal.get("evidence", ""))
        
        parsed["goals"] = goals
        
        # Ensure all required fields exist
        return {
            "goals": parsed.get("goals", []),
            "progress": parsed.get("progress", ""),
            "negative_behaviors": parsed.get("negative_behaviors", ""),
            "remedies": parsed.get("remedies", ""),
            "appreciation": parsed.get("appreciation", ""),
            "conflicts": parsed.get("conflicts", ""),
        }
    
    @staticmethod
    def _empty_insights() -> Dict:
        """Return empty insights structure."""
        return {
            "goals": [],
            "progress": "",
            "negative_behaviors": "",
            "remedies": "",
            "appreciation": "",
            "conflicts": "",
        }

    def generate_insights(self, uid: str, start_date: str = None, end_date: str = None) -> Dict:
        entries = self.db.fetch_entries_with_analysis(uid, start_date, end_date)
        entries = entries[-10:]

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
        response = None
        for attempt in range(2):
            try:
                response = self.llm.invoke(prompt)
                break
            except Exception as e:
                if attempt == 1:
                    logger.warning("Gemini failed, fallback used: %s", str(e))
                    return fallback_insight(uid, start_date, end_date)
                time.sleep(1)

        if response is None:
            logger.warning("Gemini failed, fallback used")
            return fallback_insight(uid, start_date, end_date)

        raw_text = response.content if hasattr(response, "content") else str(response)
        logger.info("Gemini response received length=%d", len(raw_text or ""))

        insights = self.parse_response(raw_text)
        if not isinstance(insights, dict):
            logger.warning("Gemini failed, fallback used")
            return fallback_insight(uid, start_date, end_date)

        if not any(insights.get(key) for key in ["goals", "progress", "negative_behaviors", "remedies", "appreciation", "conflicts"]):
            logger.warning("Gemini failed, fallback used")
            return fallback_insight(uid, start_date, end_date)

        if isinstance(insights.get("goals"), list):
            combined["goals"] = insights["goals"][:4]

        # Convert structured outputs to strings for DB compatibility
        combined["progress"] = json.dumps(insights.get("progress", ""), ensure_ascii=False)
        combined["negative_behaviors"] = json.dumps(insights.get("negative_behaviors", ""), ensure_ascii=False)
        combined["remedies"] = json.dumps(insights.get("remedies", ""), ensure_ascii=False)
        combined["appreciation"] = json.dumps(insights.get("appreciation", ""), ensure_ascii=False)
        combined["conflicts"] = json.dumps(insights.get("conflicts", ""), ensure_ascii=False)

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



