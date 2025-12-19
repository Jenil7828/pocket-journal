from datetime import datetime
import pytz
from firebase_admin import firestore
from utils import extract_dominant_mood


def process_entry(user, data, db, predictor, summarizer):
    if not data or "entry_text" not in data:
        return {"error": "Missing entry_text"}, 400

    uid = user["uid"]
    text = data["entry_text"]

    entry_id = db.insert_entry(uid, text)
    summary = summarizer.summarize(text) if summarizer else text[:200] + "..."
    mood_result = predictor.predict(summary, threshold=0.25)
    mood_probs = mood_result["probabilities"]
    db.insert_analysis(entry_id, summary, mood_probs)

    return {"entry_id": entry_id, "summary": summary, "mood_probs": mood_probs}, 200


def delete_entry(entry_id, uid, db):
    result = db.delete_entry(entry_id, uid)
    if result["success"]:
        return {"message": "Entry deleted successfully", "deleted": result["deleted"]}, 200
    return {"error": result["error"]}, 400


def delete_entries_batch(entry_ids, uid, db):
    result = db.delete_entries_batch(entry_ids, uid)
    if result["success"]:
        return {
            "message": "All entries deleted successfully",
            "deleted_count": result["deleted_count"],
            "deleted_entries": result["deleted_entries"],
        }, 200
    return {
        "message": "Some entries could not be deleted",
        "deleted_count": result["deleted_count"],
        "failed_count": result["failed_count"],
        "deleted_entries": result["deleted_entries"],
        "failed_entries": result["failed_entries"],
    }, 207


def update_entry(entry_id, uid, data, db, predictor, summarizer):
    if not entry_id:
        return {"error": "Entry ID is required"}, 400
    if not data or "entry_text" not in data:
        return {"error": "Missing entry_text in request body"}, 400

    new_entry_text = data["entry_text"]
    regenerate_analysis = data.get("regenerate_analysis", True)

    if not new_entry_text.strip():
        return {"error": "Entry text cannot be empty"}, 400

    if regenerate_analysis:
        result = db.update_entry_with_analysis(entry_id, uid, new_entry_text, predictor, summarizer)
    else:
        result = db.update_entry(entry_id, uid, new_entry_text)

    if result["success"]:
        return {"message": "Entry updated successfully", "updated": result["updated"]}, 200
    return {"error": result["error"]}, 400


def reanalyze_entry(entry_id, uid, db, predictor, summarizer):
    entry_doc = db.db.collection("journal_entries").document(entry_id).get()
    if not entry_doc.exists:
        return {"error": "Entry not found"}, 404

    entry_data = entry_doc.to_dict()
    if entry_data.get("uid") != uid:
        return {"error": "Unauthorized: Entry does not belong to user"}, 403

    entry_text = entry_data["entry_text"]

    analysis_query = db.db.collection("entry_analysis").where(filter=firestore.FieldFilter("entry_id", "==", entry_id)).get()
    old_analysis_ids = []
    for analysis_doc in analysis_query:
        analysis_doc.reference.delete()
        old_analysis_ids.append(analysis_doc.id)

    summary = summarizer.summarize(entry_text) if summarizer else entry_text[:200] + "..."
    mood_probs = predictor.predict(summary)
    db.insert_analysis(entry_id, summary, mood_probs)

    return {
        "message": "Entry reanalyzed successfully",
        "entry_id": entry_id,
        "old_analysis_deleted": len(old_analysis_ids),
        "old_analysis_ids": old_analysis_ids,
        "new_analysis": {"summary": summary, "mood_probs": mood_probs},
    }, 200


def get_single_entry(entry_id, uid, db):
    entry_doc = db.db.collection("journal_entries").document(entry_id).get()
    if not entry_doc.exists:
        return {"error": "Entry not found"}, 404

    entry_data = entry_doc.to_dict()
    if entry_data.get("uid") != uid:
        return {"error": "Unauthorized: Entry does not belong to user"}, 403

    analysis_query = db.db.collection("entry_analysis").where(filter=firestore.FieldFilter("entry_id", "==", entry_id)).get()
    analysis_data = None
    for analysis_doc in analysis_query:
        analysis_data = analysis_doc.to_dict()
        analysis_data["analysis_id"] = analysis_doc.id
        break

    return {
        "entry_id": entry_id,
        "entry_text": entry_data["entry_text"],
        "created_at": entry_data["created_at"],
        "updated_at": entry_data.get("updated_at"),
        "analysis": analysis_data,
    }, 200


def get_entry_analysis(entry_id, uid, db):
    entry_doc = db.db.collection("journal_entries").document(entry_id).get()
    if not entry_doc.exists:
        return {"error": "Entry not found"}, 404

    entry_data = entry_doc.to_dict()
    if entry_data.get("uid") != uid:
        return {"error": "Unauthorized: Entry does not belong to user"}, 403

    analysis_query = db.db.collection("entry_analysis").where(filter=firestore.FieldFilter("entry_id", "==", entry_id)).get()
    analysis_data = None
    for analysis_doc in analysis_query:
        analysis_data = analysis_doc.to_dict()
        analysis_data["analysis_id"] = analysis_doc.id
        break

    return {"entry_id": entry_id, "analysis": analysis_data}, 200


def get_entries_filtered(uid, params, db):
    start_date = params.get("start_date")
    end_date = params.get("end_date")
    mood_filter = params.get("mood")
    search_term = params.get("search")

    try:
        limit = int(params.get("limit", 50))
        offset = int(params.get("offset", 0))
    except ValueError:
        return {"error": "Invalid limit or offset parameter"}, 400

    if limit < 1 or limit > 100:
        return {"error": "Limit must be between 1 and 100"}, 400
    if offset < 0:
        return {"error": "Offset must be non-negative"}, 400

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

    query = query.order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)

    entries = []
    all_entries = []
    for entry_doc in query.stream():
        entry_data = entry_doc.to_dict()
        entry_data["entry_id"] = entry_doc.id
        all_entries.append(entry_data)

    for entry_data in all_entries:
        try:
            if search_term and search_term.lower() not in entry_data["entry_text"].lower():
                continue

            if mood_filter:
                try:
                    analysis_query = db.db.collection("entry_analysis").where(filter=firestore.FieldFilter("entry_id", "==", entry_data["entry_id"])).get()
                    has_matching_mood = False
                    for analysis_doc in analysis_query:
                        analysis_data = analysis_doc.to_dict()
                        mood_probs = analysis_data.get("mood", {})
                        if mood_probs:
                            dominant_mood = extract_dominant_mood(mood_probs)
                            if dominant_mood and dominant_mood == mood_filter.lower():
                                has_matching_mood = True
                                break
                    if not has_matching_mood:
                        continue
                except Exception:
                    pass

            entries.append(entry_data)
        except Exception:
            continue

    total_count = len(entries)
    entries = entries[offset:offset + limit]

    return {
        "entries": entries,
        "count": len(entries),
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
        "filters": {
            "start_date": start_date,
            "end_date": end_date,
            "mood": mood_filter,
            "search": search_term,
        },
    }, 200