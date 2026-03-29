# services/analytics/streak_service.py

from datetime import datetime, timedelta
import pytz
from firebase_admin import firestore

TZ = pytz.timezone("Asia/Kolkata")


def calculate_streak(uid, db):
    """
    Calculate user's writing streak.
    
    Returns:
    - current_streak: consecutive days from today
    - longest_streak: longest consecutive sequence ever
    - total_active_days: total days with entries
    """
    try:
        # Fetch all entries for user
        docs = (
            db.db.collection("journal_entries")
            .where(filter=firestore.FieldFilter("uid", "==", uid))
            .order_by("created_at", direction="DESCENDING")
            .stream()
        )
        
        # Extract unique dates (date only, no time)
        dates = sorted(set([
            doc.to_dict()["created_at"].astimezone(TZ).date()
            for doc in docs
            if "created_at" in doc.to_dict()
        ]), reverse=True)
        
        if not dates:
            return {
                "current_streak": 0,
                "longest_streak": 0,
                "total_active_days": 0
            }, 200
        
        # Calculate current streak (from most recent date backwards)
        current_streak = 0
        today = datetime.now(TZ).date()
        current = dates[0]
        
        # Check if most recent entry is today or yesterday
        if (today - current).days <= 1:
            # Start counting from the most recent date
            for d in dates:
                if d == current:
                    current_streak += 1
                    current -= timedelta(days=1)
                else:
                    break
        
        # Calculate longest streak and total active days
        longest_streak = 0
        temp_streak = 1
        prev_date = None
        
        for d in sorted(dates):
            if prev_date and (d - prev_date).days == 1:
                temp_streak += 1
            else:
                temp_streak = 1
            
            longest_streak = max(longest_streak, temp_streak)
            prev_date = d
        
        return {
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "total_active_days": len(dates)
        }, 200
        
    except Exception as e:
        return {"error": str(e)}, 500
