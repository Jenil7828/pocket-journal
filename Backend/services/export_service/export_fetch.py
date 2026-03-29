from datetime import datetime
import pytz
from firebase_admin import firestore

_TZ = "Asia/Kolkata"


def fetch_entries_and_insights(uid: str, start_date: str, end_date: str, db):
    query = db.db.collection("journal_entries").where(filter=firestore.FieldFilter("uid", "==", uid))

    if start_date and start_date.strip():
        try:
            start_date_str = str(start_date).strip()
            start_datetime_naive = datetime.strptime(start_date_str, "%Y-%m-%d")
            IST = pytz.timezone(_TZ)
            start_datetime = IST.localize(start_datetime_naive)
            query = query.where(filter=firestore.FieldFilter("created_at", ">=", start_datetime))
        except ValueError:
            return {"error": "Invalid start_date format. Use YYYY-MM-DD"}, 400

    if end_date and end_date.strip():
        try:
            end_date_str = str(end_date).strip()
            end_datetime_naive = datetime.strptime(end_date_str, "%Y-%m-%d")
            IST = pytz.timezone(_TZ)
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

    return entries, insights
