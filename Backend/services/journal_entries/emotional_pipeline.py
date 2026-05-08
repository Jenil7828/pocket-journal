"""
Emotional inference & narrative post-processing pipeline.

This module implements a multi-stage segmented inference pipeline that:
- dynamically segments the entry into semantically-coherent chunks using
  sentence embeddings and a single-pass centroid similarity heuristic
- runs per-segment emotion prediction, summarization and embedding
- analyzes temporal trajectory (escalation / resolution / oscillation / stable)
- aggregates per-segment probabilities with trajectory-aware, recency and
  salience weighting
- applies temperature-based calibration and smoothing to reduce overconfidence
- produces narrative-aware summaries (factual, emotional, outcome)

All heavy deps (predictor, summarizer, embedder) are accepted as call-time
objects so the module remains testable and decoupled from the rest of the
application.
"""
from __future__ import annotations

import logging
import math
import re
from typing import List, Dict, Any, Tuple

import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed

from config_loader import get_config

logger = logging.getLogger()
_CFG = get_config()


def _split_sentences(text: str) -> List[str]:
    # Lightweight sentence splitter: split on punctuation followed by space/newline
    if not text:
        return []
    # Normalize newlines
    t = text.replace("\r\n", "\n")
    # Ensure spacing after punctuation to avoid empty splits
    parts = re.split(r'(?<=[.!?\n])\s+', t)
    parts = [p.strip() for p in parts if p and len(p.strip()) > 0]
    return parts


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    if a is None or b is None or a.size == 0 or b.size == 0:
        return 0.0
    a = a.astype(np.float32)
    b = b.astype(np.float32)
    an = a / (np.linalg.norm(a) + 1e-12)
    bn = b / (np.linalg.norm(b) + 1e-12)
    return float(np.dot(an, bn))


class Segmenter:
    """Create dynamic semantic segments from an entry.

    Strategy: split into sentences, embed each sentence (batch), then perform a
    single-pass greedy segmentation where sentences are appended to the current
    segment while their embedding similarity to the current segment centroid
    remains above a threshold. The threshold is configurable and adaptive when
    the text is short.
    """

    def __init__(self, embedder, sim_threshold: float | None = None):
        self.embedder = embedder
        self.sim_threshold = float(sim_threshold or _CFG.get("ml", {}).get("segmentation", {}).get("sim_threshold", 0.72))

    def segment(self, text: str) -> List[Dict[str, Any]]:
        sentences = _split_sentences(text)
        if not sentences:
            return []

        # Batch embed sentences
        try:
            sent_embs = self.embedder.embed_texts(sentences)
        except Exception:
            # Fallback: if embedding fails, treat whole text as one segment
            logger.warning("Segmenter: embedding failed, returning single segment")
            try:
                fallback_embedding = self.embedder.embed_text(text)
            except Exception:
                logger.warning("Segmenter: fallback embedding failed, returning single segment without embedding")
                fallback_embedding = None
            return [{"text": text, "sentences": sentences, "embedding": fallback_embedding}]

        segments: List[Dict[str, Any]] = []
        cur_sentences = [sentences[0]]
        cur_count = 1
        cur_centroid = np.array(sent_embs[0], dtype=np.float32)

        for i in range(1, len(sentences)):
            emb = np.array(sent_embs[i], dtype=np.float32)
            sim = _cosine(emb, cur_centroid)
            # Heuristic: if sentence itself is very short but ends a paragraph, force break
            ends_paragraph = sentences[i].endswith("\n") or (len(sentences[i]) > 0 and sentences[i][-1] in "!?")
            threshold = self.sim_threshold
            if sim < threshold or ends_paragraph:
                # finalize current segment
                seg_text = " ".join(cur_sentences)
                segments.append({
                    "text": seg_text,
                    "sentences": cur_sentences.copy(),
                    "embedding": cur_centroid.copy(),
                })
                # start new segment
                cur_sentences = [sentences[i]]
                cur_centroid = emb.copy()
                cur_count = 1
            else:
                # append and update centroid (online average)
                cur_sentences.append(sentences[i])
                cur_count += 1
                cur_centroid = (cur_centroid * (cur_count - 1) + emb) / cur_count

        # flush last
        if cur_sentences:
            seg_text = " ".join(cur_sentences)
            segments.append({"text": seg_text, "sentences": cur_sentences.copy(), "embedding": cur_centroid.copy()})

        # If segmentation produced too many tiny segments, merge adjacent small ones
        merged = []
        for seg in segments:
            if not merged:
                merged.append(seg)
                continue
            if len(seg["sentences"]) == 1 and len(merged[-1]["sentences"]) == 1:
                # merge two one-sentence segments to avoid fragmentation
                merged[-1]["text"] += " " + seg["text"]
                merged[-1]["sentences"].extend(seg["sentences"])
                # recompute centroid
                merged[-1]["embedding"] = (merged[-1]["embedding"] + seg["embedding"]) / 2
            else:
                merged.append(seg)

        return merged


