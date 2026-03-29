# services/journal_entries/entry_read_all.py
from firebase_admin import firestore

def get_all_entries(uid, db):
    """Get ALL journal entries for user (no filters, sorted by date DESC)."""
    try:
        docs = (
            db.db.collection("journal_entries")
            .where(filter=firestore.FieldFilter("uid", "==", uid))
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .stream()
        )
        
        results = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            results.append(data)
        
        return {"entries": results}, 200
    except Exception as e:
        return {"error": str(e)}, 500


