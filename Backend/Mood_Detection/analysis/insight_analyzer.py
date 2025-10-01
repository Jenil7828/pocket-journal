# insight_analyzer.py
import re
import json
from database.db_manager import DBManager
from langchain_google_genai import ChatGoogleGenerativeAI

class InsightsGenerator:
    def __init__(self, db, model_name="gemini-2.0-flash", temperature=0.7, batch_size=20):
        self.db = db
        self.llm = ChatGoogleGenerativeAI(model=model_name, temperature=temperature)
        self.batch_size = batch_size

    @staticmethod
    def parse_gemini_response(raw_text: str) -> dict:
        """Extract clean JSON from Gemini response text"""
        raw_text = re.sub(r"^```json\s*|\s*```$", "", raw_text.strip(), flags=re.IGNORECASE)
        match = re.search(r"\{.*\}", raw_text, flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return {}
        return {}

    def generate_insights(self, user_id: int, start_date: str, end_date: str) -> dict:
        entries = self.db.fetch_entries_with_analysis(user_id, start_date, end_date)

        combined = {
            "goals": [],  # List of {title, description}
            "progress": "",
            "negative_behaviors": "",
            "remedies": "",
            "appreciation": "",
            "conflicts": ""
        }

        for i in range(0, len(entries), self.batch_size):
            batch = entries[i:i + self.batch_size]
            batch_text = "\n".join(
                f"Date: {e['created_at'].date()}\nEntry: {e['entry_text']}"
                for e in batch
            )

            prompt = f"""
You are my personal journaling coach speaking directly to me in first person. 
Focus on **3-4 goals max** that are most significant in the entries and explain why they matter. 
Each goal should have a **title** (short phrase) and a **description** (explains progress, significance, or advice). 

Analyze these journal entries:

{batch_text}

Return JSON ONLY, structured as:

{{
  "goals": [
    {{
      "title": "",
      "description": ""
    }}
  ],
  "progress": "",
  "negative_behaviors": "",
  "remedies": "",
  "appreciation": "",
  "conflicts": ""
}}

⚠️ Important:
- Use first-person tone, speaking directly to me.
- Keep other fields (progress, negative_behaviors, etc.) as short paragraphs.
- Do NOT list every single entry; summarize trends and insights.
"""

            response = self.llm.invoke(prompt)
            raw_text = response.content if hasattr(response, "content") else str(response)
            insights = self.parse_gemini_response(raw_text)

            # Merge structured goals
            if "goals" in insights and isinstance(insights["goals"], list):
                combined["goals"].extend(insights["goals"])

            # Merge paragraph-style fields
            for key in ["progress", "negative_behaviors", "remedies", "appreciation", "conflicts"]:
                if key in insights and isinstance(insights[key], str):
                    if combined[key]:
                        combined[key] += "\n\n" + insights[key]
                    else:
                        combined[key] = insights[key]

        # Deduplicate goals by title
        seen_titles = set()
        unique_goals = []
        for g in combined["goals"]:
            title = g.get("title")
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_goals.append(g)
        combined["goals"] = unique_goals[:4]  # limit to 3-4 max

        # Save to DB
        self.db.insert_insights(
            user_id=user_id, start_date=start_date, end_date=end_date,
            goals=combined["goals"], progress=combined["progress"],
            negative_behaviors=combined["negative_behaviors"], remedies=combined["remedies"],
            appreciation=combined["appreciation"], conflicts=combined["conflicts"],
            raw_response=json.dumps(combined, ensure_ascii=False)
        )

        return combined


if __name__ == "__main__":
    db = DBManager()
    generator = InsightsGenerator(db)
    insights = generator.generate_insights(
        user_id=1,
        start_date="2025-09-01",
        end_date="2025-09-30"
    )
    print(json.dumps(insights, indent=2, ensure_ascii=False))