"""
Production Dashboard Service - Critical Fixes Implemented

- Natural language synthesis (no pipes)
- Real data only (no fabrication)
- Activity merging: journals + media
- Correct field names: timestamp, item_id
- All 7 moods normalized
- AI cache read-only
- Empty arrays for fallbacks
"""

import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import pytz
from firebase_admin import firestore

logger = logging.getLogger()
TZ = pytz.timezone("Asia/Kolkata")

VALID_MOODS = ["anger", "disgust", "fear", "happy", "neutral", "sad", "surprise"]


def _normalize_timestamp(ts) -> str:
    """Convert to ISO 8601."""
    if ts is None:
        ts = datetime.now(TZ)
    elif isinstance(ts, str):
        try:
            if "T" in ts and "Z" in ts:
                return ts
            elif "T" in ts:
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            else:
                ts = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                ts = TZ.localize(ts)
        except Exception:
            ts = datetime.now(TZ)
    elif isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = TZ.localize(ts)
    else:
        ts = datetime.now(TZ)
    
    if ts.tzinfo is None:
        ts = TZ.localize(ts)
    ts_utc = ts.astimezone(pytz.UTC)
    return ts_utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def _clean_text(text: str, max_len: int = 160) -> str:
    """Remove quotes, trim cleanly at sentence boundaries."""
    if not text:
        return ""
    
    text = str(text).strip()
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        text = text[1:-1].strip()
    
    text = text.replace("\\\"", '"').replace("\\'", "'").replace("\\\\", "\\")
    
    # Only trim if exceeds max_len
    if len(text) > max_len:
        # Check if already ends with "..."
        if text.endswith("..."):
            return text
        
        # Trim to max_len and find last sentence boundary
        truncated = text[:max_len]
        
        # Try to find last period
        last_period = truncated.rfind(".")
        if last_period > max_len // 2:
            text = truncated[:last_period + 1]
        else:
            # No good period, try space
            last_space = truncated.rfind(" ")
            if last_space > max_len // 2:
                text = truncated[:last_space]
            else:
                text = truncated
        
        # Only add "..." if not already ending with period
        if not text.endswith("."):
            text = text.rstrip(",.;:") + "..."
    
    return text


def _synthesize_behavioral_pattern(insight: dict) -> str:
    """Synthesize natural language (2-3 lines), NO pipes."""
    if not insight:
        return "Continue exploring your thoughts through journaling."
    
    behavior = insight.get("negative_behaviors", [])
    behavior = str(behavior[0]).strip() if behavior and isinstance(behavior, list) else ""
    
    conflict = insight.get("conflicts", [])
    conflict = str(conflict[0]).strip() if conflict and isinstance(conflict, list) else ""
    
    strength = str(insight.get("appreciation", "")).strip()
    
    if behavior and conflict and strength:
        return f"You tend to struggle with {_clean_text(behavior, 40)} when facing {_clean_text(conflict, 40)}. Yet you show strength by {_clean_text(strength, 50)}."
    elif behavior and strength:
        return f"You recognize that {_clean_text(behavior, 50)} can be challenging. However, you're building strength by {_clean_text(strength, 60)}."
    elif conflict and strength:
        return f"When {_clean_text(conflict, 50)} arises, you respond by {_clean_text(strength, 60)}."
    elif strength:
        return _clean_text(strength, 160)
    elif behavior:
        return f"Noticing {_clean_text(behavior, 60)} is the first step toward growth."
    else:
        return "Keep exploring your thoughts through journaling."


def _get_greeting(user_name: str = None) -> str:
    """Personalized greeting."""
    hour = datetime.now(TZ).hour
    greeting = "Good morning" if 5 <= hour < 12 else "Good afternoon" if 12 <= hour < 17 else "Good evening"
    return f"{greeting}, {user_name}" if user_name else greeting


def _fetch_user(uid: str, db):
    try:
        doc = db.db.collection("users").document(uid).get()
        return doc.to_dict() if doc.exists else {}
    except Exception as e:
        logger.warning("Fetch user error: %s", str(e))
        return {}


