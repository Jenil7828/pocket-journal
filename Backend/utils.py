from typing import Any, Dict, Optional


def extract_dominant_mood(mood: Any) -> Optional[str]:
    """Return the dominant mood label from various possible stored formats.

    The `mood` stored in the DB may be a mapping of label->float, or
    label->{...}, so this helper normalizes and extracts a numeric score
    for each label and returns the label with the highest score.
    """
    if not isinstance(mood, dict):
        return None

    scores: Dict[str, float] = {}

    for label, val in mood.items():
        try:
            # Direct numeric
            if isinstance(val, (int, float)):
                scores[label] = float(val)
                continue

            # If the value is a dict, try common numeric keys
            if isinstance(val, dict):
                for k in ("prob", "probability", "score", "value", "confidence"):
                    if k in val and isinstance(val[k], (int, float)):
                        scores[label] = float(val[k])
                        break
                else:
                    # If dict contains a single numeric value, pick it
                    numeric_items = [v for v in val.values() if isinstance(v, (int, float))]
                    if numeric_items:
                        scores[label] = float(numeric_items[0])
                continue

            # If it's a string, try to coerce
            if isinstance(val, str):
                try:
                    scores[label] = float(val)
                except Exception:
                    continue
        except Exception:
            continue

    if not scores:
        return None

    # Return the label with highest numeric score
    return max(scores, key=scores.get)
