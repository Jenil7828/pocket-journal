import os
from datetime import datetime, time
import firebase_admin
from firebase_admin import credentials, firestore
from firebase_admin import firestore as _fa_firestore
from collections import defaultdict
from Backend.utils import extract_dominant_mood
import pytz
import logging

logger = logging.getLogger("pocket_journal.db_manager")

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
        now = datetime.now(IST)
        data = {
            "uid": uid,
            "entry_text": entry_text,
            "created_at": now,  # store in IST
            "updated_at": now   # initialize updated_at for new entries
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
        query = collection.where(filter=("uid", "==", uid))

        # Convert date strings to IST datetime
        if start_date:
            try:
                start_dt_naive = datetime.strptime(str(start_date), "%Y-%m-%d")
                start_dt = self.tz.localize(start_dt_naive).replace(
                    hour=0, minute=0, second=0, microsecond=0)
                query = query.where(filter=("created_at", ">=", start_dt))
            except ValueError:
                # If date parsing fails, skip the filter
                pass
        if end_date:
            try:
                end_dt_naive = datetime.strptime(str(end_date), "%Y-%m-%d")
                end_dt = self.tz.localize(end_dt_naive).replace(
                    hour=23, minute=59, second=59, microsecond=999999)
                query = query.where(filter=("created_at", "<=", end_dt))
            except ValueError:
                # If date parsing fails, skip the filter
                pass

        query = query.order_by("created_at")
        docs = query.stream()

        result = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id

            # attach analysis
            analysis_query = self.db.collection("entry_analysis").where(filter=("entry_id", "==", doc.id)).limit(1).get()
            data["analysis"] = analysis_query[0].to_dict() if analysis_query else {}

            result.append(data)

        return result

    def fetch_today_entries_with_mood_summary(self, uid: str):
        """Fetch today's entries for `uid` and return dominant mood plus entries.

        Keep logging minimal: do not dump per-entry document data or analysis content.
        """
        now = datetime.now(self.tz)
        today = now.date()

        start_dt = datetime.combine(today, time.min).replace(tzinfo=self.tz)
        end_dt = datetime.combine(today, time.max).replace(tzinfo=self.tz)

        collection = self.db.collection("journal_entries")
        query = (
            collection
            .where(filter=_fa_firestore.FieldFilter("uid", "==", uid))
            .where(filter=_fa_firestore.FieldFilter("created_at", ">=", start_dt))
            .where(filter=_fa_firestore.FieldFilter("created_at", "<=", end_dt))
            .order_by("created_at")
        )

        docs = query.stream()
        entries = []
        mood_counts = defaultdict(int)

        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id

            # Attach analysis if present, but do not log its contents
            analysis_query = self.db.collection("entry_analysis").where(filter=_fa_firestore.FieldFilter("entry_id", "==", doc.id)).limit(1).get()
            if analysis_query:
                analysis = analysis_query[0].to_dict()
                data["analysis"] = analysis
                mood = analysis.get("mood")
                dominant_entry = extract_dominant_mood(mood)
                if dominant_entry:
                    mood_counts[dominant_entry] += 1
            else:
                data["analysis"] = {}

            entries.append(data)

        dominant_mood = max(mood_counts, key=mood_counts.get) if mood_counts else None

        # Summary logging only: uid, dominant mood and number of entries
        logger.info("Fetched %s entries for uid=%s; dominant_mood=%s", len(entries), uid, dominant_mood)

        return {"dominant_mood": dominant_mood, "entries": entries}

    # -------------------- Delete Entries --------------------
    def delete_entry(self, entry_id: str, uid: str) -> dict:
        """
        Delete a journal entry and its associated analysis.
        Returns success status and details of what was deleted.
        """
        try:
            # First, verify the entry belongs to the user
            entry_doc = self.db.collection("journal_entries").document(entry_id).get()
            if not entry_doc.exists:
                return {"success": False, "error": "Entry not found"}
            
            entry_data = entry_doc.to_dict()
            if entry_data.get("uid") != uid:
                return {"success": False, "error": "Unauthorized: Entry does not belong to user"}
            
            # Delete the journal entry
            self.db.collection("journal_entries").document(entry_id).delete()
            
            # Find and delete associated analysis
            analysis_query = self.db.collection("entry_analysis").where(filter=_fa_firestore.FieldFilter("entry_id", "==", entry_id)).get()
            analysis_deleted = 0
            analysis_ids = []
            
            for analysis_doc in analysis_query:
                analysis_doc.reference.delete()
                analysis_deleted += 1
                analysis_ids.append(analysis_doc.id)
            
            # Also delete any insight mappings that reference this entry
            insight_mapping_query = self.db.collection("insight_entry_mapping").where(filter=_fa_firestore.FieldFilter("entry_id", "==", entry_id)).get()
            insight_mappings_deleted = 0
            
            for mapping_doc in insight_mapping_query:
                mapping_doc.reference.delete()
                insight_mappings_deleted += 1
            
            return {
                "success": True,
                "deleted": {
                    "entry_id": entry_id,
                    "analysis_count": analysis_deleted,
                    "analysis_ids": analysis_ids,
                    "insight_mappings_deleted": insight_mappings_deleted
                }
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to delete entry: {str(e)}"}

    def delete_entries_batch(self, entry_ids: list, uid: str) -> dict:
        """
        Delete multiple journal entries and their associated analysis.
        Returns success status and details of what was deleted.
        """
        try:
            deleted_entries = []
            failed_entries = []
            
            for entry_id in entry_ids:
                result = self.delete_entry(entry_id, uid)
                if result["success"]:
                    deleted_entries.append(result["deleted"])
                else:
                    failed_entries.append({"entry_id": entry_id, "error": result["error"]})
            
            return {
                "success": len(failed_entries) == 0,
                "deleted_count": len(deleted_entries),
                "failed_count": len(failed_entries),
                "deleted_entries": deleted_entries,
                "failed_entries": failed_entries
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to delete entries: {str(e)}"}

    # -------------------- Update Entries --------------------
    def update_entry(self, entry_id: str, uid: str, new_entry_text: str) -> dict:
        """
        Update a journal entry and regenerate its analysis.
        Returns success status and details of what was updated.
        """
        try:
            # First, verify the entry belongs to the user
            entry_doc = self.db.collection("journal_entries").document(entry_id).get()
            if not entry_doc.exists:
                return {"success": False, "error": "Entry not found"}
            
            entry_data = entry_doc.to_dict()
            if entry_data.get("uid") != uid:
                return {"success": False, "error": "Unauthorized: Entry does not belong to user"}
            
            # Update the journal entry text
            IST = pytz.timezone("Asia/Kolkata")
            self.db.collection("journal_entries").document(entry_id).update({
                "entry_text": new_entry_text,
                "updated_at": datetime.now(IST)
            })
            
            # Find and delete existing analysis
            analysis_query = self.db.collection("entry_analysis").where(filter=_fa_firestore.FieldFilter("entry_id", "==", entry_id)).get()
            old_analysis_ids = []
            
            for analysis_doc in analysis_query:
                analysis_doc.reference.delete()
                old_analysis_ids.append(analysis_doc.id)
            
            return {
                "success": True,
                "updated": {
                    "entry_id": entry_id,
                    "new_text": new_entry_text,
                    "old_analysis_deleted": len(old_analysis_ids),
                    "old_analysis_ids": old_analysis_ids,
                    "requires_reanalysis": True  # Flag to indicate analysis needs regeneration
                }
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to update entry: {str(e)}"}

    def update_entry_with_analysis(self, entry_id: str, uid: str, new_entry_text: str, 
                                 predictor, summarizer=None) -> dict:
        """
        Update a journal entry and immediately regenerate its analysis.
        This is a convenience method that combines update and reanalysis.
        """
        try:
            # First, verify the entry belongs to the user
            entry_doc = self.db.collection("journal_entries").document(entry_id).get()
            if not entry_doc.exists:
                return {"success": False, "error": "Entry not found"}
            
            entry_data = entry_doc.to_dict()
            if entry_data.get("uid") != uid:
                return {"success": False, "error": "Unauthorized: Entry does not belong to user"}
            
            # Update the journal entry text
            IST = pytz.timezone("Asia/Kolkata")
            self.db.collection("journal_entries").document(entry_id).update({
                "entry_text": new_entry_text,
                "updated_at": datetime.now(IST)
            })
            
            # Delete existing analysis
            analysis_query = self.db.collection("entry_analysis").where("entry_id", "==", entry_id).get()
            old_analysis_ids = []
            
            for analysis_doc in analysis_query:
                analysis_doc.reference.delete()
                old_analysis_ids.append(analysis_doc.id)
            
            # Generate new analysis
            summary = summarizer.summarize(new_entry_text) if summarizer else new_entry_text[:200] + "..."
            mood_probs = predictor.predict(summary)
            
            # Insert new analysis
            self.insert_analysis(entry_id, summary, mood_probs)
            
            return {
                "success": True,
                "updated": {
                    "entry_id": entry_id,
                    "new_text": new_entry_text,
                    "old_analysis_deleted": len(old_analysis_ids),
                    "old_analysis_ids": old_analysis_ids,
                    "new_analysis": {
                        "summary": summary,
                        "mood_probs": mood_probs
                    }
                }
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to update entry with analysis: {str(e)}"}