def _fetch_stats(uid: str, db):
    try:
        from services import stats_service
        stats_data, _ = stats_service.get_user_stats(uid, db)
        return {"total_entries": stats_data.get("total_entries", 0)}
    except Exception as e:
        logger.warning("Fetch stats error: %s", str(e))
        return {"total_entries": 0}


def _fetch_streaks(uid: str, db):
    try:
        from services.analytics import calculate_streak
        streak_data, _ = calculate_streak(uid, db)
        return {
            "current_streak": streak_data.get("current_streak", 0),
            "longest_streak": streak_data.get("longest_streak", 0)
        }
    except Exception as e:
        logger.warning("Fetch streaks error: %s", str(e))
        return {"current_streak": 0, "longest_streak": 0}


def _fetch_words_written(uid: str, db):
    try:
        entries_query = db.db.collection("journal_entries").where(
            filter=firestore.FieldFilter("uid", "==", uid)
        )
        total_words = 0
        for entry_doc in entries_query.stream():
            text = entry_doc.to_dict().get("entry_text", "")
            if text:
                total_words += len(text.split())
        return total_words
    except Exception as e:
        logger.warning("Fetch words error: %s", str(e))
        return 0


def _fetch_mood_trends(uid: str, db, days: int = 7):
    try:
        from services import stats_service
        trends_response, _ = stats_service.get_mood_trends(uid, days, db)
        return trends_response.get("trends", [])
    except Exception as e:
        logger.warning("Fetch trends error: %s", str(e))
        return []


def _fetch_latest_insight(uid: str, db):
    try:
        from services import insights_service
        insights_response, _ = insights_service.get_insights(uid, limit=1, offset=0, db=db)
        
        if "insights" in insights_response and insights_response["insights"]:
            insight = insights_response["insights"][0]
            return {
                "id": insight.get("insight_id", ""),
                "appreciation": insight.get("appreciation", ""),
                "goals": insight.get("goals", []),
                "negative_behaviors": insight.get("negative_behaviors", []),
                "conflicts": insight.get("conflicts", []),
                "created_at": insight.get("created_at")
            }
        return None
    except Exception as e:
        logger.warning("Fetch insight error: %s", str(e))
        return None


def _fetch_period_entries(uid: str, db, days: int = 7) -> list:
    try:
        today = datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
        start = today - timedelta(days=days - 1)
        
        entries_query = db.db.collection("journal_entries").where(
            filter=firestore.FieldFilter("uid", "==", uid)
        ).where(
            filter=firestore.FieldFilter("created_at", ">=", start)
        ).where(
            filter=firestore.FieldFilter("created_at", "<=", today)
        )
        
        return [doc.to_dict() for doc in entries_query.stream()]
    except Exception as e:
        logger.warning("Fetch period entries error: %s", str(e))
        return []


def _fetch_dashboard_cache(uid: str, db):
    """Fetch AI cache (READ-ONLY)."""
    try:
        cache_doc = db.db.collection("dashboard_cache").document(uid).get()
        if cache_doc.exists:
            cache_data = cache_doc.to_dict()
            valid_till = cache_data.get("valid_till")
            if valid_till:
                try:
                    valid_time = datetime.fromisoformat(valid_till.replace("Z", "+00:00")) if isinstance(valid_till, str) else valid_till
                    if datetime.now(TZ) < valid_time:
                        return cache_data
                except Exception:
                    pass
        return None
    except Exception as e:
        logger.warning("Fetch cache error: %s", str(e))
        return None


def aggregate_mood_distribution(trends: list) -> list:
    """All 7 moods, fill missing with 0."""
    if not trends:
        return []
    
    mood_by_date = {}
    for entry in trends:
        if isinstance(entry, dict):
            date, mood, confidence = entry.get("date"), entry.get("mood"), entry.get("confidence", 1.0)
            if date and mood:
                if date not in mood_by_date:
                    mood_by_date[date] = {}
                mood_by_date[date][mood] = max(mood_by_date[date].get(mood, 0), confidence)
    
    result = []
    for date in sorted(mood_by_date.keys()):
        normalized = {mood: 0.0 for mood in VALID_MOODS}
        normalized.update(mood_by_date[date])
        result.append({"date": date, "moods": normalized})
    
    return result


