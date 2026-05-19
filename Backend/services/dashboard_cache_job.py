"""
AI Cache Generation Job - Scheduled Daily at 2 AM

This runs OUTSIDE API cycle to generate:
- behavioral_pattern
- suggested_actions
- motivation_line

Stores in: dashboard_cache/{uid}

Rules:
- Runs only if user had activity in last 3 days
- Skips if cache still valid
- Uses fallback if AI fails
"""

import logging
import os
from datetime import datetime, timedelta
import pytz
from firebase_admin import firestore
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger()
TZ = pytz.timezone("Asia/Kolkata")


def _clean_text(text: str, max_len: int = 160) -> str:
    """Clean text: remove quotes, normalize spaces, trim at sentence boundary."""
    if not text:
        return ""
    
    text = str(text).strip()
    
    # Remove wrapping quotes
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1].strip()
    
    # Remove leading quotes
    text = text.lstrip('"').strip()
    
    # Normalize spaces
    text = " ".join(text.split())
    
    # Trim at sentence boundary if over max_len
    if len(text) > max_len:
        sentences = text.split(". ")
        output = ""
        
        for sentence in sentences:
            test_add = output + sentence.strip() + ". "
            if len(test_add) <= max_len:
                output = test_add
            else:
                break
        
        text = output.strip()
        if text and not text.endswith("."):
            text = text + "."
    
    return text


def fallback_ai_insight(insight: dict) -> str:
    """Safe fallback for ai_insight when AI fails."""
    if not insight:
        return "You're starting to reflect more on your patterns."
    
    try:
        appreciation = str(insight.get("appreciation", "")).strip()
        if appreciation:
            return _clean_text(appreciation, 120)
        
        behaviors = insight.get("negative_behaviors", [])
        if behaviors and isinstance(behaviors, list) and len(behaviors) > 0:
            behavior_text = str(behaviors[0]).strip()
            return _clean_text(f"You're noticing patterns: {behavior_text}.", 120)
    except Exception:
        pass
    
    return "Keep reflecting—your awareness is building."


def fallback_behavioral_pattern(insight: dict) -> str:
    """Generate fallback behavioral pattern from insight."""
    if not insight:
        return "Keep exploring your thoughts through journaling."
    
    try:
        behaviors = insight.get("negative_behaviors", [])
        conflicts = insight.get("conflicts", [])
        
        if behaviors and conflicts:
            behavior = str(behaviors[0]).strip() if behaviors else ""
            conflict = str(conflicts[0]).strip() if conflicts else ""
            return _clean_text(f"You tend to struggle with {behavior} when facing {conflict}.", 200)
        elif behaviors:
            behavior = str(behaviors[0]).strip()
            return _clean_text(f"A pattern is noticing {behavior}. Recognizing it is the first step.", 200)
        elif conflicts:
            conflict = str(conflicts[0]).strip()
            return _clean_text(f"You often face {conflict}. Your responses are evolving.", 200)
    except Exception:
        pass
    
    return "Keep exploring your thoughts through journaling."


def generate_ai_cache_for_user(uid: str, db):
    """
    Generate AI cache for single user.
    
    Only runs if:
    1. User had journal entry in last 3 days
    2. Cache missing or older than 24 hours
    """
    try:
        # Check if user has recent activity (last 3 days)
        three_days_ago = datetime.now(TZ) - timedelta(days=3)
        
        recent_query = db.db.collection("journal_entries").where(
            filter=firestore.FieldFilter("uid", "==", uid)
        ).where(
            filter=firestore.FieldFilter("created_at", ">", three_days_ago)
        ).limit(1)
        
        has_recent_activity = False
        for _ in recent_query.stream():
            has_recent_activity = True
            break
        
        if not has_recent_activity:
            logger.info("User %s has no recent activity. Skipping AI generation.", uid)
            return
        
        # Check if cache is still valid
        cache_doc = db.db.collection("dashboard_cache").document(uid).get()
        if cache_doc.exists:
            cache_data = cache_doc.to_dict()
            generated_at = cache_data.get("generated_at")
            
            if generated_at:
                try:
                    if isinstance(generated_at, str):
                        gen_time = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
                    else:
                        gen_time = generated_at
                    
                    age = datetime.now(TZ) - gen_time
                    if age.total_seconds() < 24 * 3600:
                        logger.info("Cache still valid for user %s. Skipping generation.", uid)
                        return
                except Exception:
                    pass
        
        # Fetch latest insight + 7 days of entries for AI context
        from services import insights_service, journal_entries as je
        
        try:
            insights_response, _ = insights_service.get_insights(uid, limit=1, offset=0, db=db)
            insight = None
            if "insights" in insights_response and insights_response["insights"]:
                insight = insights_response["insights"][0]
        except Exception as e:
            logger.warning("Failed to fetch insight for AI: %s", str(e))
            insight = None
        
        # If no insight, use fallback
        if not insight:
            _store_cache_fallback(uid, db)
            return
        
        # Try to call AI (Gemini)
        try:
            ai_result = _call_gemini_api(uid, db, insight)
            if ai_result:
                _store_cache(uid, db, ai_result, insight)
            else:
                _store_cache_fallback(uid, db, insight)
        except Exception as e:
            logger.exception("AI generation failed, using fallback: %s", str(e))
            _store_cache_fallback(uid, db, insight)
        
        logger.info("AI cache generated for uid=%s", uid)
    
    except Exception as e:
        logger.exception("Failed to generate AI cache for user %s: %s", uid, str(e))


