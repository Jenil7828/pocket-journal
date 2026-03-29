# services/stats_service/stats_date_range.py

from datetime import datetime, timedelta
import pytz
from firebase_admin import firestore

TZ = pytz.timezone("Asia/Kolkata")

def get_stats_by_date_range(uid, start_date, end_date, db):
    """Get statistics for a date range with timezone-aware datetime and proper filtering."""
    try:
        # Parse dates if they're strings
        if isinstance(start_date, str):
            start_date_naive = datetime.fromisoformat(start_date)
            # Make timezone-aware if not already
            if start_date_naive.tzinfo is None:
                start_date = TZ.localize(start_date_naive)
            else:
                start_date = start_date_naive
        
        if isinstance(end_date, str):
            end_date_naive = datetime.fromisoformat(end_date)
            # Make timezone-aware if not already
            if end_date_naive.tzinfo is None:
                end_date = TZ.localize(end_date_naive)
            else:
                end_date = end_date_naive
        
        # Ensure both dates are timezone-aware
        if start_date.tzinfo is None:
            start_date = TZ.localize(start_date)
        if end_date.tzinfo is None:
            end_date = TZ.localize(end_date)
        
        # Build query with proper FieldFilter syntax
        query = (
            db.db.collection("journal_entries")
            .where(filter=firestore.FieldFilter("uid", "==", uid))
            .where(filter=firestore.FieldFilter("created_at", ">=", start_date))
            .where(filter=firestore.FieldFilter("created_at", "<=", end_date))
            .order_by("created_at")
        )
        
        docs = query.stream()
        
        entries = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            entries.append(data)
        
        # Calculate mood distribution if present
        mood_counts = {}
        for entry in entries:
            if "analysis" in entry and "mood" in entry["analysis"]:
                mood = entry["analysis"]["mood"]
                mood_counts[mood] = mood_counts.get(mood, 0) + 1
        
        return {
            "count": len(entries),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "mood_distribution": mood_counts,
            "entries": entries
        }, 200
    except Exception as e:
        return {"error": str(e)}, 500