def aggregate_mood_trend(trends: list) -> list:
    """One dominant mood per date."""
    if not trends:
        return []
    
    mood_by_date = {}
    for entry in trends:
        if isinstance(entry, dict):
            date, mood, confidence = entry.get("date"), entry.get("mood"), entry.get("confidence", 0)
            if date and mood:
                if date not in mood_by_date or confidence > mood_by_date[date][1]:
                    mood_by_date[date] = (mood, confidence)
    
    return [{"date": date, "mood": mood_by_date[date][0]} for date in sorted(mood_by_date.keys())]


def get_top_mood(trends: list) -> str:
    """Most frequent mood."""
    if not trends:
        return "neutral"
    mood_counts = {}
    for entry in trends:
        if isinstance(entry, dict):
            mood = entry.get("mood", "neutral")
            mood_counts[mood] = mood_counts.get(mood, 0) + 1
    return max(mood_counts, key=mood_counts.get) if mood_counts else "neutral"


def extract_goals(insight: dict) -> list:
    """STRICT: from insight.goals[] only."""
    if not insight:
        return []
    
    insight_goals = insight.get("goals", [])
    return [
        {
            "title": goal.get("title", ""),
            "status": goal.get("status", ""),
            "description": goal.get("description", ""),
            "evidence": goal.get("evidence", ""),
            "next_step": goal.get("next_step", "")
        }
        for goal in (insight_goals if isinstance(insight_goals, list) else [])
    ]


def compute_goal_progress(goal: dict, period_entries: list, period_days: int) -> dict:
    """Fixed: completed_days = min(actual, period)."""
    status = goal.get("status", "").lower()
    actual_entries = len(period_entries)
    completed = min(actual_entries, period_days)
    
    if "struggling" in status or status == "stuck":
        progress = int(20 + (completed / max(period_days, 1)) * 30)
    elif "improving" in status or status == "progressing":
        progress = int(50 + (completed / max(period_days, 1)) * 25)
    elif "achieved" in status or status == "complete":
        progress = 100
    else:
        progress = int((completed / max(period_days, 1)) * 100)
    
    return {
        "title": goal.get("title", ""),
        "progress": int(min(100, max(0, progress))),
        "completed_days": completed,
        "total_days": period_days
    }


def _enrich_media_title(item_id: str, media_type: str, db) -> str:
    """Enrich media title from cache collection."""
    try:
        media_type_lower = media_type.lower()
        
        # Map to collection name
        collection_map = {
            "songs": "media_cache_songs",
            "movies": "media_cache_movies",
            "books": "media_cache_books",
            "podcasts": "media_cache_podcasts"
        }
        
        collection_name = collection_map.get(media_type_lower)
        if not collection_name:
            return "Unknown"
        
        # Query cache
        cache_doc = db.db.collection(collection_name).document(item_id).get()
        if cache_doc.exists:
            data = cache_doc.to_dict()
            return data.get("title") or data.get("name") or "Unknown"
        
        return "Unknown"
    except Exception as e:
        logger.debug("Media enrichment failed for %s/%s: %s", media_type, item_id, str(e))
        return "Unknown"


