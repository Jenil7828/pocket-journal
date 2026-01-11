from datetime import datetime
import pytz
from firebase_admin import firestore


def export_data(uid, start_date, end_date, export_format, db):
    query = db.db.collection("journal_entries").where(filter=firestore.FieldFilter("uid", "==", uid))

    if start_date and start_date.strip():
        try:
            start_date_str = str(start_date).strip()
            start_datetime_naive = datetime.strptime(start_date_str, "%Y-%m-%d")
            IST = pytz.timezone("Asia/Kolkata")
            start_datetime = IST.localize(start_datetime_naive)
            query = query.where(filter=firestore.FieldFilter("created_at", ">=", start_datetime))
        except ValueError:
            return {"error": "Invalid start_date format. Use YYYY-MM-DD"}, 400

    if end_date and end_date.strip():
        try:
            end_date_str = str(end_date).strip()
            end_datetime_naive = datetime.strptime(end_date_str, "%Y-%m-%d")
            IST = pytz.timezone("Asia/Kolkata")
            end_datetime = IST.localize(end_datetime_naive.replace(hour=23, minute=59, second=59))
            query = query.where(filter=firestore.FieldFilter("created_at", "<=", end_datetime))
        except ValueError:
            return {"error": "Invalid end_date format. Use YYYY-MM-DD"}, 400

    entries = []
    for entry_doc in query.stream():
        entry_data = entry_doc.to_dict()
        entry_data["entry_id"] = entry_doc.id
        analysis_query = db.db.collection("entry_analysis").where(filter=firestore.FieldFilter("entry_id", "==", entry_doc.id)).get()
        analysis_data = None
        for analysis_doc in analysis_query:
            analysis_data = analysis_doc.to_dict()
            analysis_data["analysis_id"] = analysis_doc.id
            break
        entry_data["analysis"] = analysis_data
        entries.append(entry_data)

    insights = []
    insights_query = db.db.collection("insights").where(filter=firestore.FieldFilter("uid", "==", uid))
    for insight_doc in insights_query.stream():
        insight_data = insight_doc.to_dict()
        insight_data["insight_id"] = insight_doc.id
        insights.append(insight_data)

    export_data = {
        "user_id": uid,
        "export_timestamp": datetime.now().isoformat(),
        "date_range": {"start_date": start_date, "end_date": end_date},
        "entries": entries,
        "insights": insights,
        "total_entries": len(entries),
        "total_insights": len(insights),
    }

    if export_format == "csv":
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["entry_id", "entry_text", "created_at", "updated_at", "dominant_mood", "mood_confidence"])
        from utils import extract_dominant_mood

        for entry in entries:
            dominant_mood = None
            confidence = None
            if entry.get("analysis") and entry["analysis"].get("mood"):
                mood_probs = entry["analysis"]["mood"]
                dominant_mood = extract_dominant_mood(mood_probs)
                try:
                    confidence = entry["analysis"]["mood"].get(dominant_mood) if dominant_mood else None
                except Exception:
                    confidence = None
            writer.writerow([
                entry["entry_id"],
                entry["entry_text"],
                entry["created_at"].isoformat() if entry.get("created_at") else "",
                entry.get("updated_at").isoformat() if entry.get("updated_at") else "",
                dominant_mood,
                confidence,
            ])
        return output.getvalue(), 200, {"Content-Type": "text/csv"}

    return export_data, 200