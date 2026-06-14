"""
Model store loader — resolves model paths from local disk or S3.

Used by all inference predictors instead of hardcoded paths.
Called at container startup via download_models.py before Flask or
the ML worker starts accepting work.

Usage in predictors:
    from ml.utils.model_loader import resolve_model_path
    model_path = resolve_model_path("mood_detection", "roberta", "v2")
    # Returns local cache path — model is guaranteed to exist there
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Optional

from config_loader import get_config

logger = logging.getLogger()

_CFG = get_config()
_STORE = _CFG["ml"]["model_store"]


# Validate model specs at import-time to fail fast on misconfiguration
def _validate_authoritative_model_entries():
    """
    Validate the authoritative per-group configuration for required models.
    This repository uses ml.mood_detection and ml.summarization as the source
    of truth for model_name and model_version. Fail fast if missing.
    """
    ml_cfg = _CFG.get("ml", {}) or {}
    missing = []
    for group in ("mood_detection", "summarization"):
        gcfg = ml_cfg.get(group, {}) or {}
        if not gcfg.get("model_name"):
            missing.append(f"ml.{group}.model_name")
        if not gcfg.get("model_version"):
            missing.append(f"ml.{group}.model_version")

    if missing:
        raise RuntimeError("Missing required model configuration:\n  " + "\n  ".join(missing))


# Run authoritative validation immediately so startup fails fast on misconfiguration
_validate_authoritative_model_entries()


def _cache_path(group: str, name: str, version: str) -> Path:
    """Return the local cache path for a model regardless of source."""
    cache_root = Path(_STORE["cache_dir"])
    return cache_root / group / name / version


def _is_cached(group: str, name: str, version: str) -> bool:
    """Return True if model exists in local cache and has config.json."""
    path = _cache_path(group, name, version)
    return path.exists() and (path / "config.json").exists()


def _download_from_s3(group: str, name: str, version: str, dst: Path) -> None:
    """Download model from S3 bucket to local cache path."""
    import boto3

    bucket_name = _STORE["s3_bucket"]
    region = _STORE["s3_region"]
    if not bucket_name:
        raise RuntimeError("MODEL_S3_BUCKET is not set")

    prefix = f"{group}/{name}/{version}/"
    dst.mkdir(parents=True, exist_ok=True)

    logger.info("Downloading model from S3 s3://%s/%s", bucket_name, prefix)
    s3 = boto3.client("s3", region_name=region)
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

    count = 0
    for page in pages:
        for obj in page.get("Contents", []):
            key = obj["Key"]
            relative = key[len(prefix):]
            if not relative:
                continue
            dest_file = dst / relative
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            logger.info("  Downloading %s → %s", key, dest_file)
            s3.download_file(bucket_name, key, str(dest_file))
            count += 1

    if count == 0:
        raise RuntimeError(f"No files found in S3 at s3://{bucket_name}/{prefix}")

    logger.info("S3 download complete: %d files → %s", count, dst)


def _copy_from_local(group: str, name: str, version: str, dst: Path) -> None:
    """Copy model from local MODEL_STORE_PATH to cache directory."""
    store_root = Path(_STORE["local_path"])
    if not store_root or not store_root.exists():
        raise RuntimeError(
            f"MODEL_STORE_PATH is not set or does not exist: {store_root}"
        )
    src = store_root / group / name / version
    if not src.exists():
        raise RuntimeError(f"Model not found at local path: {src}")

    dst.mkdir(parents=True, exist_ok=True)
    logger.info("Copying model from local %s → %s", src, dst)
    shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
    logger.info("Local copy complete → %s", dst)


def ensure_model(group: str, name: str, version: str) -> str:
    """
    Ensure model exists in local cache. Download if missing.
    Returns the local cache path as a string.

    This is the main entry point for all predictors.
    Call this instead of hardcoding model paths.

    Example:
        path = ensure_model("mood_detection", "roberta", "v2")
        model = AutoModel.from_pretrained(path)
    """
    if _is_cached(group, name, version):
        path = _cache_path(group, name, version)
        logger.info("Model cache hit: %s/%s/%s → %s", group, name, version, path)
        return str(path)

    dst = _cache_path(group, name, version)
    source = _STORE["source"]

    logger.info(
        "Model cache miss: %s/%s/%s — downloading from source=%s",
        group, name, version, source
    )

    if source == "s3":
        _download_from_s3(group, name, version, dst)
    elif source == "local":
        _copy_from_local(group, name, version, dst)
    else:
        raise RuntimeError(
            "Invalid MODEL_SOURCE. Supported values: local, s3"
        )

    if not _is_cached(group, name, version):
        raise RuntimeError(
            f"Model download appeared to succeed but config.json not found at {dst}"
        )

    logger.info("Model ready at %s", dst)
    return str(dst)


def resolve_model_path(group: str, name: str, version: str) -> str:
    """
    Alias for ensure_model — more readable name for use in predictors.
    Returns local cache path, downloading if necessary.
    """
    return ensure_model(group, name, version)


def get_all_model_specs() -> list:
    """
    Return all model specs derived from authoritative per-group config.

    Only include groups that are considered models that the startup downloader
    should manage. Embedding is intentionally omitted (handled by
    sentence-transformers at runtime).
    """
    specs: list = []
    # Read model entries from the authoritative model_store configuration.
    # Each model entry maps an arbitrary key (e.g., 'roberta', 'bart') to a
    # spec containing group/name/version which determines where artifacts are
    # stored in the model store (local path or S3).
    models = _STORE.get("models", {}) or {}
    for key, spec in models.items():
        group = spec.get("group")
        name = spec.get("name")
        version = spec.get("version")
        if not group or not name or not version:
            logger.warning("Skipping invalid model_store entry %s: %s", key, spec)
            continue
        logger.info(
            "Model spec resolved: %s/%s/%s",
            group,
            name,
            version,
        )
        specs.append((group, name, version))
    return specs


def get_model_spec(model_key: str) -> dict:
    """
    Read a model specification from the model_store configuration and validate fields.

    model_key refers to the key under `ml.model_store.models` (e.g. 'roberta' or 'bart').
    Returns a dict with keys: group, name, version.
    Raises RuntimeError with a descriptive message if the model_key is missing or invalid.
    """
    models = _STORE.get("models", {}) or {}

    # Backwards-compatible path: allow direct model key lookup (e.g., 'roberta')
    if model_key in models:
        spec = models.get(model_key, {}) or {}
        group = spec.get("group")
        name = spec.get("name")
        version = spec.get("version")
        if not group or not name or not version:
            raise RuntimeError(f"Invalid model_store entry for '{model_key}': {spec}")
        return {"group": group, "name": name, "version": version}

    # Primary lookup: find the model whose spec['group'] matches model_key
    for key, spec in models.items():
        if not spec:
            continue
        if spec.get("group") == model_key:
            group = spec.get("group")
            name = spec.get("name")
            version = spec.get("version")
            if not group or not name or not version:
                raise RuntimeError(f"Invalid model_store entry for '{key}': {spec}")
            return {"group": group, "name": name, "version": version}

    # Nothing matched
    raise RuntimeError(
        f"Model key not found in model_store.models (neither as key nor as group): '{model_key}'"
    )


def resolve_model_from_config(model_key: str) -> str:
    """
    Resolve a model path using the model specification stored in configuration.

    Example:
        path = resolve_model_from_config("mood_detection")

    This is a convenience wrapper that reads the model spec via get_model_spec()
    and then delegates to resolve_model_path()/ensure_model().
    """
    spec = get_model_spec(model_key)
    return resolve_model_path(spec["group"], spec["name"], spec["version"])


