"""Structured performance instrumentation for journal processing."""
from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Dict

logger = logging.getLogger()


class JournalPerfLogger:
    """Collects per-stage timings for journal create/analysis flows."""

    def __init__(self, entry_id: str = "", uid: str = ""):
        self.entry_id = entry_id or ""
        self.uid = uid or ""
        self._started_at = time.perf_counter()
        self.stages: Dict[str, float] = {}

    def _prefix(self) -> str:
        parts = ["[PERF][journal]"]
        if self.entry_id:
            parts.append(f"entry_id={self.entry_id}")
        if self.uid:
            parts.append(f"uid={self.uid}")
        return " ".join(parts)

    @contextmanager
    def stage(self, name: str):
        started = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            self.stages[name] = elapsed_ms
            logger.info("%s stage=%s duration_ms=%.1f", self._prefix(), name, elapsed_ms)

    def mark(self, name: str, duration_ms: float) -> None:
        self.stages[name] = duration_ms
        logger.info("%s stage=%s duration_ms=%.1f", self._prefix(), name, duration_ms)

    def event(self, name: str, **fields) -> None:
        extras = " ".join(f"{key}={value}" for key, value in fields.items())
        logger.info("%s event=%s %s", self._prefix(), name, extras.strip())

    def finish(self, label: str = "total_request") -> float:
        total_ms = (time.perf_counter() - self._started_at) * 1000
        self.stages[label] = total_ms
        breakdown = " ".join(f"{key}={value:.1f}ms" for key, value in sorted(self.stages.items()))
        logger.info("%s event=pipeline_complete %s", self._prefix(), breakdown)
        return total_ms