def _call_gemini_api(uid: str, db, insight: dict) -> dict:
    """
    Call Gemini API via LangChain with structured prompt and JSON parser.
    Includes retry logic to handle 503 errors.
    
    Returns:
    {
      "ai_insight": string,
      "behavioral_pattern": string,
      "suggested_actions": [{title, subtitle}, ...],
      "motivation_line": string
    }
    """
    MAX_RETRIES = 2
    attempt = 0
    
    while attempt < MAX_RETRIES:
        try:
            attempt += 1
            # Build context from insight
            context = _build_ai_context(uid, db, insight)
            
            # Initialize JSON parser with format instructions
            parser = JsonOutputParser()
            
            # Load prompt template from file
            prompt_file = os.path.join(
                os.path.dirname(__file__), 
                "prompts", 
                "dashboard_cache.txt"
            )
            
            if not os.path.exists(prompt_file):
                logger.warning("Prompt template not found at %s", prompt_file)
                return None
            
            with open(prompt_file, "r") as f:
                prompt_text = f.read()
            
            # Create prompt template with format instructions for strict JSON
            prompt = PromptTemplate.from_template(
                prompt_text + "\n\n{format_instructions}"
            ).partial(
                format_instructions=parser.get_format_instructions()
            )
            
            # Initialize LLM
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                logger.warning("GEMINI_API_KEY not set in environment")
                return None
            
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                temperature=0.4,
                google_api_key=api_key
            )
            
            # Build chain: prompt -> llm -> parser
            chain = prompt | llm | parser
            
            # Execute chain
            result = chain.invoke({
                "emotions": context.get("top_emotions", []),
                "consistency": context.get("journaling_consistency", 0),
                "struggles": context.get("insight_fields", {}).get("negative_behaviors", []),
                "conflicts": context.get("insight_fields", {}).get("conflicts", []),
                "strengths": context.get("insight_fields", {}).get("appreciation", ""),
                "goals": context.get("insight_fields", {}).get("goals", 0),
            })
            
            # Validation layer
            if not isinstance(result, dict):
                logger.warning("Invalid AI result format")
                return None
            
            # Clean and extract all fields
            ai_insight = _clean_text(result.get("ai_insight", ""), 150)
            behavioral_pattern = _clean_text(result.get("behavioral_pattern", ""), 200)
            motivation_line = _clean_text(result.get("motivation_line", ""), 120)
            
            # CRITICAL: Ensure ai_insight exists (fallback to behavioral_pattern if missing)
            if not ai_insight:
                logger.warning("AI result missing ai_insight, using behavioral_pattern as fallback")
                ai_insight = behavioral_pattern
            
            # CRITICAL: Ensure behavioral_pattern exists
            if not behavioral_pattern:
                logger.warning("AI result missing behavioral_pattern")
                behavioral_pattern = fallback_behavioral_pattern(insight)
            
            # Prevent duplication
            if behavioral_pattern.strip() == ai_insight.strip():
                logger.warning("Duplicate detected: ai_insight == behavioral_pattern, regenerating")
                behavioral_pattern = fallback_behavioral_pattern(insight)
            
            # CRITICAL: Ensure motivation_line exists
            if not motivation_line or len(motivation_line.split()) < 4:
                motivation_line = _clean_text("Write what just happened before it fades.", 120)
            
            # Ensure suggested_actions is list
            suggested_actions = result.get("suggested_actions", [])
            if not isinstance(suggested_actions, list):
                suggested_actions = []
            
            # Validate and clean each action
            cleaned_actions = []
            for action in suggested_actions:
                if not isinstance(action, dict):
                    continue
                # Clean title (max 3 words)
                title = _clean_text(action.get("title", ""), 40)
                subtitle = _clean_text(action.get("subtitle", ""), 120)
                
                if title and subtitle:
                    cleaned_actions.append({
                        "title": title,
                        "subtitle": subtitle
                    })
            
            # Ensure at least 1 action
            if not cleaned_actions:
                cleaned_actions = [{
                    "title": "Track Pattern",
                    "subtitle": "Write down what triggered this pattern today."
                }]
            
            return {
                "ai_insight": ai_insight,
                "behavioral_pattern": behavioral_pattern,
                "suggested_actions": cleaned_actions,
                "motivation_line": motivation_line
            }
        
        except Exception as e:
            error_msg = str(e)
            logger.warning("Gemini API call failed (attempt %d/%d): %s", attempt, MAX_RETRIES, error_msg)
            
            # If this is last retry,return None to trigger fallback
            if attempt >= MAX_RETRIES:
                logger.error("Gemini API failed after %d retries, using fallback", MAX_RETRIES)
                return None
            
            # Check if it's a retryable error (503)
            if "503" in error_msg or "temporarily unavailable" in error_msg.lower():
                continue  # Retry
            else:
                # Non-retryable error
                return None


