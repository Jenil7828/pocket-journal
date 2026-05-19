import logging
import pytz
from datetime import datetime
from typing import List, Dict, Any, Optional
from firebase_admin import firestore
from persistence.db_manager import DBManager
from config_loader import get_config

logger = logging.getLogger()
_CFG = get_config()
_TZ = pytz.timezone(_CFG["app"]["timezone"])
_COLS = _CFG["firestore"]["collections"]

class FirestoreFetcher:
    """Fetches real journal entries and analysis directly from Firestore.
    
    Uses DBManager for Firestore access to ensure consistent configuration usage.
    """
    
    def __init__(self, db_manager: DBManager):
        self.db_manager = db_manager
        self.db = db_manager.db

    def fetch_entries_for_uid(self, uid: str, limit: int = 100, 
                             start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """Fetch journal entries for a specific user ID with optional date filters."""
        logger.info("[DB] Fetching entries for uid=%s (limit=%d)", uid, limit)
        
        collection_name = _COLS.get("journal_entries", "journal_entries")
        query = self.db.collection(collection_name).where(
            filter=firestore.FieldFilter("uid", "==", uid)
        )

        if start_date:
            try:
                dt = _TZ.localize(datetime.strptime(start_date, "%Y-%m-%d"))
                query = query.where(filter=firestore.FieldFilter("created_at", ">=", dt))
            except ValueError:
                logger.warning("[DB] Invalid start_date format: %s. Expected YYYY-MM-DD", start_date)

        if end_date:
            try:
                dt = _TZ.localize(datetime.strptime(end_date, "%Y-%m-%d")).replace(
                    hour=23, minute=59, second=59, microsecond=999999
                )
                query = query.where(filter=firestore.FieldFilter("created_at", "<=", dt))
            except ValueError:
                logger.warning("[DB] Invalid end_date format: %s. Expected YYYY-MM-DD", end_date)

        query = query.order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)
        
        results = []
        for doc in query.stream():
            data = doc.to_dict()
            results.append({
                "entry_id": doc.id,
                "entry_text": data.get("entry_text", ""),
                "created_at": data.get("created_at").isoformat() if data.get("created_at") else None,
                "title": data.get("title"),
                "uid": data.get("uid")
            })
            
        logger.info("[DB] Found %d entries for evaluation", len(results))
        return results

    def fetch_entries_by_ids(self, uid: str, entry_ids: List[str]) -> List[Dict[str, Any]]:
        """Fetch specific journal entries by their document IDs."""
        logger.info("[DB] Fetching %d specific entries for uid=%s", len(entry_ids), uid)
        
        collection_name = _COLS.get("journal_entries", "journal_entries")
        results = []
        
        for eid in entry_ids:
            eid = eid.strip()
            if not eid:
                continue
                
            doc_ref = self.db.collection(collection_name).document(eid)
            doc = doc_ref.get()
            
            if not doc.exists:
                logger.warning("[DB] Entry %s not found in Firestore", eid)
                continue
                
            data = doc.to_dict()
            
            # Security check: ensure entry belongs to the specified user
            if data.get("uid") != uid:
                logger.warning("[DB] Entry %s does not belong to uid %s, skipping", eid, uid)
                continue
                
            results.append({
                "entry_id": doc.id,
                "entry_text": data.get("entry_text", ""),
                "created_at": data.get("created_at").isoformat() if data.get("created_at") else None,
                "title": data.get("title"),
                "uid": data.get("uid")
            })
            
        logger.info("[DB] Successfully fetched %d/%d entries", len(results), len(entry_ids))
        return results

    def fetch_entry_existing_analysis(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """Fetch existing analysis document for a given entry ID."""
        collection_name = _COLS.get("entry_analysis", "entry_analysis")
        query = self.db.collection(collection_name).where(
            filter=firestore.FieldFilter("entry_id", "==", entry_id)
        ).limit(1).get()
        
        if query:
            data = query[0].to_dict()
            return {
                "mood": data.get("mood", {}),
                "summary": data.get("summary", "")
            }
        return None
