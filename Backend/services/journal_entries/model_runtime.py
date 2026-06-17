import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from services.journal_entries.performance import JournalPerfLogger

logger = logging.getLogger()

_PREDICTOR_LOCK = threading.RLock()
_SUMMARIZER_LOCK = threading.RLock()


def summarize_text(
    summarizer,
    text: str,
    fallback_length: int,
    perf: Optional["JournalPerfLogger"] = None,
) -> str:
    """Thread-safe summarization wrapper with truncation fallback."""
    if not text:
        return ""
    if not summarizer:
        return text[:fallback_length] + ("..." if len(text) > fallback_length else "")

    started = time.perf_counter()
    with _SUMMARIZER_LOCK:
        try:
            summary = summarizer.summarize(text)
        except Exception:
            logger.exception("Summarization failed; using truncation fallback")
            summary = text[:fallback_length] + ("..." if len(text) > fallback_length else "")

    elapsed_ms = (time.perf_counter() - started) * 1000
    if perf:
        perf.mark("summary_generation", elapsed_ms)
    else:
        logger.info("[PERF][journal] stage=summary_generation duration_ms=%.1f", elapsed_ms)
    return summary


def predict_mood(
    predictor,
    text: str,
    perf: Optional["JournalPerfLogger"] = None,
) -> Dict:
    """Thread-safe mood prediction wrapper."""
    if not predictor or not text:
        return {}

    started = time.perf_counter()
    with _PREDICTOR_LOCK:
        try:
            mood_result = predictor.predict(text)
            if isinstance(mood_result, dict) and "probabilities" in mood_result:
                result = mood_result.get("probabilities") or {}
            else:
                result = mood_result if isinstance(mood_result, dict) else {}
        except Exception:
            logger.exception("Mood prediction failed; using empty probabilities")
            result = {}

    elapsed_ms = (time.perf_counter() - started) * 1000
    if perf:
        perf.event("mood_inference_segment", duration_ms=f"{elapsed_ms:.1f}")
    return result


def run_summary_and_mood_concurrently(
    predictor,
    summarizer,
    text: str,
    fallback_length: int,
    perf: Optional["JournalPerfLogger"] = None,
) -> Tuple[str, Dict]:
    """Run summary and mood prediction in parallel when both are available."""
    if not text:
        return "", {}

    if not predictor:
        return summarize_text(summarizer, text, fallback_length, perf=perf), {}
    if not summarizer:
        return summarize_text(None, text, fallback_length, perf=perf), predict_mood(predictor, text, perf=perf)

    parallel_started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=2) as ex:
        summary_future = ex.submit(summarize_text, summarizer, text, fallback_length, perf)
        mood_future = ex.submit(predict_mood, predictor, text, perf)
        summary = summary_future.result()
        mood_probs = mood_future.result()

    if perf:
        perf.mark(
            "parallel_fallback_wall_clock",
            (time.perf_counter() - parallel_started) * 1000,
        )
    return summary, mood_probs
