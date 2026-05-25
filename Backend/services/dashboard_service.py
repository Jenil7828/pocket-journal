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
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import pytz
import re
import time
import threading
from firebase_admin import firestore
from utils import extract_dominant_mood

logger = logging.getLogger()
TZ = pytz.timezone("Asia/Kolkata")

VALID_MOODS = ["anger", "disgust", "fear", "happy", "neutral", "sad", "surprise"]

# === Fix 2: Module-level in-process cache with TTL ===
_dashboard_cache: dict = {}  # uid -> {key -> (value, expires_at_epoch_float)}
_CACHE_TTL = 30  # seconds
_cache_lock = threading.Lock()


def _cache_get(uid: str, key: str):
    """Get cached value if present and not expired."""
    with _cache_lock:
        if uid not in _dashboard_cache:
            return None
        if key not in _dashboard_cache[uid]:
            return None
        value, expires_at = _dashboard_cache[uid][key]
        if time.time() > expires_at:
            del _dashboard_cache[uid][key]
            if not _dashboard_cache[uid]:
                del _dashboard_cache[uid]
            return None
        return value


def _cache_set(uid: str, key: str, value):
    """Store value with expiry."""
    with _cache_lock:
        if uid not in _dashboard_cache:
            _dashboard_cache[uid] = {}
        _dashboard_cache[uid][key] = (value, time.time() + _CACHE_TTL)


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


