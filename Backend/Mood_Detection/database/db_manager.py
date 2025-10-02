import os
from datetime import datetime, time
import firebase_admin
from firebase_admin import credentials, firestore
from collections import defaultdict
import pytz

class DBManager:
    def __init__(self, firebase_json_path=None):
        # Initialize Firebase
        cred_path = firebase_json_path or os.getenv("FIREBASE_CREDENTIALS_PATH")
        if not firebase_admin._apps:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        self.db = firestore.client()
        self.tz = pytz.timezone("Asia/Kolkata")  # IST timezone

    # -------------------- Journal Entries --------------------
    def insert_entry(self, uid: str, entry_text: str) -> str:
        doc_ref = self.db.collection("journal_entries").document()
        IST = pytz.timezone("Asia/Kolkata")
        data = {
            "uid": uid,
            "entry_text": entry_text,
            "created_at": datetime.now(IST)  # store in IST
        }
        doc_ref.set(data)
        return doc_ref.id

    def insert_analysis(self, entry_id: str, summary: str, mood: dict):
        doc_ref = self.db.collection("entry_analysis").document()
        IST = pytz.timezone("Asia/Kolkata")
        data = {
            "entry_id": entry_id,
            "summary": summary,
            "mood": mood,
            "created_at": datetime.now(IST)  # IST
        }
        doc_ref.set(data)

    def insert_insights(self, uid: str, start_date: str, end_date: str, goals: list,
                        progress: str, negative_behaviors: str, remedies: str,
                        appreciation: str, conflicts: str, raw_response: str,
                        entry_ids: list = None):
        doc_ref = self.db.collection("insights").document()
        IST = pytz.timezone("Asia/Kolkata")
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
            "created_at": datetime.now(IST)  # IST
        }
        doc_ref.set(data)

        if entry_ids:
            for entry_id in entry_ids:
                self.db.collection("insight_entry_mapping").add({
                    "insight_id": doc_ref.id,
                    "entry_id": entry_id
                })

    # -------------------- Fetch Entries --------------------
    def fetch_entries_with_analysis(self, uid: str, start_date: str = None, end_date: str = None):
        collection = self.db.collection("journal_entries")
        query = collection.where("uid", "==", uid)

        # Convert ISO date strings to IST datetime
        if start_date:
            start_dt = self.tz.localize(datetime.fromisoformat(start_date)).replace(
                hour=0, minute=0, second=0, microsecond=0)
            query = query.where("created_at", ">=", start_dt)
        if end_date:
            end_dt = self.tz.localize(datetime.fromisoformat(end_date)).replace(
                hour=23, minute=59, second=59, microsecond=999999)
            query = query.where("created_at", "<=", end_dt)

        query = query.order_by("created_at")
        docs = query.stream()

        result = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id

            # attach analysis
            analysis_query = self.db.collection("entry_analysis").where("entry_id", "==", doc.id).limit(1).get()
            data["analysis"] = analysis_query[0].to_dict() if analysis_query else {}

            result.append(data)

        return result

    def fetch_today_entries_with_mood_summary(self, uid: str):
        print("===== FETCH TODAY ENTRIES START =====")

        now = datetime.now(self.tz)
        today = now.date()

        start_dt = datetime.combine(today, time.min).replace(tzinfo=self.tz)
        end_dt = datetime.combine(today, time.max).replace(tzinfo=self.tz)
        print("Start datetime (IST):", start_dt)
        print("End datetime (IST):", end_dt)

        collection = self.db.collection("journal_entries")
        query = (
            collection
            .where("uid", "==", uid)
            .where("created_at", ">=", start_dt)
            .where("created_at", "<=", end_dt)
            .order_by("created_at")
        )

        docs = query.stream()
        entries = []
        mood_counts = defaultdict(int)

        for count, doc in enumerate(docs, start=1):
            data = doc.to_dict()
            data["id"] = doc.id
            print(f"\n--- Entry {count} ---")
            print("Document data:", data)

            # Fetch entry_analysis
            analysis_query = self.db.collection("entry_analysis").where("entry_id", "==", doc.id).limit(1).get()
            if analysis_query:
                data["analysis"] = analysis_query[0].to_dict()
                mood = data["analysis"].get("mood")
                if mood:
                    dominant_entry = max(mood, key=mood.get)
                    mood_counts[dominant_entry] += 1
                    print(f"Dominant mood for this entry: {dominant_entry}")
                print("Analysis found:", data["analysis"])
            else:
                data["analysis"] = {}
                print("No analysis found")

            entries.append(data)

        dominant_mood = max(mood_counts, key=mood_counts.get) if mood_counts else None
        print("Mood counts:", dict(mood_counts))
        print("Dominant mood:", dominant_mood)
        print("Number of docs fetched:", len(entries))
        print("===== FETCH TODAY ENTRIES END =====\n")

        return {"dominant_mood": dominant_mood, "entries": entries}

