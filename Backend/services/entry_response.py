"""
Entry response builder

Produces a deterministic, interpretable API response that represents an emotionally
intelligent understanding of a user journal entry. It transforms raw model outputs
(mood probabilities + summary + timestamp) into a structured response without
exposing raw model probabilities.

Primary function:
    build_entry_response(input_json) -> dict

Design notes:
- Uses deterministic rules and math only (no ML, no randomness).
- Emotion dimensions (valence/arousal) are computed from an emotion-to-dimension
  mapping. Stability is derived from the entropy of the distribution.
- Emotional modes, confidence, intent tags, and recommendation strategies are
  rule-based and documented inline.

This module is intentionally standalone and has no external dependencies so it
can be used easily in production environments.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from math import log2
from typing import Dict, Any, List, Tuple, Optional

# Public API
__all__ = ["build_entry_response"]

# Known emotions (expected keys in mood_probs). We'll treat any missing keys as 0.
KNOWN_EMOTIONS = ["anger", "disgust", "fear", "happy", "neutral", "sad", "surprise"]

# Mapping of each emotion to its valence (-1..1) and arousal (-1..1) contributions.
# Values are deterministic, human-interpretable approximations based on common
# affective circumplex positions.
EMOTION_DIMENSIONS: Dict[str, Tuple[float, float]] = {
    "anger": (-0.85, 0.9),
    "disgust": (-0.7, 0.35),
    "fear": (-0.9, 0.9),
    "happy": (0.95, 0.75),
    "neutral": (0.0, 0.0),
    "sad": (-0.9, -0.35),
    "surprise": (0.2, 0.9),
}

# Deterministic text-to-intent keywords (lowercased). Order matters for stable
# tag ordering (we'll return tags sorted deterministically at the end).
INTENT_KEYWORDS: Dict[str, List[str]] = {
    "seeking_help": ["help", "support", "assist", "can't", "unable"],
    "celebration": ["celebrate", "congrat", "won", "achiev"],
    "reflection": ["reflect", "thinking", "thought", "remember"],
    "anxiety": ["anxious", "anxiety", "worried", "worry", "nervous"],
    "gratitude": ["thank", "grateful", "gratitude"],
    "planning": ["plan", "planning", "schedule", "prepare"],
    "loss": ["lost", "loss", "grief", "grieved"],
    "sleep_issues": ["sleep", "insomnia", "tired", "exhausted"],
    "relationships": ["friend", "partner", "family", "relationship", "love"],
}

# Recommendation strategies mapped to emotional_mode. Each entry contains:
# - strategy: short description
# - avoid: list of suggestions to avoid
# - prefer: list of recommended activities/content
RECOMMENDATION_MAP: Dict[str, Dict[str, List[str]]] = {
    "Driven Optimism": {
        "strategy": "Reinforce progress and nudge meaningful goal-setting.",
        "avoid": ["passive content", "doom-scrolling"],
        "prefer": ["reflective prompts", "micro-goal exercises", "gratitude journaling"],
    },
    "Restless Excitement": {
        "strategy": "Channel high energy into focused activities and calming routines.",
        "avoid": ["stimulant content", "overcommitment"],
        "prefer": ["breathing exercises", "short focusing tasks", "walking breaks"],
    },
    "Reflective Low": {
        "strategy": "Offer gentle reflection and mood-lift micro-interventions.",
        "avoid": ["heavy self-critique", "isolating tasks"],
        "prefer": ["supportive prompts", "mood-boosting suggestions", "light social check-ins"],
    },
    "Volatile Negative": {
        "strategy": "Stabilize mood first; provide grounding and quick coping tools.",
        "avoid": ["challenging cognitive tasks", "provocative content"],
        "prefer": ["grounding exercises", "breathing", "short peer-support prompts"],
    },
    "Neutral Stable": {
        "strategy": "Maintain balance and encourage continued awareness.",
        "avoid": ["unnecessary intensification"],
        "prefer": ["curated reading", "habit nudges", "light reflection prompts"],
    },
}


@dataclass(frozen=True)
class InputEntry:
    """Typed container for expected input.

    Fields:
    - entry_id: opaque string identifier
    - mood_probs: mapping from emotion -> probability (not necessarily normalized)
    - summary: short text summary from summarizer
    - timestamp: raw timestamp (str, int, or datetime)
    """

    entry_id: str
    mood_probs: Dict[str, float]
    summary: str
    timestamp: Any


# Helper utilities


def _coerce_numeric(v: Any) -> float:
    """Coerce value to float, treating invalid/missing as 0.0 deterministically."""
    try:
        if v is None:
            return 0.0
        if isinstance(v, bool):
            return 1.0 if v else 0.0
        return float(v)
    except Exception:
        return 0.0


def normalize_probs(mood_probs: Dict[str, Any]) -> Dict[str, float]:
    """Normalize and sanitize input probabilities into a deterministic distribution.

    Rules:
    - Missing known emotions are treated as 0.0.
    - Unknown keys are ignored.
    - Negative values or NaN are replaced with 0.0.
    - If the sum is zero after sanitization, fall back to a uniform distribution.
    - Return ordering is deterministic based on KNOWN_EMOTIONS.
    """
    sanitized: Dict[str, float] = {}
    total = 0.0
    for emo in KNOWN_EMOTIONS:
        raw = mood_probs.get(emo, 0.0) if isinstance(mood_probs, dict) else 0.0
        val = _coerce_numeric(raw)
        if val <= 0 or val != val:  # handles negatives and NaN
            val = 0.0
        sanitized[emo] = val
        total += val

    if total <= 0.0:
        # deterministic uniform fallback
        uniform = 1.0 / len(KNOWN_EMOTIONS)
        return {emo: round(uniform, 6) for emo in KNOWN_EMOTIONS}

    normalized = {emo: val / total for emo, val in sanitized.items()}
    # deterministic rounding to avoid floating noise while preserving relative order
    normalized = {emo: round(prob, 6) for emo, prob in normalized.items()}

    # Re-normalize to ensure a sum to 1.0 after rounding (distribute remainder deterministically)
    sum_norm = sum(normalized.values())
    remainder = round(1.0 - sum_norm, 6)
    if abs(remainder) >= 1e-6:
        # add remainder to the emotion with the largest probability (deterministic tie-breaker = label order)
        top_emo = max(normalized.items(), key=lambda kv: (kv[1], -KNOWN_EMOTIONS.index(kv[0])))[0]
        normalized[top_emo] = round(normalized[top_emo] + remainder, 6)

    return normalized


def _shannon_entropy(probs: Dict[str, float]) -> float:
    """Compute Shannon entropy (base 2) of the distribution. Returns 0..log2(n)."""
    h = 0.0
    for p in probs.values():
        if p > 0.0:
            h -= p * log2(p)
    return h


def compute_emotion_vector(probs: Dict[str, float]) -> Dict[str, float]:
    """Compute valence, arousal, and stability from normalized probabilities.

    - valence: weighted sum of emotion valence coordinates (range roughly -1..1)
    - arousal: weighted sum of arousal coordinates (range roughly -1..1)
    - stability: 1 - normalized entropy (so 1=very stable/peaked, 0=very volatile)

    These are deterministic transforms and intentionally interpretable.
    """
    # Weighted sums
    valence = 0.0
    arousal = 0.0
    for emo in KNOWN_EMOTIONS:
        weight = probs.get(emo, 0.0)
        v, a = EMOTION_DIMENSIONS.get(emo, (0.0, 0.0))
        valence += v * weight
        arousal += a * weight

    # Clip to -1..1 defensively
    valence = max(-1.0, min(1.0, valence))
    arousal = max(-1.0, min(1.0, arousal))

    # Stability from entropy
    entropy = _shannon_entropy(probs)
    max_entropy = log2(len(KNOWN_EMOTIONS))
    stability = 1.0 - (entropy / max_entropy) if max_entropy > 0 else 1.0
    stability = max(0.0, min(1.0, stability))

    # Return rounded to 3 decimal places for compactness
    return {"valence": round(valence, 3), "arousal": round(arousal, 3), "stability": round(stability, 3)}


def _select_emotional_mode(vec: Dict[str, float], dominant_emo: str) -> str:
    """Map the continuous emotion vector to one of the defined emotional modes.

    Rules (deterministic):
    - Driven Optimism: valence > 0.3, arousal <= 0.6, stability >= 0.6
    - Restless Excitement: valence > 0.2, arousal > 0.6, stability < 0.6
    - Reflective Low: valence < -0.35, arousal <= 0.0, stability >= 0.5
    - Volatile Negative: valence < -0.2 and stability < 0.5
    - Neutral Stable: default fallback when valence ~ 0 or stability high

    The dominant_emo is available for tie-breaking (e.g., sad plus low arousal -> Reflective Low).
    """
    v = vec["valence"]
    a = vec["arousal"]
    s = vec["stability"]

    # Deterministic priority order to avoid ambiguity
    if v > 0.3 and a <= 0.6 and s >= 0.6:
        return "Driven Optimism"
    if v > 0.2 and a > 0.6 and s < 0.6:
        return "Restless Excitement"
    if v < -0.35 and a <= 0.0 and s >= 0.5:
        return "Reflective Low"
    if v < -0.2 and s < 0.5:
        return "Volatile Negative"
    # If the distribution is extremely balanced and stable, call it neutral stable
    if abs(v) <= 0.15 and s >= 0.7:
        return "Neutral Stable"

    # Use sensible fallback rules involving the dominant emotion
    if dominant_emo in {"sad", "fear", "disgust"} and v < 0:
        return "Reflective Low" if a <= 0.2 else "Volatile Negative"
    if dominant_emo in {"happy", "surprise"} and v > 0:
        return "Driven Optimism" if s >= 0.5 else "Restless Excitement"

    return "Neutral Stable"


def _compute_confidence(probs: Dict[str, float]) -> float:
    """Compute a deterministic confidence score (0..1).

    Uses dominance (top - runner-up) and stability to estimate how confident the
    system should be about the emotional interpretation.

    Formula chosen deterministically:
        dominance = top - runner_up
        confidence = clamp(0..1, 0.7 * dominance + 0.3 * stability)
    """
    sorted_probs = sorted(probs.values(), reverse=True)
    top = sorted_probs[0]
    runner_up = sorted_probs[1] if len(sorted_probs) > 1 else 0.0
    dominance = max(0.0, top - runner_up)

    # recompute stability for direct access (cheap):
    entropy = _shannon_entropy(probs)
    max_entropy = log2(len(probs))
    stability = 1.0 - (entropy / max_entropy) if max_entropy > 0 else 1.0

    conf = 0.7 * dominance + 0.3 * stability
    conf = max(0.0, min(1.0, conf))
    return round(conf, 3)


def extract_intent_tags(summary: str, dominant_emo: str) -> List[str]:
    """Deterministic lightweight intent tagging.

    Rules:
    - Tokenize summary (simple whitespace, lowercasing) and check keyword substrings.
    - Add a tag for the dominant emotion simplified to a stable label.
    - Return tags sorted deterministically.
    """
    summary_l = (summary or "").lower()
    tags: List[str] = []

    # keyword-based tags
    for tag, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in summary_l:
                tags.append(tag)
                break

    # emotion-derived simple tag
    emotion_tag_map = {
        "happy": "joy",
        "sad": "sadness",
        "anger": "anger",
        "fear": "fear",
        "disgust": "disgust",
        "surprise": "surprise",
        "neutral": "neutral",
    }
    if dominant_emo in emotion_tag_map:
        tags.append(emotion_tag_map[dominant_emo])

    # deterministic unique and sorted order
    unique = sorted(list(dict.fromkeys(tags)))
    return unique


def _parse_timestamp(ts: Any) -> Tuple[Optional[datetime], str]:
    """Parse timestamp robustly into an aware UTC datetime and return ISO-8601.

    Accepts:
    - datetime instances (naive -> treated as UTC)
    - ISO-8601 strings (datetime.fromisoformat)
    - integer/float epoch seconds

    If parsing fails deterministically, returns (None, original_string).
    """
    if isinstance(ts, datetime):
        dt = ts
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt, dt.isoformat()

    # epoch numeric
    if isinstance(ts, (int, float)):
        try:
            dt = datetime.fromtimestamp(float(ts), tz=timezone.utc)
            return dt, dt.isoformat()
        except Exception:
            return None, str(ts)

    # string attempts
    if isinstance(ts, str):
        s = ts.strip()
        # try ISO first
        try:
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt, dt.isoformat()
        except Exception:
            pass
        # try common formats deterministically
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(s, fmt)
                dt = dt.replace(tzinfo=timezone.utc)
                return dt, dt.isoformat()
            except Exception:
                continue

    return None, str(ts)


def _temporal_context_from_dt(dt: Optional[datetime], vec: Dict[str, float]) -> Dict[str, Any]:
    """Derive temporal context fields given a parsed datetime (or None).

    - timestamp: ISO string (or original if None)
    - emotion_trend: derived from stability (stable/shifting/volatile)
    - relative_position: based on proximity to now (today/recent/past/future)
    """
    now = datetime.now(timezone.utc)
    if dt is None:
        timestamp_iso = None
    else:
        timestamp_iso = dt.astimezone(timezone.utc).isoformat()

    s = vec["stability"]
    if s >= 0.7:
        emotion_trend = "stable"
    elif s >= 0.4:
        emotion_trend = "shifting"
    else:
        emotion_trend = "volatile"

    if dt is None:
        relative = "unknown"
    else:
        delta = now - dt
        if delta < timedelta(seconds=-60):
            relative = "future"
        elif abs(delta) <= timedelta(hours=24) and dt.date() == now.date():
            relative = "today"
        elif delta <= timedelta(days=2):
            relative = "recent"
        else:
            relative = "past"

    return {"timestamp": timestamp_iso, "emotion_trend": emotion_trend, "relative_position": relative}


def _derive_day_interpretation(vec: Dict[str, float], emotion_trend: str, summary: str) -> str:
    """Derive a short human-readable sentence describing how the day felt overall.

    Deterministic rules (uses only valence, arousal, stability, emotion_trend, summary):
    - Explicitly handles the requested cases (stressful->resolved, mixed/volatile,
      consistently negative/positive, calm/uneventful, low-energy but not sad).
    - Uses simple keyword signals from the summary for negative-phase and resolution-phase.
    - Neutral, simple, non-judgmental language returned as a single sentence.
    """
    valence = vec.get("valence", 0.0)
    arousal = vec.get("arousal", 0.0)
    stability = vec.get("stability", 0.0)

    s = (summary or "").lower()
    # keyword signals
    negative_kw = ["tense", "anxious", "anxiety", "worried", "worry", "stressed", "stressed", "frustrated", "irritat"]
    resolution_kw = ["better", "relieved", "calm", "satisfied", "okay", "manageable", "okay", "relief"]

    negative_present = any(kw in s for kw in negative_kw)
    resolution_present = any(kw in s for kw in resolution_kw)

    # Case 1: Stressful start -> calm/satisfied end (explicit signal in text)
    if negative_present and resolution_present and (emotion_trend == "volatile" or stability < 0.6):
        return "Stressful day, but it ended well"

    # Case 2: Emotionally mixed / volatile day
    if emotion_trend == "volatile" or stability < 0.4:
        return "Emotionally mixed day with highs and lows"

    # Case 3: Consistently negative day (low valence and reasonably stable)
    if valence <= -0.35 and stability >= 0.5:
        return "A difficult and emotionally draining day"

    # Case 4: Consistently positive day
    if valence >= 0.3 and stability >= 0.5:
        return "A positive and satisfying day overall"

    # Case 5: Calm, routine, uneventful day
    if abs(valence) <= 0.15 and stability >= 0.7 and abs(arousal) <= 0.3:
        return "A calm and uneventful day"

    # Case 6: Low energy / tired but not sad
    if arousal <= -0.35 and valence > -0.2:
        return "A tiring day, but emotionally manageable"

    # Fallbacks that still reflect arc and are neutral
    # If there is textual evidence of negative then resolution but trend not volatile, prefer a soft phrasing
    if negative_present and resolution_present:
        return "Difficult moments earlier, but it felt better by the end"

    # If summary contains negative words and no resolution, acknowledge difficulty
    if negative_present and valence < 0:
        return "A challenging day with some difficult moments"

    # If summary contains resolution words and valence positive-ish
    if resolution_present and valence > 0:
        return "A day that improved over time and felt positive by the end"

    # Conservative neutral fallbacks
    if valence > 0.15:
        return "A generally positive day with some variation"
    if valence < -0.15:
        return "A generally negative day with ups and downs"

    return "An emotionally steady day"


def _recommendation_from_mode(mode: str) -> Dict[str, Any]:
    """Return recommendation strategy dict for a given emotional mode.

    Ensures safe defaults if mode is unknown.
    """
    entry = RECOMMENDATION_MAP.get(mode)
    if entry is None:
        # default neutral strategy
        return RECOMMENDATION_MAP["Neutral Stable"]
    # copy to avoid accidental mutation
    return {"strategy": entry["strategy"], "avoid": list(entry["avoid"]), "prefer": list(entry["prefer"]) }


# Main function

def build_entry_response(input_json: Dict[str, Any]) -> Dict[str, Any]:
    """Build the emotionally intelligent API response for a single entry.

    Input shape (example):
        {
            "entry_id": "abc123",
            "mood_probs": {"happy": 0.8, "sad": 0.1, ...},
            "summary": "Short summary text",
            "timestamp": "2023-07-01T12:00:00Z"
        }

    Returns a dict matching the required API response structure.

    Deterministic behavior highlights:
    - No raw probabilities are returned.
    - All derived numbers are rounded for stability.
    """
    # Basic validation and extraction; keep failures deterministic via ValueError
    if not isinstance(input_json, dict):
        raise ValueError("input_json must be a dict with keys: entry_id, mood_probs, summary, timestamp")

    entry_id = str(input_json.get("entry_id", ""))
    raw_probs = input_json.get("mood_probs", {}) or {}
    summary = str(input_json.get("summary", ""))
    ts_raw = input_json.get("timestamp")

    # Normalize probs deterministically
    probs = normalize_probs(raw_probs)

    # Dominant emotion selection (deterministic tie-breaker: prob desc, label asc)
    sorted_items = sorted(probs.items(), key=lambda kv: (-kv[1], kv[0]))
    dominant_emo, dominant_prob = sorted_items[0]

    # Compute vector
    vec = compute_emotion_vector(probs)

    # Emotional mode
    emotional_mode = _select_emotional_mode(vec, dominant_emo)

    # Confidence
    confidence = _compute_confidence(probs)

    # Intent tags
    intent_tags = extract_intent_tags(summary, dominant_emo)

    # Timestamp parsing
    dt, timestamp_iso_or_original = _parse_timestamp(ts_raw)

    temporal = _temporal_context_from_dt(dt, vec)
    # If parsing failed, preserve original string deterministically
    if temporal["timestamp"] is None:
        temporal["timestamp"] = timestamp_iso_or_original

    # NEW: compute day interpretation using deterministic helper
    day_interpretation = _derive_day_interpretation(vec, temporal["emotion_trend"], summary)

    # Recommendation
    rec = _recommendation_from_mode(emotional_mode)

    # Build final response according to the required schema
    response = {
        "entry_id": entry_id,
        "emotional_state": {
            "emotion_vector": {
                "valence": vec["valence"],
                "arousal": vec["arousal"],
                "stability": vec["stability"],
            },
            "emotional_mode": emotional_mode,
            "confidence": confidence,
            # NEW: day interpretation logic
            "day_interpretation": day_interpretation,
        },
        "semantic_context": {
            "summary": summary,
            "intent_tags": intent_tags,
        },
        "temporal_context": {
            "timestamp": temporal["timestamp"],
            "emotion_trend": temporal["emotion_trend"],
            "relative_position": temporal["relative_position"],
        },
        "recommendation_strategy": {
            "strategy": rec["strategy"],
            "avoid": rec["avoid"],
            "prefer": rec["prefer"],
        },
    }

    return response

