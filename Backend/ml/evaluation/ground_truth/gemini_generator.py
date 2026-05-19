import os
import json
import logging
import time
import hashlib
from typing import Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger()

class GeminiGTGenerator:
    """Generates high-quality ground truth labels for journal entries using Gemini via LangChain.
    
    Includes caching and retry logic for robust automated evaluation.
    """
    
    def __init__(self, cache_dir: str = "ml/evaluation/cache", model_name: str = "gemini-2.5-flash"):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("[GEMINI] GEMINI_API_KEY not found in environment.")
            
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=self.api_key,
            temperature=0,
            max_retries=2
        )
        
        self.cache_path = os.path.join(cache_dir, "gemini_gt_cache.json")
        self.cache = self._load_cache()
        
        os.makedirs(cache_dir, exist_ok=True)
        
        # Setup prompt and parser
        self.prompt = ChatPromptTemplate.from_template("""
Analyze the following journal entry and provide ground truth labels for emotion detection and summarization.
You MUST respond with a valid JSON object only.

EMOTIONS (Soft labels 0.0 to 1.0):
- happy, sad, anger, fear, surprise, disgust, neutral
- These are multi-label; multiple emotions can have high scores if present.

INSIGHTS:
- core_issue: The main underlying problem or theme.
- behavior_pattern: Any recurring behavior described.
- recommendation_intent: What kind of recommendation would help this user?

FORMAT:
{{
  "summary": "Brief 1-2 sentence summary",
  "emotions": {{
    "happy": 0.0, "sad": 0.0, "anger": 0.0, "fear": 0.0, "surprise": 0.0, "disgust": 0.0, "neutral": 0.0
  }},
  "primary_emotion": "most dominant emotion name",
  "insight": {{
    "core_issue": "...",
    "behavior_pattern": "...",
    "recommendation_intent": "..."
  }}
}}

JOURNAL ENTRY:
\"\"\"{entry_text}\"\"\"
""")
        self.parser = JsonOutputParser()
        self.chain = self.prompt | self.llm | self.parser

    def _load_cache(self) -> Dict[str, Any]:
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error("[GEMINI] Failed to load cache: %s", str(e))
        return {}

    def _save_cache(self):
        try:
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            logger.error("[GEMINI] Failed to save cache: %s", str(e))

    def _get_text_hash(self, text: str) -> str:
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def generate_ground_truth(self, entry_text: str, retries: int = 3) -> Optional[Dict[str, Any]]:
        """Generate soft-label ground truth for a journal entry using LangChain."""
        if not self.api_key:
            return None
            
        text_hash = self._get_text_hash(entry_text)
        if text_hash in self.cache:
            logger.info("[GEMINI] Loaded GT from cache for entry.")
            return self.cache[text_hash]

        logger.info("[GEMINI] Generating GT for entry using LangChain...")
        
        for attempt in range(retries):
            try:
                result = self.chain.invoke({"entry_text": entry_text})
                
                # Validation
                required_keys = ["summary", "emotions", "primary_emotion", "insight"]
                if all(k in result for k in required_keys):
                    self.cache[text_hash] = result
                    self._save_cache()
                    
                    # Free tier rate limit — 20s mandatory sleep between requests
                    time.sleep(20)
                    return result
                
                logger.warning("[GEMINI] Response missing keys, attempt %d/%d", attempt + 1, retries)
                
            except Exception as e:
                # Custom wait times for Gemini Free Tier
                if "429" in str(e) or "quota" in str(e).lower():
                    wait = 30 if attempt == 0 else 60
                elif "503" in str(e) or "unavailable" in str(e).lower():
                    wait = 30 if attempt == 0 else 60
                else:
                    wait = 2 ** attempt
                
                logger.warning("[GEMINI] LangChain call failed, attempt %d/%d: %s. Waiting %ds", 
                               attempt + 1, retries, str(e), wait)
                time.sleep(wait)

        logger.error("[GEMINI] Failed to generate GT after %d retries.", retries)
        return None
