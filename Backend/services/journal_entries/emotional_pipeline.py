"""
Emotional inference pipeline for journal entries.

Stage 1 — Emotional journey (sync):
  segment entry → mood per segment → trajectory → aggregate mood distribution

Stage 2 — Narrative summary (sync, parallel with stage 1):
  full journal text → single BART summarization call

Embeddings are not generated in this module. A single summary embedding is
created asynchronously after the API response (see background_tasks.py).
"""
from __future__ import annotations

import logging
import math
import re
import time
from typing import List, Dict, Any, Tuple

import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed

from config_loader import get_config
from services.journal_entries.model_runtime import predict_mood, summarize_text
from services.journal_entries.performance import JournalPerfLogger

logger = logging.getLogger()
_CFG = get_config()

# Lightweight valence map for trajectory analysis without embedding calls.
_EMOTION_VALENCE = {
    "happy": 1.0,
    "joy": 1.0,
    "love": 0.9,
    "surprise": 0.5,
    "gratitude": 0.8,
    "excitement": 0.85,
    "neutral": 0.0,
    "sad": -1.0,
    "anger": -0.9,
    "fear": -0.8,
    "anxiety": -0.7,
    "disgust": -0.8,
    "frustration": -0.75,
}


def _split_sentences(text: str) -> List[str]:
    if not text:
        return []
    t = text.replace("\r\n", "\n")
    parts = re.split(r"(?<=[.!?\n])\s+", t)
    return [p.strip() for p in parts if p and p.strip()]


def _dominant_emotion(probs: Dict[str, float]) -> str | None:
    if not probs:
        return None
    return max(probs.items(), key=lambda x: x[1])[0]


def _segment_valence(probs: Dict[str, float]) -> float:
    if not probs:
        return 0.0
    total = 0.0
    weight = 0.0
    for label, prob in probs.items():
        valence = _EMOTION_VALENCE.get(str(label).lower(), 0.0)
        p = float(prob)
        total += valence * p
        weight += p
    return total / weight if weight > 0 else 0.0


class Segmenter:
    """Sentence-based segmentation for emotion analysis only (no embeddings)."""

    def __init__(self, max_sentences_per_segment: int | None = None):
        self.max_sentences = int(
            max_sentences_per_segment
            or _CFG.get("ml", {}).get("segmentation", {}).get("max_sentences", 3)
        )

    def segment(self, text: str) -> List[Dict[str, Any]]:
        sentences = _split_sentences(text)
        if not sentences:
            return []
        if len(sentences) == 1:
            return [{"text": sentences[0], "sentences": sentences}]

        segments: List[Dict[str, Any]] = []
        current: List[str] = []
        for sentence in sentences:
            ends_paragraph = sentence.endswith("\n") or sentence[-1] in "!?"
            current.append(sentence)
            if len(current) >= self.max_sentences or ends_paragraph:
                segments.append({"text": " ".join(current), "sentences": current.copy()})
                current = []
        if current:
            segments.append({"text": " ".join(current), "sentences": current.copy()})

        # Merge tiny adjacent one-sentence fragments to reduce over-segmentation.
        merged: List[Dict[str, Any]] = []
        for seg in segments:
            if not merged:
                merged.append(seg)
                continue
            if len(seg["sentences"]) == 1 and len(merged[-1]["sentences"]) == 1:
                merged[-1]["text"] += " " + seg["text"]
                merged[-1]["sentences"].extend(seg["sentences"])
            else:
                merged.append(seg)
        return merged


class SegmentInference:
    """Mood-only per-segment inference."""

    def __init__(self, predictor):
        self.predictor = predictor

    def infer_segment(self, seg: Dict[str, Any]) -> Dict[str, Any]:
        text = seg.get("text", "")
        return {
            "text": text,
            "emotion_scores": predict_mood(self.predictor, text),
        }