def fetch_recent_activity(uid: str, db, limit: int = 10) -> tuple:
    """Merged: max 5 journals + 5 media, enforced diversity."""
    journals, media = [], []
    seen_ids = set()  # Deduplication
    
    try:
        from services import journal_entries
        params = {"limit": 5, "offset": 0}
        entries_response, _ = journal_entries.get_entries_filtered(uid, params, db)
        
        if entries_response and "entries" in entries_response:
            for entry in entries_response.get("entries", [])[:5]:
                entry_id = entry.get("entry_id", "")
                if entry_id and ("journal", entry_id) not in seen_ids:
                    journals.append({
                        "id": entry_id,
                        "type": "journal",
                        "title": entry.get("title", "Untitled"),
                        "created_at": entry.get("created_at")
                    })
                    seen_ids.add(("journal", entry_id))
    except Exception as e:
        logger.warning("Fetch journals error: %s", str(e))
    
    try:
        events_collection = db.db.collection("user_interactions").document(uid).collection("events")
        events_query = events_collection.order_by(
            "timestamp", direction=firestore.Query.DESCENDING
        ).limit(10)  # Get more to find 5 valid media
        
        valid_types = {"songs", "movies", "books", "podcasts"}
        type_output_map = {"songs": "song", "movies": "movie", "books": "book", "podcasts": "podcast"}
        
        for doc in events_query.stream():
            if len(media) >= 5:
                break
            
            data = doc.to_dict()
            signal = data.get("signal", "").lower()
            media_type = data.get("media_type", "").lower()
            
            # Validate signal and type
            if signal not in ["click", "save"]:
                continue
            if media_type not in valid_types:
                continue
            
            item_id = data.get("item_id", "")
            if not item_id:
                continue
            
            # Deduplication
            if (media_type, item_id) in seen_ids:
                continue
            
            # Enrich title from cache
            title = _enrich_media_title(item_id, media_type, db)
            
            media.append({
                "id": item_id,
                "type": type_output_map.get(media_type, "song"),
                "title": title,
                "created_at": _normalize_timestamp(data.get("timestamp"))
            })
            seen_ids.add((media_type, item_id))
    except Exception as e:
        logger.warning("Fetch media error: %s", str(e))
    
    # Enforce diversity: at least 2 media + 2 journals in top 6 for home
    all_items = journals + media
    
    def get_ts(item):
        try:
            ts = item.get("created_at")
            return datetime.fromisoformat(ts.replace("Z", "+00:00")) if isinstance(ts, str) else ts
        except Exception:
            return datetime.min
    
    sorted_items = sorted(all_items, key=get_ts, reverse=True)
    
    # If requesting top 6 (home screen), ensure mix
    if limit == 6 and len(sorted_items) > 2:
        result = []
        journal_count = 0
        media_count = 0
        
        for item in sorted_items:
            if item["type"] == "journal":
                if journal_count < 4:  # Max 4 journals
                    result.append(item)
                    journal_count += 1
            else:
                if media_count < 4:  # Max 4 media
                    result.append(item)
                    media_count += 1
            
            if len(result) >= 6:
                break
    else:
        result = sorted_items[:limit]
    
    # Ensure all timestamps normalized
    for item in result:
        item["created_at"] = _normalize_timestamp(item.get("created_at"))
    
    return result, 200


def get_dashboard(uid: str, db):
    """Home screen."""
    try:
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {
                "user": executor.submit(_fetch_user, uid, db),
                "stats": executor.submit(_fetch_stats, uid, db),
                "streaks": executor.submit(_fetch_streaks, uid, db),
                "words": executor.submit(_fetch_words_written, uid, db),
                "insight": executor.submit(_fetch_latest_insight, uid, db),
                "cache": executor.submit(_fetch_dashboard_cache, uid, db),
                "activity": executor.submit(fetch_recent_activity, uid, db, 6),
                "trends": executor.submit(_fetch_mood_trends, uid, db, 7),
            }
            
            results = {key: future.result(timeout=10) if future else None for key, future in futures.items()}
        
        user_data = results.get("user") or {}
        stats = results.get("stats") or {}
        streaks = results.get("streaks") or {}
        insight = results.get("insight")
        cache = results.get("cache")
        activity = results.get("activity")[0] if isinstance(results.get("activity"), tuple) else []
        trends = results.get("trends") or []
        
        greeting = _get_greeting(user_data.get("name"))
        
        insight_preview = None
        if insight and insight.get("appreciation"):
            insight_preview = {
                "id": insight.get("id", ""),
                "created_at": _normalize_timestamp(insight.get("created_at")),
                "summary": _clean_text(insight["appreciation"], max_len=160)
            }
        
        # Smart motivation line (not generic)
        if cache and cache.get("motivation_line"):
            motivation_line = cache.get("motivation_line")
        else:
            # Fallback based on user context
            entries_count = stats.get("total_entries", 0)
            streak = streaks.get("current_streak", 0)
            
            if streak >= 7:
                motivation_line = "Your consistency is powerful. Keep it going."
            elif entries_count >= 10:
                motivation_line = "You're building meaningful records of your life."
            else:
                motivation_line = "Every entry matters. Write what you feel."
        mood_dist = aggregate_mood_distribution(trends)
        latest_mood = mood_dist[-1]["moods"] if mood_dist else {m: 0.0 for m in VALID_MOODS}
        
        response = {
            "greeting": greeting,
            "summary": {
                "current_streak": streaks.get("current_streak", 0),
                "longest_streak": streaks.get("longest_streak", 0),
                "total_entries": stats.get("total_entries", 0),
                "words_written": results.get("words", 0) or 0
            },
            "motivation_line": motivation_line,
            "quick_activity": activity,
            "mood_snapshot": latest_mood
        }
        
        if insight_preview:
            response["insight_preview"] = insight_preview
        
        logger.info("Dashboard generated for uid=%s", uid)
        return response, 200
    
    except Exception as e:
        logger.exception("Dashboard error: %s", str(e))
        return {"error": str(e)}, 500


