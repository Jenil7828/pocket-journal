from .export_fetch import fetch_entries_and_insights
from .export_format import format_as_csv
from datetime import datetime


def export_data(uid, start_date, end_date, export_format, db):
    entries, insights = fetch_entries_and_insights(uid, start_date, end_date, db)

    if isinstance(entries, dict) and entries.get("error"):
        return entries, 400

    export_data = {
        "user_id": uid,
        "export_timestamp": datetime.now().isoformat(),
        "date_range": {"start_date": start_date, "end_date": end_date},
        "entries": entries,
        "insights": insights,
        "total_entries": len(entries),
        "total_insights": len(insights),
    }

    if export_format == "csv":
        csv_text = format_as_csv(entries)
        return csv_text, 200, {"Content-Type": "text/csv"}

    return export_data, 200


__all__ = ["export_data"]