class TrajectoryAnalyzer:
    """Detect emotional trajectory from segment mood scores."""

    def __init__(self, labels: List[str]):
        self.labels = labels

    @staticmethod
    def _entropy(probs: Dict[str, float]) -> float:
        if not probs:
            return 0.0
        arr = np.asarray([max(1e-12, float(v)) for v in probs.values()], dtype=np.float32)
        arr = arr / (arr.sum() + 1e-12)
        return float(-(arr * np.log(arr + 1e-12)).sum())

    def analyze(self, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        traj = []
        valences = []
        entropies = []

        for seg in segments:
            probs = seg.get("emotion_scores") or {}
            dom = _dominant_emotion(probs)
            traj.append(dom)
            entropies.append(self._entropy(probs))
            valences.append(_segment_valence(probs))

        trajectory = [d for d in traj if d]
        result: Dict[str, Any] = {"trajectory": trajectory}

        if len(valences) >= 2:
            start, end = valences[0], valences[-1]
            mean_val = float(np.mean(valences))
            std_val = float(np.std(valences))
            if end - start > 0.15 and mean_val > 0:
                ttype = "resolution"
            elif end - start < -0.15 and mean_val < 0:
                ttype = "escalation"
            elif std_val > 0.25:
                ttype = "oscillation"
            elif mean_val < -0.1:
                ttype = "stable_negative"
            elif mean_val > 0.1:
                ttype = "stable_positive"
            else:
                ttype = "mixed"
        else:
            if valences and valences[0] > 0:
                ttype = "stable_positive"
            elif valences and valences[0] < 0:
                ttype = "stable_negative"
            else:
                ttype = "mixed"

        result.update({
            "trajectory_type": ttype,
            "valences": valences,
            "entropies": entropies,
        })
        return result


class Aggregator:
    """Aggregate per-segment emotion probabilities into final distribution."""

    def __init__(self, labels: List[str]):
        self.labels = labels

    @staticmethod
    def _normalized_entropy(entropy: float, num_labels: int) -> float:
        if num_labels <= 1:
            return 0.0
        max_ent = math.log(num_labels + 1e-12)
        return float(entropy / (max_ent + 1e-12))

    def aggregate(self, segments: List[Dict[str, Any]], traj_meta: Dict[str, Any]) -> Tuple[Dict[str, float], float, float]:
        n = len(segments)
        if n == 0:
            return {}, 0.0, 0.0

        num_labels = len(self.labels)
        probs_mat = np.zeros((n, num_labels), dtype=np.float32)
        entropies = []
        for i, seg in enumerate(segments):
            probs = seg.get("emotion_scores") or {}
            for j, lab in enumerate(self.labels):
                probs_mat[i, j] = float(probs.get(lab, 0.0))
            arr = probs_mat[i]
            arrn = arr / (arr.sum() + 1e-12)
            ent = -float((arrn * np.log(arrn + 1e-12)).sum())
            entropies.append(ent)

        valences = traj_meta.get("valences", [])
        drift = float((valences[-1] - valences[0])) if valences else 0.0
        beta = 1.0 + min(3.0, abs(drift) * 5.0)
        recency = np.array([math.exp(beta * (i / max(1, n - 1))) for i in range(n)], dtype=np.float32)

        max_probs = probs_mat.max(axis=1)
        ent_norm = np.array([self._normalized_entropy(e, num_labels) for e in entropies], dtype=np.float32)
        salience = max_probs * (1.0 + (1.0 - ent_norm))

        weights = recency * salience
        if weights.sum() <= 0:
            weights = np.ones_like(weights)
        weights = weights / (weights.sum() + 1e-12)

        agg = (weights.reshape(-1, 1) * probs_mat).sum(axis=0)

        mean_ent = float(np.mean(entropies))
        norm_ent = self._normalized_entropy(mean_ent, num_labels)

        activity_threshold = 0.06
        per_seg_support = (probs_mat.max(axis=0) >= activity_threshold)
        agg_norm = agg / (agg.sum() + 1e-12)
        active_mask = (agg_norm >= activity_threshold) | per_seg_support
        if not active_mask.any():
            topk = np.argsort(agg_norm)[-3:]
            active_mask[topk] = True

        eps = 1e-12
        logits = np.log(np.clip(agg_norm, eps, 1.0))
        temp_range = 2.0
        T = 1.0 + (1.0 - norm_ent) * temp_range
        scaled = logits / float(max(1e-6, T))
        exp = np.exp(scaled - np.max(scaled))
        calibrated = exp / exp.sum()

        mean_peak = float(max_probs.mean())
        activation_score = float(np.clip(mean_peak * (1.0 - norm_ent), 0.0, 1.0))

        neutral_idx = None
        for idx, lab in enumerate(self.labels):
            if lab.lower() == "neutral":
                neutral_idx = idx
                break

        calibrated = calibrated.copy()
        if neutral_idx is not None and activation_score >= 0.18:
            neutral_support = agg_norm[neutral_idx]
            suppressed_neutral = neutral_support * (0.25 if neutral_support < 0.12 else 0.5)
            delta = calibrated[neutral_idx] - suppressed_neutral
            if delta > 1e-8:
                calibrated[neutral_idx] = suppressed_neutral
                redistribute_idx = np.where(active_mask)[0]
                redistribute_idx = redistribute_idx[redistribute_idx != neutral_idx]
                if redistribute_idx.size > 0:
                    masses = calibrated[redistribute_idx]
                    if masses.sum() <= 0:
                        masses = np.ones_like(masses)
                    masses = masses / masses.sum()
                    calibrated[redistribute_idx] += masses * delta

        order = np.argsort(calibrated)[::-1]
        top = order[0]
        second = order[1] if len(order) > 1 else top
        top_mass = float(calibrated[top])
        second_mass = float(calibrated[second]) if top != second else 0.0
        dominance_ratio = 2.0
        max_allowed_top = max(0.55, second_mass * dominance_ratio)
        if top_mass > max_allowed_top and activation_score >= 0.15:
            new_top = max_allowed_top
            excess = top_mass - new_top
            calibrated[top] = new_top
            redistribute_idx = np.where(active_mask)[0]
            if neutral_idx is not None and activation_score >= 0.18:
                redistribute_idx = redistribute_idx[redistribute_idx != neutral_idx]
            redistribute_idx = redistribute_idx[redistribute_idx != top]
            if redistribute_idx.size > 0:
                masses = calibrated[redistribute_idx]
                if masses.sum() <= 0:
                    masses = np.ones_like(masses)
                masses = masses / masses.sum()
                calibrated[redistribute_idx] += masses * excess

        calibrated = np.clip(calibrated, 0.0, None)
        if calibrated.sum() <= 0:
            calibrated = np.ones_like(calibrated) / calibrated.size
        else:
            calibrated = calibrated / calibrated.sum()

        probs_out = {lab: float(calibrated[j]) for j, lab in enumerate(self.labels)}
        conf_score = float((1.0 - norm_ent) * 0.6 + mean_peak * 0.4)
        complexity = float(norm_ent)
        return probs_out, conf_score, complexity


def _entropy_of(probs: dict) -> float:
    if not probs:
        return 0.0
    arr = np.array(list(probs.values()), dtype=float)
    arr = np.clip(arr, 1e-12, 1.0)
    arr = arr / arr.sum()
    return float(-np.sum(arr * np.log(arr)))


def _annotate_segment_salience(segments: List[Dict[str, Any]], traj_meta: Dict[str, Any], num_labels: int) -> float:
    """Attach salience metadata used by aggregation and journey representation."""
    n = len(segments)
    if n == 0:
        traj_meta["activation_score"] = 0.0
        return 0.0

    positions = np.arange(n) / max(1, n - 1)
    entropies = []
    peaks = []
    for seg in segments:
        probs = seg.get("emotion_scores") or {}
        entropies.append(_entropy_of(probs))
        peaks.append(max(probs.values()) if probs else 0.0)

    max_ent = math.log(max(1, num_labels) + 1e-12)
    ent_norm = [e / (max_ent + 1e-12) for e in entropies]
    valences = traj_meta.get("valences", [0.0] * n)
    volatility = [0.0] * n
    for i in range(1, n):
        volatility[i] = abs(valences[i] - valences[i - 1])

    mean_peak = float(np.mean(peaks)) if peaks else 0.0
    mean_ent_norm = float(np.mean(ent_norm)) if ent_norm else 0.0
    entry_activation = float(np.clip(mean_peak * (1.0 - mean_ent_norm), 0.0, 1.0))
    final_val = valences[-1] if valences else 0.0

    for i, seg in enumerate(segments):
        peak = peaks[i]
        e_norm = ent_norm[i]
        vol = volatility[i]
        seg_val = valences[i] if i < len(valences) else 0.0
        emotional_intensity = float(peak * (1.0 + (1.0 - e_norm)))
        trajectory_importance = float(min(1.0, vol * 3.0))
        resolution_importance = float(max(0.0, abs(final_val - seg_val)))
        narrative_salience = (
            0.55 * emotional_intensity
            + 0.20 * trajectory_importance
            + 0.15 * resolution_importance
            + 0.10 * positions[i]
        )
        seg["salience_score"] = float(narrative_salience)
        seg["emotional_intensity"] = emotional_intensity
        seg["trajectory_importance"] = trajectory_importance
        seg["resolution_importance"] = resolution_importance
        seg["narrative_salience"] = float(narrative_salience)

    traj_meta["activation_score"] = entry_activation
    return entry_activation


def _build_semantic_summaries(
    full_summary: str,
    segments: List[Dict[str, Any]],
    traj_meta: Dict[str, Any],
) -> Dict[str, str]:
    """Build schema-compatible summary artifacts without segment-level BART calls."""
    fallback_len = int(_CFG.get("app", {}).get("summary_fallback_length", 200))
    trajectory = traj_meta.get("trajectory", [])
    ttype = traj_meta.get("trajectory_type", "mixed")

    journey_labels = []
    for seg in segments:
        dom = _dominant_emotion(seg.get("emotion_scores") or {})
        if dom:
            journey_labels.append(dom)
    journey_path = " → ".join(journey_labels) if journey_labels else "unknown"
    emotional_summary = f"Emotional progression ({ttype}): {journey_path}."

    if trajectory:
        final_emotion = trajectory[-1]
        outcome_summary = f"The entry concludes with a {final_emotion} emotional tone."
    else:
        outcome_summary = full_summary[:fallback_len] + ("..." if len(full_summary) > fallback_len else "")

    return {
        "factual_summary": full_summary,
        "emotional_summary": emotional_summary,
        "outcome_summary": outcome_summary,
    }


def _build_emotional_journey(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    journey = []
    for i, seg in enumerate(segments):
        probs = seg.get("emotion_scores") or {}
        journey.append({
            "segment_index": i,
            "dominant_emotion": _dominant_emotion(probs),
            "emotion_scores": probs,
            "text_preview": (seg.get("text") or "")[:160],
        })
    return journey


def _analyze_emotional_journey(
    text: str,
    predictor,
    perf: JournalPerfLogger | None = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, float], float, float]:
    labels = predictor.labels if hasattr(predictor, "labels") else []

    if perf:
        with perf.stage("text_segmentation"):
            segmenter = Segmenter()
            segments_raw = segmenter.segment(text)
    else:
        segmenter = Segmenter()
        segments_raw = segmenter.segment(text)

    if not segments_raw:
        segments_raw = [{"text": text, "sentences": [text]}]
    if perf:
        perf.event(
            "segmentation_complete",
            segment_count=len(segments_raw),
            input_chars=len(text),
        )

    infer = SegmentInference(predictor)
    segments: List[Dict[str, Any] | None] = [None] * len(segments_raw)
    max_workers = min(8, max(2, len(segments_raw)))

    if perf:
        with perf.stage("mood_inference"):
            with ThreadPoolExecutor(max_workers=max_workers) as ex:
                future_to_idx = {ex.submit(infer.infer_segment, seg): idx for idx, seg in enumerate(segments_raw)}
                for fut in as_completed(future_to_idx):
                    idx = future_to_idx[fut]
                    try:
                        segments[idx] = fut.result()
                    except Exception:
                        logger.exception("Per-segment mood inference failed for idx=%s", idx)
                        segments[idx] = {
                            "text": segments_raw[idx].get("text", ""),
                            "emotion_scores": {},
                        }
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            future_to_idx = {ex.submit(infer.infer_segment, seg): idx for idx, seg in enumerate(segments_raw)}
            for fut in as_completed(future_to_idx):
                idx = future_to_idx[fut]
                try:
                    segments[idx] = fut.result()
                except Exception:
                    logger.exception("Per-segment mood inference failed for idx=%s", idx)
                    segments[idx] = {
                        "text": segments_raw[idx].get("text", ""),
                        "emotion_scores": {},
                    }

    segments = [s for s in segments if s is not None]
    traj = TrajectoryAnalyzer(labels)

    if perf:
        with perf.stage("trajectory_analysis"):
            traj_meta = traj.analyze(segments)
    else:
        traj_meta = traj.analyze(segments)

    num_labels = len(labels) if labels else max(1, len((segments[0].get("emotion_scores") or {})))
    _annotate_segment_salience(segments, traj_meta, num_labels)

    agg = Aggregator(labels)
    if perf:
        with perf.stage("emotion_aggregation"):
            final_probs, confidence_score, complexity_score = agg.aggregate(segments, traj_meta)
    else:
        final_probs, confidence_score, complexity_score = agg.aggregate(segments, traj_meta)

    return segments, traj_meta, final_probs, confidence_score, complexity_score


def process_entry(
    user: dict | None,
    text: str,
    predictor,
    summarizer,
    embedder=None,
    db=None,
    perf: JournalPerfLogger | None = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Run emotion journey + full-entry summary and return interpreted/raw analysis."""
    del user, embedder, db  # kept for backward-compatible call signature

    if not text or not text.strip():
        interpreted = {
            "emotional_state": {},
            "semantic_context": {},
            "temporal_context": {},
            "recommendation_strategy": {},
        }
        return interpreted, {"summary": "", "mood": {}}

    fallback_len = int(_CFG.get("app", {}).get("summary_fallback_length", 200))

    parallel_started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=2) as ex:
        emotion_future = ex.submit(_analyze_emotional_journey, text, predictor, perf)
        summary_future = ex.submit(summarize_text, summarizer, text, fallback_len, perf)
        segments, traj_meta, final_probs, confidence_score, complexity_score = emotion_future.result()
        full_summary = summary_future.result()

    if perf:
        mood_ms = sum(
            value for key, value in perf.stages.items()
            if key in {"text_segmentation", "mood_inference", "trajectory_analysis", "emotion_aggregation"}
        )
        summary_ms = perf.stages.get("summary_generation", 0.0)
        parallel_ms = (time.perf_counter() - parallel_started) * 1000
        perf.mark("parallel_analysis_wall_clock", parallel_ms)
        perf.event(
            "parallel_analysis_complete",
            mood_branch_ms=f"{mood_ms:.1f}",
            summary_branch_ms=f"{summary_ms:.1f}",
            wall_clock_ms=f"{parallel_ms:.1f}",
            theoretical_sequential_ms=f"{mood_ms + summary_ms:.1f}",
        )

    summaries = _build_semantic_summaries(full_summary, segments, traj_meta)
    emotional_journey = _build_emotional_journey(segments)

    emotional_state = {
        "dominant_mood": max(final_probs.items(), key=lambda x: x[1])[0] if final_probs else None,
        "mood_distribution": final_probs,
        "confidence_score": confidence_score,
        "emotional_complexity_score": complexity_score,
    }

    semantic_context = {"summaries": summaries}
    temporal_context = {
        "trajectory": traj_meta.get("trajectory", []),
        "trajectory_type": traj_meta.get("trajectory_type"),
        "valences": traj_meta.get("valences"),
        "emotional_journey": emotional_journey,
    }

    interpreted = {
        "emotional_state": emotional_state,
        "semantic_context": semantic_context,
        "temporal_context": temporal_context,
        "recommendation_strategy": {},
    }

    raw_analysis = {
        "summary": summaries.get("factual_summary"),
        "mood": final_probs,
        "trajectory_meta": {
            "trajectory": traj_meta.get("trajectory", []),
            "trajectory_type": traj_meta.get("trajectory_type"),
        },
        "emotional_journey": emotional_journey,
    }

    return interpreted, raw_analysis
