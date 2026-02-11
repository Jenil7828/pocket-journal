import csv
import io
from utils import extract_dominant_mood


def format_as_csv(entries):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["entry_id", "entry_text", "created_at", "updated_at", "dominant_mood", "mood_confidence"])

    for entry in entries:
        dominant_mood = None
        confidence = None
        if entry.get("analysis") and entry["analysis"].get("mood"):
            mood_probs = entry["analysis"]["mood"]
            dominant_mood = extract_dominant_mood(mood_probs)
            try:
                confidence = entry["analysis"]["mood"].get(dominant_mood) if dominant_mood else None
            except Exception:
                confidence = None
        writer.writerow([
            entry["entry_id"],
            entry["entry_text"],
            entry["created_at"].isoformat() if entry.get("created_at") else "",
            entry.get("updated_at").isoformat() if entry.get("updated_at") else "",
            dominant_mood,
            confidence,
        ])

    return output.getvalue()

