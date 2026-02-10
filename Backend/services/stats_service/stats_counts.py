from datetime import datetime, timedelta
from firebase_admin import firestore
from utils import extract_dominant_mood


def get_user_stats(uid, db):
    entries_query = db.db.collection("journal_entries").where(filter=firestore.FieldFilter("uid", "==", uid))
    total_entries = len(list(entries_query.stream()))

    insights_query = db.db.collection("insights").where(filter=firestore.FieldFilter("uid", "==", uid))
    total_insights = len(list(insights_query.stream()))

    mood_distribution = {}
    analysis_query = db.db.collection("entry_analysis").stream()
    for analysis_doc in analysis_query:
        analysis_data = analysis_doc.to_dict()
        entry_id = analysis_data.get("entry_id")
        entry_doc = db.db.collection("journal_entries").document(entry_id).get()
        if entry_doc.exists and entry_doc.to_dict().get("uid") == uid:
            mood_probs = analysis_data.get("mood", {})
            if mood_probs:
                dominant_mood = extract_dominant_mood(mood_probs)
                if dominant_mood:
                    mood_distribution[dominant_mood] = mood_distribution.get(dominant_mood, 0) + 1

    seven_days_ago = datetime.now() - timedelta(days=7)
    recent_entries_query = db.db.collection("journal_entries").where(filter=firestore.FieldFilter("uid", "==", uid)).where(filter=firestore.FieldFilter("created_at", ">=", seven_days_ago))
    recent_entries_count = len(list(recent_entries_query.stream()))

    return {
        "total_entries": total_entries,
        "total_insights": total_insights,
        "recent_entries_7_days": recent_entries_count,
        "mood_distribution": mood_distribution,
        "most_common_mood": max(mood_distribution, key=mood_distribution.get) if mood_distribution else None,
    }, 200


def get_mood_trends(uid, days, db):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    entries_query = db.db.collection("journal_entries").where(filter=firestore.FieldFilter("uid", "==", uid)).where(filter=firestore.FieldFilter("created_at", ">=", start_date)).where(filter=firestore.FieldFilter("created_at", "<=", end_date))
    entries = list(entries_query.stream())

    mood_trends = []
    for entry_doc in entries:
        entry_data = entry_doc.to_dict()
        entry_id = entry_doc.id
        analysis_query = db.db.collection("entry_analysis").where(filter=firestore.FieldFilter("entry_id", "==", entry_id)).get()
        for analysis_doc in analysis_query:
            analysis_data = analysis_doc.to_dict()
            mood_probs = analysis_data.get("mood", {})
            if mood_probs:
                dominant_mood = extract_dominant_mood(mood_probs)
                if dominant_mood:
                    confidence = None
                    try:
                        confidence = float(analysis_data.get("mood", {}).get(dominant_mood))
                    except Exception:
                        confidence = None
                    mood_trends.append({
                        "date": entry_data["created_at"].strftime("%Y-%m-%d"),
                        "mood": dominant_mood,
                        "confidence": confidence,
                    })

    mood_trends.sort(key=lambda x: x["date"])

    return {
        "period_days": days,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "trends": mood_trends,
        "total_data_points": len(mood_trends),
    }, 200

