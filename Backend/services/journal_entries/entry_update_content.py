# services/journal_entries/entry_update_content.py

def update_entry_content_only(entry_id, uid, data, db):
    """Update entry_text and/or title WITHOUT triggering analysis regeneration."""
    try:
        ref = db.db.collection("journal_entries").document(entry_id)
        doc = ref.get()
        
        if not doc.exists:
            return {"error": "Entry not found"}, 404
        
        entry_data = doc.to_dict()
        if entry_data.get("uid") != uid:
            return {"error": "Unauthorized"}, 403
        
        # Only update content fields
        update_data = {}
        if "entry_text" in data:
            update_data["entry_text"] = data["entry_text"]
        if "title" in data:
            update_data["title"] = data["title"]
        
        if not update_data:
            return {"error": "Must provide entry_text and/or title"}, 400
        
        ref.update(update_data)
        
        updated = ref.get().to_dict()
        updated["id"] = entry_id
        
        return {"entry": updated}, 200
    except Exception as e:
        return {"error": str(e)}, 500