def get_journey(uid: str, db, period: str = "7d"):
    """Journey screen."""
    try:
        period_days = 30 if period == "30d" else 7
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                "trends": executor.submit(_fetch_mood_trends, uid, db, period_days),
                "insight": executor.submit(_fetch_latest_insight, uid, db),
                "period_entries": executor.submit(_fetch_period_entries, uid, db, period_days),
                "cache": executor.submit(_fetch_dashboard_cache, uid, db),
            }
            
            results = {key: future.result(timeout=10) if future else None for key, future in futures.items()}
        
        trend_data = results.get("trends") or []
        insight = results.get("insight")
        period_entries = results.get("period_entries") or []
        cache = results.get("cache")
        
        goals = extract_goals(insight)
        goal_progress = [compute_goal_progress(goal, period_entries, period_days) for goal in goals]
         
        # Use AI-generated values from cache, with fallbacks
        behavioral_pattern = ""
        if cache and cache.get("behavioral_pattern"):
            behavioral_pattern = cache.get("behavioral_pattern")
        else:
            behavioral_pattern = _synthesize_behavioral_pattern(insight) if insight else "Keep exploring your thoughts."
         
        suggested_actions = cache.get("suggested_actions", []) if cache else []

        # Generate ai_insight: prefer cache, fallback to appreciation, then default
        ai_insight = ""
        if cache and cache.get("ai_insight"):
            ai_insight = cache.get("ai_insight")
        elif insight and insight.get("appreciation"):
            ai_insight = _clean_ai_insight(str(insight.get("appreciation", "")), max_len=120)
        else:
            ai_insight = "Keep reflecting—your patterns are becoming clearer."
        
        mood_distribution = aggregate_mood_distribution(trend_data)
        mood_trend = aggregate_mood_trend(trend_data)
        top_mood = get_top_mood(trend_data)
        
        response = {
            "period": f"{period_days}d",
            "ai_insight": ai_insight,
            "stats": {
                "top_mood": top_mood,
                "entries": len(period_entries),
                "streak": len(mood_trend)
            },
            "goal_progress": goal_progress,
            "behavioral_pattern": behavioral_pattern,
            "suggested_actions": suggested_actions,
            "mood_trend": mood_trend,
            "mood_distribution": mood_distribution
        }
        
        logger.info("Journey generated for uid=%s (%s)", uid, f"{period_days}d")
        return response, 200
    
    except Exception as e:
        logger.exception("Journey error: %s", str(e))
        return {"error": str(e)}, 500


def get_activity(uid: str, db, limit: int = 10):
    """Recent activity."""
    try:
        activity, status = fetch_recent_activity(uid, db, limit)
        logger.info("Activity generated for uid=%s (items=%d)", uid, len(activity))
        return activity, status
    except Exception as e:
        logger.exception("Activity error: %s", str(e))
        return {"error": str(e)}, 500