class SegmentInference:
    """Run per-segment emotion prediction, summarization, and get final embedding.

    Accepts predictor (RoBERTa), summarizer (BART) and embedder singleton.
    """

    def __init__(self, predictor, summarizer, embedder):
        self.predictor = predictor
        self.summarizer = summarizer
        self.embedder = embedder

    def infer_segment(self, seg: Dict[str, Any], summarize: bool = True) -> Dict[str, Any]:
        text = seg.get("text", "")
        # emotion prediction (RoBERTa) — operate on the segment text
        try:
            mood_result = self.predictor.predict(text)
            probs = mood_result.get("probabilities", {}) if isinstance(mood_result, dict) else mood_result
        except Exception:
            logger.warning("SegmentInference: predictor failed on segment; using empty probs")
            probs = {}

        # conditional segment summary (BART) — may be skipped for low-salience segments
        summary = ""
        if summarize and self.summarizer:
            try:
                summary = self.summarizer.summarize(text)
            except Exception:
                logger.warning("SegmentInference: summarizer failed on segment; using truncated text")
                summary = text[:200] + ("..." if len(text) > 200 else "")

        # final embedding (prefer to reuse centroid if present, otherwise compute)
        emb = seg.get("embedding")
        if emb is None or getattr(emb, "size", 0) == 0:
            try:
                emb = self.embedder.embed_text(text)
            except Exception:
                emb = np.array([], dtype=np.float32)

        return {
            "text": text,
            "summary": summary,
            "emotion_scores": probs,
            "embedding": emb.tolist() if hasattr(emb, "tolist") else emb,
        }


