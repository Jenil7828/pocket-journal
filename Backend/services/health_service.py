from datetime import datetime
from firebase_admin import auth


def health_check(db):
    db_status = "connected"
    try:
        db.db.collection("journal_entries").limit(1).stream()
    except Exception:
        db_status = "disconnected"

    auth_status = "connected"
    try:
        auth.list_users(max_results=1)
    except Exception:
        auth_status = "disconnected"

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "database": db_status,
            "authentication": auth_status,
        },
        "version": "1.0.0",
    }, 200