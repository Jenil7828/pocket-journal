import os
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

CURRENT_TIME = datetime.now()

class DBManager:
    def __init__(self, firebase_json_path=None):
        # Use provided path or env var
        cred_path = firebase_json_path or os.getenv("FIREBASE_CREDENTIALS_PATH")
        if not firebase_admin._apps:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        self.db = firestore.client()

    # -------------------- Journal Entries --------------------
    def insert_entry(self, uid: str, entry_text: str) -> str:
        doc_ref = self.db.collection("journal_entries").document()
        data = {
            "uid": uid,
            "entry_text": entry_text,
            "created_at": CURRENT_TIME
        }
        doc_ref.set(data)
        return doc_ref.id

    def fetch_entries_with_analysis(self, uid: str, start_date: str = None, end_date: str = None):
        collection = self.db.collection("journal_entries")
        query = collection.where("user_id", "==", uid)
        if start_date:
            query = query.where("created_at", ">=", datetime.fromisoformat(start_date))
        if end_date:
            query = query.where("created_at", "<=", datetime.fromisoformat(end_date))

        query = query.order_by("created_at")  # ensures range queries are indexed
        docs = query.stream()
        result = []

        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id

            # Fetch entry_analysis where entry_id matches journal entry ID
            analysis_query = self.db.collection("entry_analysis").where("entry_id", "==", doc.id).limit(1).get()
            if analysis_query:
                data["analysis"] = analysis_query[0].to_dict()
            else:
                data["analysis"] = {}

            result.append(data)

        return result

    def insert_analysis(self, entry_id: str, summary: str, mood: dict):
        doc_ref = self.db.collection("entry_analysis").document()
        data = {
            "entry_id": entry_id,
            "summary": summary,
            "mood": mood,
            "created_at": CURRENT_TIME
        }
        doc_ref.set(data)

    def insert_insights(self, uid: str, start_date: str, end_date: str, goals: list,
                        progress: str, negative_behaviors: str, remedies: str,
                        appreciation: str, conflicts: str, raw_response: str,
                        entry_ids: list = None):
        doc_ref = self.db.collection("insights").document()
        data = {
            "uid": uid,
            "start_date": start_date,
            "end_date": end_date,
            "goals": goals,
            "progress": progress,
            "negative_behaviors": negative_behaviors,
            "remedies": remedies,
            "appreciation": appreciation,
            "conflicts": conflicts,
            "raw_response": raw_response,
            "created_at": CURRENT_TIME
        }
        doc_ref.set(data)

        # Map entries to insights if provided
        if entry_ids:
            for entry_id in entry_ids:
                self.db.collection("insight_entry_mapping").add({
                    "insight_id": doc_ref.id,
                    "entry_id": entry_id
                })
