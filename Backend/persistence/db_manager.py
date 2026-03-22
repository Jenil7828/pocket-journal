import os
import logging
from datetime import datetime, time
from collections import defaultdict

import firebase_admin
from firebase_admin import credentials, firestore
from firebase_admin import firestore as _fa_firestore
import pytz

from config_loader import get_config
from utils import extract_dominant_mood

logger = logging.getLogger("pocket_journal.db_manager")

_CFG = get_config()
_COLS = _CFG["firestore"]["collections"]
_TZ = _CFG["app"]["timezone"]


class DBManager:
    def __init__(self, firebase_json_path=None):
        cred_path = firebase_json_path or os.getenv("FIREBASE_CREDENTIALS_PATH")
        if not firebase_admin._apps:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)

        self.db = firestore.client()
        self.tz = pytz.timezone(_TZ)

    # -------------------- Journal Entries --------------------
    def insert_entry(self, uid: str, entry_text: str) -> str:
        doc_ref = self.db.collection(_COLS["journal_entries"]).document()
        now = datetime.now(self.tz)

        doc_ref.set({
            "uid": uid,
            "entry_text": entry_text,
            "created_at": now,
            "updated_at": now
        })
        return doc_ref.id

    def insert_analysis(self, entry_id: str, interpreted_response_or_summary, mood: dict = None, raw_analysis: dict = None):
        """Insert analysis for an entry.

        Backwards-compatible signature:
            insert_analysis(entry_id, summary, mood)
        New preferred signature:
            insert_analysis(entry_id, interpreted_response, raw_analysis=...)

        If an interpreted_response dict is provided, store its top-level sections
        (emotional_state, semantic_context, temporal_context, recommendation_strategy)
        at top-level in the document for easier querying. The raw ML outputs may be
        stored under 'raw_analysis' if provided.
        """
        now = datetime.now(self.tz)

        # Detect new call style: interpreted_response_or_summary is a dict with emotional_state
        doc = {"entry_id": entry_id, "created_at": now}
        if isinstance(interpreted_response_or_summary, dict) and "emotional_state" in interpreted_response_or_summary:
            interpreted = interpreted_response_or_summary
            # store top-level interpreted fields
            for k in ["emotional_state", "semantic_context", "temporal_context", "recommendation_strategy"]:
                if k in interpreted:
                    doc[k] = interpreted[k]
            # also keep entry_id reference and optionally raw_analysis
            if raw_analysis:
                doc["raw_analysis"] = raw_analysis
                # Backcompat: copy common raw fields into top-level keys for older code
                if isinstance(raw_analysis, dict):
                    if "mood" in raw_analysis:
                        doc["mood"] = raw_analysis["mood"]
                    if "mood_probs" in raw_analysis:
                        doc["mood"] = raw_analysis["mood_probs"]
                    if "summary" in raw_analysis:
                        doc["summary"] = raw_analysis["summary"]
        else:
            # backwards compatible: (entry_id, summary, mood)
            summary = interpreted_response_or_summary if isinstance(interpreted_response_or_summary, str) else ""
            doc["summary"] = summary
            if mood is not None:
                doc["mood"] = mood

        self.db.collection(_COLS["entry_analysis"]).document().set(doc)

    def insert_insights(
        self,
        uid: str,
        start_date: str,
        end_date: str,
        goals: list,
        progress: str,
        negative_behaviors: str,
        remedies: str,
        appreciation: str,
        conflicts: str,
        raw_response: str,
        entry_ids: list = None,
    ):
        doc_ref = self.db.collection(_COLS["insights"]).document()
        doc_ref.set({
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
            "created_at": datetime.now(self.tz),
        })

        if entry_ids:
            for entry_id in entry_ids:
                self.db.collection(_COLS["insight_entry_mapping"]).add({
                    "insight_id": doc_ref.id,
                    "entry_id": entry_id
                })

    # -------------------- Fetch Entries --------------------
    def fetch_entries_with_analysis(self, uid: str, start_date: str = None, end_date: str = None):
        query = self.db.collection(_COLS["journal_entries"]).where(
            filter=_fa_firestore.FieldFilter("uid", "==", uid)
        )

        if start_date:
            try:
                dt = self.tz.localize(datetime.strptime(start_date, "%Y-%m-%d"))
                query = query.where(filter=_fa_firestore.FieldFilter("created_at", ">=", dt))
            except ValueError:
                pass

        if end_date:
            try:
                dt = self.tz.localize(
                    datetime.strptime(end_date, "%Y-%m-%d")
                ).replace(hour=23, minute=59, second=59)
                query = query.where(filter=_fa_firestore.FieldFilter("created_at", "<=", dt))
            except ValueError:
                pass

        query = query.order_by("created_at")
        result = []

        for doc in query.stream():
            data = doc.to_dict()
            data["id"] = doc.id

            analysis = (
                self.db.collection(_COLS["entry_analysis"])
                .where(filter=_fa_firestore.FieldFilter("entry_id", "==", doc.id))
                .limit(1)
                .get()
            )

            data["analysis"] = analysis[0].to_dict() if analysis else {}
            result.append(data)

        return result

    def fetch_today_entries_with_mood_summary(self, uid: str):
        today = datetime.now(self.tz).date()
        start_dt = self.tz.localize(datetime.combine(today, time.min))
        end_dt = self.tz.localize(datetime.combine(today, time.max))

        query = (
            self.db.collection(_COLS["journal_entries"])
            .where(filter=_fa_firestore.FieldFilter("uid", "==", uid))
            .where(filter=_fa_firestore.FieldFilter("created_at", ">=", start_dt))
            .where(filter=_fa_firestore.FieldFilter("created_at", "<=", end_dt))
            .order_by("created_at")
        )

        entries = []
        mood_counts = defaultdict(int)

        for doc in query.stream():
            data = doc.to_dict()
            data["id"] = doc.id

            analysis = (
                self.db.collection(_COLS["entry_analysis"])
                .where(filter=_fa_firestore.FieldFilter("entry_id", "==", doc.id))
                .limit(1)
                .get()
            )

            if analysis:
                analysis_data = analysis[0].to_dict()
                data["analysis"] = analysis_data
                mood = analysis_data.get("mood")
                dominant = extract_dominant_mood(mood)
                if dominant:
                    mood_counts[dominant] += 1
            else:
                data["analysis"] = {}

            entries.append(data)

        dominant_mood = max(mood_counts, key=mood_counts.get) if mood_counts else None

        logger.info(
            "Fetched %d entries for uid=%s, dominant_mood=%s",
            len(entries),
            uid,
            dominant_mood,
        )

        return {
            "dominant_mood": dominant_mood,
            "entries": entries
        }

    # -------------------- Delete Entries --------------------
    def delete_entry(self, entry_id: str, uid: str) -> dict:
        try:
            entry_ref = self.db.collection(_COLS["journal_entries"]).document(entry_id)
            entry_doc = entry_ref.get()

            if not entry_doc.exists:
                return {"success": False, "error": "Entry not found"}

            if entry_doc.to_dict().get("uid") != uid:
                return {"success": False, "error": "Unauthorized: Entry does not belong to user"}

            entry_ref.delete()

            analysis_docs = (
                self.db.collection(_COLS["entry_analysis"])
                .where(filter=_fa_firestore.FieldFilter("entry_id", "==", entry_id))
                .get()
            )

            analysis_ids = []
            for doc in analysis_docs:
                analysis_ids.append(doc.id)
                doc.reference.delete()

            mapping_docs = (
                self.db.collection(_COLS["insight_entry_mapping"])
                .where(filter=_fa_firestore.FieldFilter("entry_id", "==", entry_id))
                .get()
            )

            for doc in mapping_docs:
                doc.reference.delete()

            return {
                "success": True,
                "deleted": {
                    "entry_id": entry_id,
                    "analysis_count": len(analysis_ids),
                    "analysis_ids": analysis_ids,
                    "insight_mappings_deleted": len(mapping_docs),
                },
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to delete entry: {str(e)}"}

    def delete_entries_batch(self, entry_ids: list, uid: str) -> dict:
        deleted_entries = []
        failed_entries = []

        for entry_id in entry_ids:
            result = self.delete_entry(entry_id, uid)
            if result["success"]:
                deleted_entries.append(result["deleted"])
            else:
                failed_entries.append({
                    "entry_id": entry_id,
                    "error": result["error"]
                })

        return {
            "success": len(failed_entries) == 0,
            "deleted_count": len(deleted_entries),
            "failed_count": len(failed_entries),
            "deleted_entries": deleted_entries,
            "failed_entries": failed_entries,
        }

    # -------------------- Update Entries --------------------
    def update_entry(self, entry_id: str, uid: str, new_entry_text: str) -> dict:
        try:
            ref = self.db.collection(_COLS["journal_entries"]).document(entry_id)
            doc = ref.get()

            if not doc.exists:
                return {"success": False, "error": "Entry not found"}

            if doc.to_dict().get("uid") != uid:
                return {"success": False, "error": "Unauthorized: Entry does not belong to user"}

            ref.update({
                "entry_text": new_entry_text,
                "updated_at": datetime.now(self.tz)
            })

            analysis_docs = (
                self.db.collection(_COLS["entry_analysis"])
                .where(filter=_fa_firestore.FieldFilter("entry_id", "==", entry_id))
                .get()
            )

            old_ids = []
            for doc in analysis_docs:
                old_ids.append(doc.id)
                doc.reference.delete()

            return {
                "success": True,
                "updated": {
                    "entry_id": entry_id,
                    "new_text": new_entry_text,
                    "old_analysis_deleted": len(old_ids),
                    "old_analysis_ids": old_ids,
                    "requires_reanalysis": True,
                },
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to update entry: {str(e)}"}

    def update_entry_with_analysis(self, entry_id, uid, new_entry_text, predictor, summarizer=None):
        result = self.update_entry(entry_id, uid, new_entry_text)
        if not result.get("success"):
            return result

        summary = summarizer.summarize(new_entry_text) if summarizer else new_entry_text[:200] + "..."
        mood_probs = predictor.predict(summary)

        # Build interpreted response using deterministic builder and store it
        # Import locally to avoid circular imports
        try:
            from ..services.entry_response import build_entry_response
        except Exception:
            # Fallback: if import fails, store legacy analysis
            self.insert_analysis(entry_id, summary, mood_probs)
            result["updated"]["new_analysis"] = {
                "summary": summary,
                "mood_probs": mood_probs,
            }
            return result

        # Prepare input for the builder (use timezone-aware timestamp)
        input_for_builder = {
            "entry_id": entry_id,
            "mood_probs": mood_probs,
            "summary": summary,
            "timestamp": datetime.now(self.tz),
        }
        interpreted = build_entry_response(input_for_builder)

        # Store interpreted response as primary analysis and keep raw under raw_analysis
        raw_analysis = {"summary": summary, "mood": mood_probs}
        self.insert_analysis(entry_id, interpreted, raw_analysis=raw_analysis)

        result["updated"]["new_analysis"] = interpreted
        return result
