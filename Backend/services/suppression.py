"""Minimal suppression context manager for Hugging Face/Transformers materialization output.

Usage:
    from services.suppression import suppress_hf
    with suppress_hf():
        # call model.from_pretrained, SentenceTransformer(...), model.encode(...)

This implementation intentionally avoids low-level file descriptor manipulation (os.dup/os.dup2/os.close)
so it is safe on Windows and in environments where duplicating fds can fail. It uses Python-level
contextlib.redirect_stdout/redirect_stderr to silence noisy HF progress output only while inside the
context manager. Environment variables are set temporarily to reduce HF/Transformers verbosity. The
context does NOT permanently change global stdout/stderr or logging configuration.
"""
from __future__ import annotations

import contextlib
import os
import sys
import logging
from typing import Optional

logger = logging.getLogger("pocket_journal.suppression")


class suppress_hf:
    def __init__(self):
        # Keep track of env vars we change so we can restore them
        self._old_env = {}
        self._env_updates = {
            "TRANSFORMERS_NO_TQDM": "1",
            "HF_DISABLE_TQDM": "1",
            "HF_HUB_DISABLE_PROGRESS": "1",
            "HF_HUB_DISABLE_TELEMETRY": "1",
            "TRANSFORMERS_VERBOSITY": "error",
            # keep compatibility with other flags
        }
        # We'll also ensure this extra opt-out is set where requested by the app
        self._extra = {"HF_HUB_DISABLE_XET": "1"}

        self._stdout_cm = None
        self._stderr_cm = None
        self._devnull = None
        self._old_tqdm = None
        self._old_hf_level = None

    def __enter__(self):
        # Set env vars
        for k, v in {**self._env_updates, **self._extra}.items():
            self._old_env[k] = os.environ.get(k)
            os.environ[k] = v

        # Redirect Python-level stdout/stderr to devnull for the duration
        self._devnull = open(os.devnull, "w")
        self._stdout_cm = contextlib.redirect_stdout(self._devnull)
        self._stderr_cm = contextlib.redirect_stderr(self._devnull)
        self._stdout_cm.__enter__()
        self._stderr_cm.__enter__()

        # Monkeypatch tqdm.tqdm to a no-op to prevent progress bars from printing
        try:
            import tqdm

            self._old_tqdm = getattr(tqdm, "tqdm", None)

            class _DummyTqdm:
                def __init__(self, *a, **k):
                    pass

                def __iter__(self):
                    return iter(())

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return False

                def update(self, *a, **k):
                    pass

                def close(self):
                    pass

            tqdm.tqdm = lambda *a, **k: _DummyTqdm()
        except Exception:
            self._old_tqdm = None

        # Lower transformers verbosity (best-effort)
        try:
            import transformers
            from transformers import logging as _hf_logging

            try:
                # some HF versions expose this API
                self._old_hf_level = _hf_logging.get_verbosity()
                _hf_logging.set_verbosity_error()
            except Exception:
                try:
                    transformers.utils.logging.set_verbosity_error()
                except Exception:
                    self._old_hf_level = None
        except Exception:
            self._old_hf_level = None

        return self

    def __exit__(self, exc_type, exc, tb):
        # Restore transformers verbosity
        try:
            if self._old_hf_level is not None:
                from transformers import logging as _hf_logging

                try:
                    _hf_logging.set_verbosity(self._old_hf_level)
                except Exception:
                    pass
        except Exception:
            pass

        # Restore tqdm
        try:
            if self._old_tqdm is not None:
                import tqdm

                tqdm.tqdm = self._old_tqdm
        except Exception:
            pass

        # Restore Python-level stdout/stderr
        try:
            if self._stderr_cm is not None:
                self._stderr_cm.__exit__(exc_type, exc, tb)
            if self._stdout_cm is not None:
                self._stdout_cm.__exit__(exc_type, exc, tb)
        except Exception:
            pass

        # Close devnull
        try:
            if self._devnull:
                self._devnull.close()
        except Exception:
            pass

        # Restore env vars
        for k, old in self._old_env.items():
            if old is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = old


__all__ = ["suppress_hf"]