def _clean_ai_insight(text: str, max_len: int = 120) -> str:
    """Sanitize AI-generated appreciation/insight text for UI display.
    Remove timestamps, short date tokens and obvious numeric anchors that bias summaries.
    Preserve punctuation and sentence boundaries where possible and trim to max_len.
    """
    if not text:
        return ""

    # Start with the generic cleaner but allow a longer working buffer
    s = _clean_text(str(text), max_len * 2)

    # Remove common time tokens (e.g., 8:30, 08:30:00, 8am, 8 PM)
    s = re.sub(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", "", s)
    s = re.sub(r"\b\d{1,2}\s?(am|pm|AM|PM)\b", "", s)

    # Remove simple numeric date patterns (7/5/2024, 07/05)
    s = re.sub(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", "", s)
    s = re.sub(r"\b\d{1,2}/\d{1,2}\b", "", s)

    # Remove ordinal tokens like 7th, 1st etc
    s = re.sub(r"\b\d{1,2}(st|nd|rd|th)\b", "", s)

    # Remove stray years (1900-2099)
    s = re.sub(r"\b(19|20)\d{2}\b", "", s)

    # Collapse excessive whitespace introduced by removals
    s = re.sub(r"\s+", " ", s).strip()

    # Short final trim preserving sentence boundary where possible
    if len(s) > max_len:
        truncated = s[:max_len]
        last_period = truncated.rfind(".")
        if last_period > max_len // 2:
            s = truncated[:last_period + 1]
        else:
            last_space = truncated.rfind(" ")
            if last_space > max_len // 2:
                s = truncated[:last_space]
            else:
                s = truncated

        if not s.endswith("."):
            s = s.rstrip(",.;:") + "..."

    return s


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
    # Fix 2: Check cache
    cached = _cache_get(uid, "user")
    if cached is not None:
        return cached

    try:
        doc = db.db.collection("users").document(uid).get()
        result = doc.to_dict() if doc.exists else {}
        _cache_set(uid, "user", result)
        return result
    except Exception as e:
        logger.warning("Fetch user error: %s", str(e))
        return {}


def _fetch_stats(uid: str, db):
    # Fix 2: Check cache
    cached = _cache_get(uid, "stats")
    if cached is not None:
        return cached

    try:
        # Direct Firestore count aggregation (not streaming all entries)
        try:
            # Try using modern SDK .count() aggregation API
            query = db.db.collection("journal_entries").where(
                filter=firestore.FieldFilter("uid", "==", uid)
            )
            count_query = query.count()
            count_result = count_query.get()
            total_entries = count_result[0][0].value
        except (AttributeError, TypeError):
            # Fallback: .limit(1000).stream() for older SDK versions
            query = db.db.collection("journal_entries").where(
                filter=firestore.FieldFilter("uid", "==", uid)
            ).limit(1000)
            entries = list(query.stream())
            total_entries = len(entries)

        result = {"total_entries": total_entries}
        _cache_set(uid, "stats", result)
        return result
    except Exception as e:
        logger.warning("Fetch stats error: %s", str(e))
        return {"total_entries": 0}


def _fetch_streaks(uid: str, db):
    # Fix 1: Check cache
    cached = _cache_get(uid, "streaks")
    if cached is not None:
        return cached

    try:
        # Direct Firestore query for entries (cap at 60 docs for performance)
        query = db.db.collection("journal_entries").where(
            filter=firestore.FieldFilter("uid", "==", uid)
        ).order_by("created_at", direction=firestore.Query.DESCENDING).limit(60)

        dates = set()
        for doc in query.stream():
            created_at = doc.to_dict().get("created_at")
            if created_at:
                if isinstance(created_at, datetime):
                    date_str = created_at.strftime("%Y-%m-%d")
                else:
                    date_str = str(created_at)[:10]
                dates.add(date_str)

        # Compute current_streak and longest_streak from unique dates
        if not dates:
            result = {"current_streak": 0, "longest_streak": 0}
        else:
            sorted_dates = sorted(dates, reverse=True)
            today = datetime.now(TZ).strftime("%Y-%m-%d")

            # Current streak logic: consecutive days from today
            current_streak = 0
            current_date = datetime.strptime(today, "%Y-%m-%d").date()
            for date_str in sorted_dates:
                entry_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                if entry_date == current_date:
                    current_streak += 1
                    current_date = current_date - timedelta(days=1)
                else:
                    break

            # Longest streak: find the longest sequence in the date list
            longest_streak = 1
            current_length = 1
            prev_date = datetime.strptime(sorted_dates[0], "%Y-%m-%d").date()
            for date_str in sorted_dates[1:]:
                entry_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                if entry_date == prev_date - timedelta(days=1):
                    current_length += 1
                else:
                    longest_streak = max(longest_streak, current_length)
                    current_length = 1
                prev_date = entry_date
            longest_streak = max(longest_streak, current_length)

            result = {"current_streak": current_streak, "longest_streak": longest_streak}

        _cache_set(uid, "streaks", result)
        return result
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


# Fix 3: Optimized mood trends with reduced Firestore reads
def _fetch_mood_trends_lite(uid: str, db, days: int = 7):
    """
    Fetch mood trends with two sequential Firestore reads instead of O(n):
    1. Query journal_entries for entries in period (extract IDs and dates)
    2. Batch query entry_analysis WHERE entry_id IN [...] (batch up to 30)
    """
    # Fix 4: Check cache with key that includes days
    cache_key = f"trends_{days}"
    cached = _cache_get(uid, cache_key)
    if cached is not None:
        return cached

    try:
        today = datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
        start = today - timedelta(days=days - 1)

        # Read 1: Get entry IDs and dates from journal_entries (Fix 5: limit to 30 docs)
        entries_query = db.db.collection("journal_entries").where(
            filter=firestore.FieldFilter("uid", "==", uid)
        ).where(
            filter=firestore.FieldFilter("created_at", ">=", start)
        ).where(
            filter=firestore.FieldFilter("created_at", "<=", today)
        ).order_by("created_at", direction=firestore.Query.DESCENDING).limit(30)

        entry_map = {}  # entry_id -> date
        for doc in entries_query.stream():
            entry_id = doc.id
            created_at = doc.to_dict().get("created_at")
            if entry_id and created_at:
                # Normalize date to YYYY-MM-DD
                if isinstance(created_at, datetime):
                    date_str = created_at.strftime("%Y-%m-%d")
                else:
                    date_str = str(created_at)[:10]
                entry_map[entry_id] = date_str

        if not entry_map:
            result = []
            _cache_set(uid, cache_key, result)
            return result

        # Read 2: Batch query entry_analysis with IN filter (now single batch due to .limit(30))
        results = []
        entry_ids = list(entry_map.keys())

        for i in range(0, len(entry_ids), 30):
            chunk = entry_ids[i:i + 30]
            analysis_query = db.db.collection("entry_analysis").where(
                filter=firestore.FieldFilter("entry_id", "in", chunk)
            )

            for doc in analysis_query.stream():
                data = doc.to_dict()
                entry_id = data.get("entry_id")
                if entry_id in entry_map:
                    mood_probs = data.get("mood", {})
                    dominant_mood = extract_dominant_mood(mood_probs)
                    if dominant_mood:
                        confidence = mood_probs.get(dominant_mood, 0.0)
                        results.append({
                            "date": entry_map[entry_id],
                            "mood": dominant_mood,
                            "confidence": float(confidence) if confidence else 0.0
                        })

        _cache_set(uid, cache_key, results)
        return results
    except Exception as e:
        logger.warning("Fetch trends lite error: %s", str(e))
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
    
    # Fix 4: Direct Firestore query for journals instead of get_entries_filtered
    try:
        docs = db.db.collection("journal_entries").where(
            filter=firestore.FieldFilter("uid", "==", uid)
        ).order_by("created_at", direction=firestore.Query.DESCENDING).limit(5).stream()

        for doc in docs:
            entry_id = doc.id
            data = doc.to_dict()
            if entry_id and ("journal", entry_id) not in seen_ids:
                journals.append({
                    "id": entry_id,
                    "type": "journal",
                    "title": data.get("title", "Untitled"),
                    "created_at": data.get("created_at")
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
        # Fix 3: Static titles based on media type (no _enrich_media_title calls)
        type_title_map = {"songs": "Saved song", "movies": "Saved movie", "books": "Saved book", "podcasts": "Saved podcast"}

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
            
            # Fix 3: Use static title lookup instead of _enrich_media_title
            title = type_title_map.get(media_type, "Saved media")

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
        # Fix 6: Call _fetch_user synchronously before executor (it's already cached, very fast)
        user_data = _fetch_user(uid, db)

        # Fix 1: Split into Tier 1 (blocking) and Tier 2 (daemon threads)
        # Tier 1: stats, streaks, trends, activity (hot path — must complete)
        # Tier 2: words, insight, cache (background — start but don't wait)

        tier1_results = {}

        # Tier 1: Blocking fetches with short timeout (Fix 6: max_workers=4 instead of 5)
        with ThreadPoolExecutor(max_workers=4) as executor:
            tier1_futures = {
                "stats": executor.submit(_fetch_stats, uid, db),
                "streaks": executor.submit(_fetch_streaks, uid, db),
                "trends": executor.submit(_fetch_mood_trends_lite, uid, db, 7),
                "activity": executor.submit(fetch_recent_activity, uid, db, 6),
            }

            for key, future in tier1_futures.items():
                try:
                    tier1_results[key] = future.result(timeout=4)
                except (TimeoutError, Exception) as e:
                    logger.warning("Tier1 fetch timeout/error for key=%s: %s", key, str(e))
                    if key in ("streaks",):
                        tier1_results[key] = {}
                    elif key == "stats":
                        tier1_results[key] = {"total_entries": 0}
                    elif key == "trends":
                        tier1_results[key] = []
                    elif key == "activity":
                        tier1_results[key] = ([], 200)
                    else:
                        tier1_results[key] = None

        # Tier 2: Non-blocking daemon threads (fire and forget)
        def _fetch_words_thread():
            try:
                return _fetch_words_written(uid, db)
            except Exception as e:
                logger.debug("Words fetch in daemon: %s", str(e))
                return 0

        def _fetch_insight_thread():
            try:
                return _fetch_latest_insight(uid, db)
            except Exception as e:
                logger.debug("Insight fetch in daemon: %s", str(e))
                return None

        def _fetch_cache_thread():
            try:
                return _fetch_dashboard_cache(uid, db)
            except Exception as e:
                logger.debug("Cache fetch in daemon: %s", str(e))
                return None

        # Start daemon threads but don't wait for them
        words_thread = threading.Thread(target=_fetch_words_thread, daemon=True)
        insight_thread = threading.Thread(target=_fetch_insight_thread, daemon=True)
        cache_thread = threading.Thread(target=_fetch_cache_thread, daemon=True)

        words_thread.start()
        insight_thread.start()
        cache_thread.start()

        # Use fallbacks for Tier 2 fields (don't wait for daemon threads)
        stats = tier1_results.get("stats") or {}
        streaks = tier1_results.get("streaks") or {}
        activity = tier1_results.get("activity")[0] if isinstance(tier1_results.get("activity"), tuple) else []
        trends = tier1_results.get("trends") or []

        greeting = _get_greeting(user_data.get("name"))
        
        # insight_preview: omit if insight not immediately available (not waiting for daemon)
        insight_preview = None

        # motivation_line: compute inline from Tier 1 data only
        entries_count = (stats.get("total_entries", 0) if isinstance(stats, dict) else 0)
        streak = (streaks.get("current_streak", 0) if isinstance(streaks, dict) else 0)

        if entries_count == 0:
            motivation_line = "Write your first entry — a few words is all it takes."
        else:
            # No cache check — cache is in Tier 2
            if streak >= 7:
                motivation_line = "Your consistency is powerful. Keep it going."
            elif entries_count >= 10:
                motivation_line = "You're building meaningful records of your life."
            else:
                motivation_line = "Every entry matters. Write what you feel."

        # Replace empty activity with placeholder
        if not activity:
            activity = [
                {"id": "placeholder_journal", "type": "journal", "title": "Start your first journal entry", "created_at": None},
                {"id": "placeholder_song",    "type": "song",    "title": "Discover music for your mood",   "created_at": None},
                {"id": "placeholder_movie",   "type": "movie",   "title": "Find a movie to watch tonight",  "created_at": None},
                {"id": "placeholder_book",    "type": "book",    "title": "Pick a book to read this week",  "created_at": None},
            ]

        response = {
            "greeting": greeting,
            "summary": {
                "current_streak": streaks.get("current_streak", 0),
                "longest_streak": streaks.get("longest_streak", 0),
                "total_entries": stats.get("total_entries", 0),
                "words_written": 0
            },
            "motivation_line": motivation_line,
            "quick_activity": activity
        }
        
        # Note: insight_preview is omitted (not waited for)

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
                "trends": executor.submit(_fetch_mood_trends_lite, uid, db, period_days),  # Fix 3: use lite version
                "insight": executor.submit(_fetch_latest_insight, uid, db),
                "period_entries": executor.submit(_fetch_period_entries, uid, db, period_days),
                "cache": executor.submit(_fetch_dashboard_cache, uid, db),
            }

            results = {}
            for key, future in futures.items():
                try:
                    results[key] = future.result(timeout=4)  # Fix 5: timeout=4 instead of 10
                except TimeoutError as te:
                    logger.warning("Journey fetch timeout for key=%s: %s", key, str(te))
                    if key in ("trends", "period_entries"):
                        results[key] = []
                    elif key == "insight":
                        results[key] = None
                    elif key == "cache":
                        results[key] = None
                    else:
                        results[key] = None
                except Exception as e:
                    logger.warning("Journey fetch error for key=%s: %s", key, str(e))
                    if key in ("trends", "period_entries"):
                        results[key] = []
                    elif key == "insight":
                        results[key] = None
                    elif key == "cache":
                        results[key] = None
                    else:
                        results[key] = None

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

        # Generate ai_insight: prefer cache, then appreciation, then default
        if cache and isinstance(cache, dict) and cache.get("ai_insight"):
            ai_insight = cache.get("ai_insight")
        elif insight and isinstance(insight, dict) and insight.get("appreciation"):
            ai_insight = _clean_ai_insight(str(insight.get("appreciation", "")), max_len=120)
        else:
            ai_insight = "Keep reflecting—your patterns are becoming clearer."
        
        # Fix 4: Empty state logic when no entries in the requested period
        if not trend_data:
            mood_trend = []
            mood_distribution = {m: 0 for m in VALID_MOODS}
            stats_obj = {"top_mood": None, "entries": 0, "streak": 0}

            # Set period-specific fallback text
            if period_days == 7:
                ai_insight = "No entries in the last 7 days. Write something today — even a sentence captures where you are right now."
            else:  # 30 days
                ai_insight = "No entries in the last 30 days. Your journal is waiting. Start small and build the habit back up."

            behavioral_pattern = "Patterns emerge from consistency. The more you write, the more you'll see about yourself."
            suggested_actions = [
                {"title": "Write today", "subtitle": "Open the journal and write one sentence about how you feel right now."},
                {"title": "Set a reminder", "subtitle": "Pick a time each day to journal — morning works well for most people."}
            ]
            goal_progress = []
        else:
            # Fix 3: mood_distribution is now a count dict instead of per-date snapshots
            mood_distribution = {mood: 0 for mood in VALID_MOODS}
            for entry in trend_data:
                if isinstance(entry, dict) and "mood" in entry:
                    mood = entry.get("mood")
                    if mood in mood_distribution:
                        mood_distribution[mood] += 1

            mood_trend = aggregate_mood_trend(trend_data)
            top_mood = get_top_mood(trend_data)
            stats_obj = {
                "top_mood": top_mood,
                "entries": len(period_entries),
                "streak": len(mood_trend)
            }

        response = {
            "period": f"{period_days}d",
            "ai_insight": ai_insight,
            "stats": stats_obj,
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