def _build_ai_context(uid: str, db, insight: dict) -> dict:
    """Build context for AI prompt."""
    try:
        from services import stats_service
        
        # Get mood summary
        trends_response, _ = stats_service.get_mood_trends(uid, 7, db)
        trends = trends_response.get("trends", [])
        
        mood_counts = {}
        for entry in trends:
            mood = entry.get("mood", "neutral")
            mood_counts[mood] = mood_counts.get(mood, 0) + 1
        
        top_moods = sorted(mood_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return {
            "top_emotions": [m[0] for m in top_moods],
            "journaling_consistency": len(trends),
            "insight_fields": {
                "negative_behaviors": insight.get("negative_behaviors", [])[:2],
                "conflicts": insight.get("conflicts", [])[:2],
                "appreciation": insight.get("appreciation", "")[:100],
                "goals": len(insight.get("goals", []))
            }
        }
    except Exception as e:
        logger.warning("Failed to build AI context: %s", str(e))
        return {}


def _store_cache(uid: str, db, ai_result: dict, insight: dict):
    """Store AI-generated cache to Firestore. SKIP if data is broken."""
    try:
        # DO NOT store if data is incomplete
        if not ai_result:
            logger.warning("Skipping cache storage: ai_result is empty")
            return
        
        if not ai_result.get("ai_insight") or not ai_result.get("behavioral_pattern"):
            logger.warning("Skipping cache storage: missing required fields")
            return
        
        # Check for duplicates
        if ai_result["ai_insight"].strip() == ai_result["behavioral_pattern"].strip():
            logger.warning("Skipping cache storage: ai_insight == behavioral_pattern (duplicate)")
            return
        
        now = datetime.now(TZ)
        valid_till = now + timedelta(hours=24)
        
        cache_data = {
            "generated_at": now.isoformat(),
            "valid_till": valid_till.isoformat(),
            "ai_insight": ai_result.get("ai_insight", ""),
            "behavioral_pattern": ai_result.get("behavioral_pattern", ""),
            "suggested_actions": ai_result.get("suggested_actions", []),
            "motivation_line": ai_result.get("motivation_line", ""),
            "period": "7d",
            "last_insight_id": insight.get("insight_id", "")
        }
        
        db.db.collection("dashboard_cache").document(uid).set(cache_data, merge=True)
        logger.info("Cache stored for uid=%s", uid)
    except Exception as e:
        logger.exception("Failed to store cache: %s", str(e))


def _store_cache_fallback(uid: str, db, insight: dict = None):
    """Store clean fallback cache if AI fails."""
    try:
        now = datetime.now(TZ)
        valid_till = now + timedelta(hours=24)
        
        # Generate clean fallback fields
        ai_insight = fallback_ai_insight(insight) if insight else "You're taking time to reflect on your journey."
        behavioral_pattern = fallback_behavioral_pattern(insight) if insight else "Keep exploring your thoughts through journaling."
        motivation_line = _clean_text("Write what's on your mind.", 120)
        
        # Ensure they're different
        if ai_insight.strip() == behavioral_pattern.strip():
            behavioral_pattern = "Keep exploring your thoughts through journaling."
        
        cache_data = {
            "generated_at": now.isoformat(),
            "valid_till": valid_till.isoformat(),
            "ai_insight": ai_insight,
            "behavioral_pattern": behavioral_pattern,
            "suggested_actions": [{
                "title": "Reflect",
                "subtitle": "Take time to journal about what's happening."
            }],
            "motivation_line": motivation_line,
            "period": "7d"
        }
        
        db.db.collection("dashboard_cache").document(uid).set(cache_data, merge=True)
        logger.info("Fallback cache stored for uid=%s", uid)
    except Exception as e:
        logger.exception("Failed to store fallback cache: %s", str(e))


def generate_ai_cache_for_all_users(db, limit: int = 500):
    """
    Batch process AI cache generation for all eligible users.
    
    Args:
        db: Database instance
        limit: Max number of users to process (default 500)
    
    Returns:
        dict: {processed: int, failed: int, skipped: int}
    """
    try:
        stats = {"processed": 0, "failed": 0, "skipped": 0}
        
        # Fetch users in batches
        users_query = db.db.collection("users").limit(limit)
        
        logger.info("Starting AI cache generation for all users (limit=%d)", limit)
        
        for user_doc in users_query.stream():
            try:
                uid = user_doc.id
                logger.info("Processing user %s", uid)
                
                # Generate cache for this user
                generate_ai_cache_for_user(uid, db)
                stats["processed"] += 1
            
            except Exception as e:
                logger.warning("Failed to generate cache for user %s: %s", uid, str(e))
                stats["failed"] += 1
                # Continue with next user (no blocking failures)
        
        logger.info("AI cache generation completed: processed=%d failed=%d", 
                    stats["processed"], stats["failed"])
        
        return stats
    
    except Exception as e:
        logger.exception("Fatal error in batch AI cache generation: %s", str(e))
        raise





