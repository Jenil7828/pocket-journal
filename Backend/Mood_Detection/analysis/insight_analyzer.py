import os
import re
import json
from Mood_Detection.database.db_manager import DBManager
from langchain_google_genai import ChatGoogleGenerativeAI

# Set Gemini credentials explicitly
GEMINI_JSON = os.getenv("GEMINI_CREDENTIALS_PATH")
if GEMINI_JSON:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GEMINI_JSON
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

class InsightsGenerator:
    def __init__(self, db: DBManager, model_name="gemini-2.0-flash", temperature=0.7, batch_size=20):
        self.db = db
        self.llm = ChatGoogleGenerativeAI(model=model_name, temperature=temperature)
        self.batch_size = batch_size

    @staticmethod
    def parse_gemini_response(raw_text: str) -> dict:
        raw_text = re.sub(r"^```json\s*|\s*```$", "", raw_text.strip(), flags=re.IGNORECASE)
        match = re.search(r"\{.*\}", raw_text, flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return {}
        return {}

    def generate_insights(self, uid: str, start_date: str = None, end_date: str = None) -> dict:
        entries = self.db.fetch_entries_with_analysis(uid, start_date, end_date)
        combined = {
            "goals": [], "progress": "", "negative_behaviors": "",
            "remedies": "", "appreciation": "", "conflicts": ""
        }

        # Track entry_ids used for this insight
        entry_ids_for_insight = [e["id"] for e in entries]

        for i in range(0, len(entries), self.batch_size):
            batch = entries[i:i + self.batch_size]
            batch_text = "\n".join(
                f"Date: {e['created_at']}\nEntry: {e.get('entry_text','')}\nAnalysis: {e.get('analysis',{}).get('summary','')}"
                for e in batch
            )

            prompt = f"""
            You are my personal journaling coach. Focus on 3-4 key goals and summarize insights.
            Analyze these entries:
            {batch_text}
            
            Return JSON ONLY:
            {{
            "goals": [{{"title": "", "description": ""}}],
            "progress": "",
            "negative_behaviors": "",
            "remedies": "",
            "appreciation": "",
            "conflicts": ""
            }}
            """
            response = self.llm.invoke(prompt)
            raw_text = response.content if hasattr(response, "content") else str(response)
            insights = self.parse_gemini_response(raw_text)

            # Merge goals
            if "goals" in insights and isinstance(insights["goals"], list):
                combined["goals"].extend(insights["goals"])
            # Merge paragraphs
            for key in ["progress", "negative_behaviors", "remedies", "appreciation", "conflicts"]:
                if key in insights and isinstance(insights[key], str):
                    combined[key] += "\n\n" + insights[key] if combined[key] else insights[key]

        # Deduplicate goals
        seen = set()
        unique_goals = []
        for g in combined["goals"]:
            title = g.get("title")
            if title and title not in seen:
                seen.add(title)
                unique_goals.append(g)
        combined["goals"] = unique_goals[:4]

        # Save insights to DB
        self.db.insert_insights(
            uid=uid,
            start_date=start_date,
            end_date=end_date,
            goals=combined["goals"],
            progress=combined["progress"],
            negative_behaviors=combined["negative_behaviors"],
            remedies=combined["remedies"],
            appreciation=combined["appreciation"],
            conflicts=combined["conflicts"],
            raw_response=json.dumps(combined, ensure_ascii=False),
            entry_ids=entry_ids_for_insight
        )
        combined['entry'] = entries[:4]
        return combined