class TrajectoryAnalyzer:
    """Analyze sequence of segments to detect emotional trajectory.

    Uses embedding-based valence proxy (distance to small positive/negative seed vectors),
    entropy of segment predictions and probability drift to determine trajectory type.
    """

    def __init__(self, embedder, labels: List[str]):
        self.embedder = embedder
        self.labels = labels
        # precompute small positive/negative prototypes
        try:
            self.pos_proto = self.embedder.embed_text("positive resolution relief happy good")
            self.neg_proto = self.embedder.embed_text("negative anger frustration sad upset")
        except Exception:
            self.pos_proto = None
            self.neg_proto = None

    @staticmethod
    def _entropy(probs: Dict[str, float]) -> float:
        if not probs:
            return 0.0
        arr = np.asarray([max(1e-12, float(v)) for v in probs.values()], dtype=np.float32)
        arr = arr / (arr.sum() + 1e-12)
        ent = -float((arr * np.log(arr + 1e-12)).sum())
        return ent

    def analyze(self, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        traj = []
        valences = []
        entropies = []
        doms = []

        for seg in segments:
            probs = seg.get("emotion_scores") or {}
            if probs:
                # dominant emotion
                dom = max(probs.items(), key=lambda x: x[1])[0]
                doms.append(dom)
                ent = self._entropy(probs)
                entropies.append(ent)
            else:
                doms.append(None)
                entropies.append(0.0)

            # valence proxy via embedding similarity to pos/neg prototypes
            emb = np.asarray(seg.get("embedding") or [])
            if emb.size == 0 or self.pos_proto is None or self.neg_proto is None:
                val = 0.0
            else:
                pos_sim = _cosine(emb, np.asarray(self.pos_proto))
                neg_sim = _cosine(emb, np.asarray(self.neg_proto))
                val = pos_sim - neg_sim
            valences.append(val)

        # build trajectory array of dominant emotions
        traj = [d for d in doms if d]

        # basic trajectory type rules (heuristic)
        result: Dict[str, Any] = {"trajectory": traj}

        if len(valences) >= 2:
            start, end = valences[0], valences[-1]
            mean_val = float(np.mean(valences))
            std_val = float(np.std(valences))
            # Determine pattern
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
            ttype = "stable_positive" if (valences and valences[0] > 0) else "stable_negative" if (valences and valences[0] < 0) else "mixed"

        result.update({
            "trajectory_type": ttype,
            "valences": valences,
            "entropies": entropies,
        })

        return result


class Aggregator:
    """Aggregate per-segment emotion probabilities into final distribution.

    Uses trajectory-aware recency weighting, salience weighting (peak mass and low entropy),
    and temperature scaling based on final entropy to reduce overconfidence.
    """

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

        # Build matrix of probs
        num_labels = len(self.labels)
        probs_mat = np.zeros((n, num_labels), dtype=np.float32)
        entropies = []
        for i, seg in enumerate(segments):
            probs = seg.get("emotion_scores") or {}
            for j, lab in enumerate(self.labels):
                probs_mat[i, j] = float(probs.get(lab, 0.0))
            # compute entropy
            arr = probs_mat[i]
            arrn = arr / (arr.sum() + 1e-12)
            ent = -float((arrn * np.log(arrn + 1e-12)).sum())
            entropies.append(ent)

        # Recency weighting: exponential with base derived from valence drift
        valences = traj_meta.get("valences", [])
        drift = 0.0
        if valences:
            drift = float((valences[-1] - valences[0]))
        # beta grows with absolute drift magnitude (stronger narrative change -> stronger recency)
        beta = 1.0 + min(3.0, abs(drift) * 5.0)
        recency = np.array([math.exp(beta * (i / max(1, n - 1))) for i in range(n)], dtype=np.float32)

        # Salience weighting: combination of max_prob and (1 - entropy_norm)
        max_probs = probs_mat.max(axis=1)
        ent_norm = np.array([self._normalized_entropy(e, num_labels) for e in entropies], dtype=np.float32)
        salience = max_probs * (1.0 + (1.0 - ent_norm))

        weights = recency * salience
        if weights.sum() <= 0:
            weights = np.ones_like(weights)
        weights = weights / (weights.sum() + 1e-12)

        # Weighted sum
        agg = (weights.reshape(-1, 1) * probs_mat).sum(axis=0)

        # === Structure-preserving calibration (no uniform mixing) ===
        # 1) compute entry-level entropy and normalized entropy
        mean_ent = float(np.mean(entropies))
        norm_ent = self._normalized_entropy(mean_ent, num_labels)

        # 2) determine emotionally-active labels (only these receive redistributed mass)
        # active if aggregated mass or any segment supports it above a small threshold
        activity_threshold = 0.06  # label considered active if >= this mass in agg or per-segment support
        per_seg_support = (probs_mat.max(axis=0) >= activity_threshold)
        agg_norm = agg / (agg.sum() + 1e-12)
        active_mask = (agg_norm >= activity_threshold) | per_seg_support
        # Ensure at least one active label
        if not active_mask.any():
            # take top-3 labels as active to preserve structure
            topk = np.argsort(agg_norm)[-3:]
            active_mask[topk] = True

        # 3) temperature scaling via softmax-like logits (preserves relative topology)
        eps = 1e-12
        logits = np.log(np.clip(agg_norm, eps, 1.0))  # treat agg as categorical
        # Temperature increases when entropy is low (overconfident), soften peaks
        temp_range = 2.0
        T = 1.0 + (1.0 - norm_ent) * temp_range  # in [1, 1+temp_range]
        scaled = logits / float(max(1e-6, T))
        exp = np.exp(scaled - np.max(scaled))
        calibrated = exp / exp.sum()

        # 4) Emotional-activation score: how emotionally expressive the entry is
        # Use mean peak across segments and inverse normalized entropy
        mean_peak = float(max_probs.mean())
        activation_score = float(np.clip(mean_peak * (1.0 - norm_ent), 0.0, 1.0))

        # 5) Special handling for neutral: do NOT treat neutral as "uncertainty sink"
        neutral_idx = None
        for idx, lab in enumerate(self.labels):
            if lab.lower() == "neutral":
                neutral_idx = idx
                break

        calibrated = calibrated.copy()
        # If entry is emotionally active, suppress neutral unless it had genuine support
        if neutral_idx is not None and activation_score >= 0.18:
            # only keep a fraction of neutral mass proportional to its original support
            neutral_support = agg_norm[neutral_idx]
            # if neutral had little original support, force it near-zero; otherwise reduce
            if neutral_support < 0.12:
                suppressed_neutral = neutral_support * 0.25
            else:
                suppressed_neutral = neutral_support * 0.5
            delta = calibrated[neutral_idx] - suppressed_neutral
            if delta > 1e-8:
                calibrated[neutral_idx] = suppressed_neutral
                # redistribute delta among active non-neutral labels proportionally
                redistribute_idx = np.where(active_mask)[0]
                redistribute_idx = redistribute_idx[redistribute_idx != neutral_idx]
                if redistribute_idx.size > 0:
                    masses = calibrated[redistribute_idx]
                    if masses.sum() <= 0:
                        masses = np.ones_like(masses)
                    masses = masses / masses.sum()
                    calibrated[redistribute_idx] += masses * delta

        # 6) Dominance balancing: reduce excessive single-label peaks while preserving secondaries
        # Identify top and second
        order = np.argsort(calibrated)[::-1]
        top = order[0]
        second = order[1] if len(order) > 1 else top
        top_mass = float(calibrated[top])
        second_mass = float(calibrated[second]) if top != second else 0.0
        # If top is disproportionately large compared to second and entry is not low-activation,
        # clip it toward a reasonable bound and redistribute excess among active labels (excluding neutral if active)
        dominance_ratio = 2.0
        max_allowed_top = max(0.55, second_mass * dominance_ratio)
        if top_mass > max_allowed_top and activation_score >= 0.15:
            new_top = max_allowed_top
            excess = top_mass - new_top
            calibrated[top] = new_top
            # redistribute excess to other active labels (exclude neutral when activation high)
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

        # 7) Final renormalize and ensure numeric stability
        calibrated = np.clip(calibrated, 0.0, None)
        if calibrated.sum() <= 0:
            calibrated = np.ones_like(calibrated) / calibrated.size
        else:
            calibrated = calibrated / calibrated.sum()

        # Build output dict preserving label ordering
        probs_out = {lab: float(calibrated[j]) for j, lab in enumerate(self.labels)}

        # Confidence score: combine inverse entropy and mean peak
        max_mass = float(calibrated.max()) if calibrated.size else 0.0
        conf_score = float((1.0 - norm_ent) * 0.6 + mean_peak * 0.4)
        complexity = float(norm_ent)

        return probs_out, float(conf_score), float(complexity)


class NarrativeSummarizer:
    """Build factual, emotional and outcome summaries from segment outputs.

    Uses chunk summaries and trajectory to produce three complementary summaries.
    """

    def __init__(self, summarizer):
        self.summarizer = summarizer

    def build(self, full_text: str, segments: List[Dict[str, Any]], traj_meta: Dict[str, Any]) -> Dict[str, str]:
        # New narrative synthesis pipeline:
        # 1) Select top-K salient segments (assumes segments already have 'salience_score' if computed)
        try:
            top_k = min(6, max(1, int(_CFG.get("app", {}).get("narrative_top_k", 5))))
        except Exception:
            top_k = 5

        # Order segments by narrative_salience (computed earlier). Fallback to salience_score then position
        def seg_score(i, s):
            return float(s.get("narrative_salience", s.get("salience_score", 0.0)))

        scored = [(i, seg_score(i, s)) for i, s in enumerate(segments)]
        scored.sort(key=lambda x: x[1], reverse=True)
        top_idxs = [i for i, _ in scored[:top_k]]
        # For factual synthesis keep chronological order of selected segments
        top_idxs_sorted = sorted(top_idxs)

        # Helper: sanitize text to remove timestamps and low-value tokens that bias summarizer
        def _sanitize(t: str) -> str:
            if not t:
                return ""
            # remove common time patterns like '8:30 a.m.', '1 p.m.', '13:00'
            t = re.sub(r"\b\d{1,2}:\d{2}\s*(am|pm|a\.m\.|p\.m\.)?\b", "", t, flags=re.I)
            t = re.sub(r"\b\d{1,2}\s*(am|pm|a\.m\.|p\.m\.)\b", "", t, flags=re.I)
            # remove isolated dates like 'on the 7th' or numeric day mentions
            t = re.sub(r"\b(on the )?\d{1,2}(st|nd|rd|th)?\b", "", t, flags=re.I)
            # collapse multiple spaces
            t = re.sub(r"\s+", " ", t).strip()
            return t

        # factual: build emotionally-focused factual input from top segments
        pieces = []
        for i in top_idxs_sorted:
            s = segments[i]
            summary = s.get("summary") or s.get("text")[:400]
            dom = None
            probs = s.get("emotion_scores") or {}
            if probs:
                dom = max(probs.items(), key=lambda kv: kv[1])[0]
            short = _sanitize(str(summary))
            meta = []
            if dom:
                meta.append(f"dominant_emotion={dom}")
            intensity = s.get("emotional_intensity")
            if intensity is not None:
                meta.append(f"intensity={int(round(float(intensity), 2))}")
            pieces.append(f"HIGHLIGHT {i} [{', '.join(meta)}]: {short}")

        factual_input = "\n\n".join(pieces) if pieces else _sanitize(full_text)[:_CFG.get("app", {}).get("summary_fallback_length", 200)]
        try:
            factual = self.summarizer.summarize(factual_input)
        except Exception:
            factual = factual_input[:_CFG.get("app", {}).get("summary_fallback_length", 200)]

        # emotional: interpret trajectory and produce a reflective emotional narrative
        traj = traj_meta.get("trajectory", [])
        ttype = traj_meta.get("trajectory_type")
        activation = float(traj_meta.get("activation_score", 0.0))

        # Build an interpretable emotional prompt: include top emotional highlights (by intensity)
        top_emotional = [i for i, _ in sorted([(i, s.get("emotional_intensity", 0.0)) for i, s in enumerate(segments)], key=lambda x: x[1], reverse=True)[:3]]
        emo_pieces = []
        for idx in top_emotional:
            s = segments[idx]
            dom = None
            probs = s.get("emotion_scores") or {}
            if probs:
                dom = max(probs.items(), key=lambda kv: kv[1])[0]
            short = _sanitize(s.get("summary") or s.get("text")[:200])
            emo_pieces.append(f"Segment {idx} felt {dom if dom else 'mixed'}: {short}")

        emo_base = f"Interpretation: trajectory_type={ttype}; activation={round(activation,2)}; path={' -> '.join(traj) if traj else 'unknown'}. Highlights:\n" + "\n".join(emo_pieces)
        try:
            emotional = self.summarizer.summarize(emo_base)
        except Exception:
            emotional = emo_base

        # outcome: emphasize resolution and final state without factual timestamps
        if segments:
            last = segments[-1]
            last_summary = _sanitize(last.get("summary") or last.get("text")[:300])
            final_dom = None
            if last.get("emotion_scores"):
                final_dom = max(last.get("emotion_scores").items(), key=lambda x: x[1])[0]
            outcome_base = f"Final emotional state: {final_dom if final_dom else 'unknown'}. {last_summary}"
        else:
            outcome_base = factual
        try:
            outcome = self.summarizer.summarize(outcome_base)
        except Exception:
            outcome = outcome_base

        return {
            "factual_summary": factual,
            "emotional_summary": emotional,
            "outcome_summary": outcome,
        }


def process_entry(user: dict | None, text: str, predictor, summarizer, embedder, db=None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Run the full pipeline and return interpreted_response and raw_analysis.

    interpreted_response: hierarchical structure suitable for DBManager.insert_analysis
    raw_analysis: raw outputs (segment-level) for debugging and storage
    """
    if not text or not text.strip():
        interpreted = {"emotional_state": {}, "semantic_context": {}, "temporal_context": {}, "recommendation_strategy": {}}
        return interpreted, {"summary": "", "mood": {}}

    # 1. Segment
    seg = Segmenter(embedder)
    segments_raw = seg.segment(text)
    # If segmentation failed, fall back to single chunk
    if not segments_raw:
        segments_raw = [{"text": text, "sentences": [text], "embedding": embedder.embed_text(text)}]

    # 2. Per-segment inference (parallelized) - initially skip summarization
    infer = SegmentInference(predictor, summarizer, embedder)
    segments = [None] * len(segments_raw)
    max_workers = min(8, max(2, len(segments_raw)))
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        future_to_idx = {ex.submit(infer.infer_segment, s, False): idx for idx, s in enumerate(segments_raw)}
        for fut in as_completed(future_to_idx):
            idx = future_to_idx[fut]
            try:
                res = fut.result()
            except Exception:
                logger.exception("Per-segment inference failed for idx=%s", idx)
                res = {"text": segments_raw[idx].get("text", ""), "summary": "", "emotion_scores": {}, "embedding": segments_raw[idx].get("embedding", [])}
            segments[idx] = res

    # 3. Trajectory analysis (initial) to compute valence progression and volatility
    traj = TrajectoryAnalyzer(embedder, predictor.labels if hasattr(predictor, "labels") else [])
    traj_meta = traj.analyze(segments)

    # 4. Salience scoring: compute per-segment salience and selectively summarize top segments
    num_labels = len(predictor.labels) if hasattr(predictor, "labels") else None
    # derive label count if missing
    if num_labels is None and segments:
        first_probs = segments[0].get("emotion_scores") or {}
        num_labels = max(1, len(first_probs))

    # helper entropy
    def _entropy_of(probs: dict) -> float:
        if not probs:
            return 0.0
        arr = np.array(list(probs.values()), dtype=float)
        arr = np.clip(arr, 1e-12, 1.0)
        arr = arr / arr.sum()
        return float(-np.sum(arr * np.log(arr)))

    n = len(segments)
    positions = np.arange(n) / max(1, n - 1)
    entropies = []
    peaks = []
    peak_labels = []
    for i, s in enumerate(segments):
        probs = s.get("emotion_scores") or {}
        ent = _entropy_of(probs)
        entropies.append(ent)
        if probs:
            lab, val = max(probs.items(), key=lambda kv: kv[1])
            peaks.append(val)
            peak_labels.append(lab)
        else:
            peaks.append(0.0)
            peak_labels.append(None)

    # normalized entropy
    max_ent = math.log(max(1, num_labels) + 1e-12)
    ent_norm = [e / (max_ent + 1e-12) for e in entropies]

    # valence volatility from traj_meta
    valences = traj_meta.get("valences", [0.0] * n)
    volatility = [0.0] * n
    for i in range(1, n):
        volatility[i] = abs(valences[i] - valences[i - 1])

    # compute salience per segment with richer metadata (intensity, trajectory importance, resolution importance)
    salience_scores = []
    recency_alpha = float(_CFG.get("ml", {}).get("salience", {}).get("recency_alpha", 1.0))
    # entry-level stats for activation
    mean_peak = float(np.mean(peaks)) if peaks else 0.0
    mean_ent_norm = float(np.mean(ent_norm)) if ent_norm else 0.0
    entry_activation = float(np.clip(mean_peak * (1.0 - mean_ent_norm), 0.0, 1.0))

    final_val = valences[-1] if valences else 0.0
    for i in range(n):
        peak = peaks[i]
        e_norm = ent_norm[i]
        recency = positions[i]
        vol = volatility[i]
        # emotional_intensity: peak scaled by inverse entropy
        emotional_intensity = float(peak * (1.0 + (1.0 - e_norm)))
        # trajectory_importance: local volatility (how much this seg changes valence relative to neighbours)
        trajectory_importance = float(min(1.0, vol * 3.0))
        # resolution_importance: how much this segment moves toward final state (positive value if moving toward final_val)
        seg_val = valences[i] if i < len(valences) else 0.0
        resolution_importance = float(max(0.0, abs(final_val - seg_val)))
        # combine into narrative salience (weights are tunable)
        narrative_salience = (
            0.55 * emotional_intensity + 0.20 * trajectory_importance + 0.15 * resolution_importance + 0.10 * recency
        )
        narrative_salience = float(narrative_salience)
        salience_scores.append(narrative_salience)
        segments[i]["salience_score"] = float(narrative_salience)
        segments[i]["emotional_intensity"] = float(emotional_intensity)
        segments[i]["trajectory_importance"] = float(trajectory_importance)
        segments[i]["resolution_importance"] = float(resolution_importance)
        segments[i]["narrative_salience"] = float(narrative_salience)

    # attach activation to trajectory meta for downstream summarizer
    traj_meta["activation_score"] = entry_activation

    # choose top-K segments to summarize (always include last segment)
    try:
        top_k = int(_CFG.get("app", {}).get("narrative_top_k", 5))
    except Exception:
        top_k = 5
    idxs_sorted_by_sal = sorted(range(n), key=lambda i: salience_scores[i], reverse=True)
    selected = set(idxs_sorted_by_sal[:top_k])
    selected.add(n - 1)  # always include final segment
    # also include any high-volatility pivots
    for i, v in enumerate(volatility):
        if v > 0.25:
            selected.add(i)

    # 5. Selective summarization (parallel)
    with ThreadPoolExecutor(max_workers=min(6, max(1, len(selected)))) as ex:
        futs = {ex.submit(summarizer.summarize, segments[i]["text"]): i for i in selected}
        for fut in as_completed(futs):
            i = futs[fut]
            try:
                segments[i]["summary"] = fut.result()
            except Exception:
                logger.exception("Failed to summarize segment %s", i)
                segments[i]["summary"] = segments[i]["text"][:200] + ("..." if len(segments[i]["text"]) > 200 else "")

    # ensure non-selected have short excerpt only (avoid heavy summaries)
    for i in range(n):
        if "summary" not in segments[i] or not segments[i]["summary"]:
            text = segments[i].get("text", "")
            segments[i]["summary"] = text[:120] + ("..." if len(text) > 120 else "")

    # 6. Re-run trajectory analysis (optional refinement) using summaries/updated data
    traj_meta = traj.analyze(segments)

    # 7. Aggregation and calibration
    agg = Aggregator(predictor.labels if hasattr(predictor, "labels") else [])
    final_probs, confidence_score, complexity_score = agg.aggregate(segments, traj_meta)

    # 8. Narrative summaries (synthesis)
    narr = NarrativeSummarizer(summarizer)
    summaries = narr.build(text, segments, traj_meta)

    # build interpreted response
    emotional_state = {
        "dominant_mood": max(final_probs.items(), key=lambda x: x[1])[0] if final_probs else None,
        "mood_distribution": final_probs,
        "confidence_score": confidence_score,
        "emotional_complexity_score": complexity_score,
    }

    # Persist only lightweight semantic context (do NOT persist per-segment raw inference or embeddings)
    semantic_context = {
        "summaries": summaries,
    }

    temporal_context = {
        "trajectory": traj_meta.get("trajectory", []),
        "trajectory_type": traj_meta.get("trajectory_type"),
        "valences": traj_meta.get("valences"),
    }

    interpreted = {
        "emotional_state": emotional_state,
        "semantic_context": semantic_context,
        "temporal_context": temporal_context,
        "recommendation_strategy": {},
    }

    # Raw analysis returned to caller (kept small to avoid persisting heavy internal state).
    # Do NOT include embeddings, segment vectors or full per-segment inference.
    raw_analysis = {
        "summary": summaries.get("factual_summary"),
        "mood": final_probs,
        "trajectory_meta": {
            "trajectory": traj_meta.get("trajectory", []),
            "trajectory_type": traj_meta.get("trajectory_type"),
        },
    }

    return interpreted, raw_analysis









