import logging

logger = logging.getLogger()


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

