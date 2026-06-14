"""
Model store loader — resolves model paths from local disk, GCS, or S3.

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
def _validate_model_store_models():
    models = _STORE.get("models", {})
    errors = []
    for key, spec in models.items():
        if not isinstance(spec, dict):
            errors.append(f"model spec for '{key}' must be a mapping/dict")
            continue
        for field in ("group", "name", "version"):
            if field not in spec or not spec[field]:
                errors.append(f"model '{key}' missing required field: {field}")
    if errors:
        raise RuntimeError("Invalid model_store.models configuration:\n  " + "\n  ".join(errors))


# Run validation immediately so startup fails fast if config malformed
_validate_model_store_models()


def _cache_path(group: str, name: str, version: str) -> Path:
    """Return the local cache path for a model regardless of source."""
    cache_root = Path(_STORE["cache_dir"])
    return cache_root / group / name / version


def _is_cached(group: str, name: str, version: str) -> bool:
    """Return True if model exists in local cache and has config.json."""
    path = _cache_path(group, name, version)
    return path.exists() and (path / "config.json").exists()


def _download_from_gcs(group: str, name: str, version: str, dst: Path) -> None:
    # GCS download functionality temporarily disabled in this build.
    # If you need GCS-based model downloads, restore the implementation below
    # (original implementation used google.cloud.storage to list and download
    # objects from the configured GCS bucket into the local cache path).
    #
    # Example (restoration hint):
    # from google.cloud import storage
    # bucket_name = _STORE["gcs_bucket"]
    # if not bucket_name:
    #     raise RuntimeError("MODEL_GCS_BUCKET is not set")
    # ...
    raise RuntimeError("GCS model downloads are disabled in this build")


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

    # GCS-based downloads are currently disabled/commented out.
    # To re-enable GCS as a model source, restore the _download_from_gcs
    # implementation above and uncomment the call below.
    # if source == "gcs":
    #     _download_from_gcs(group, name, version, dst)
    if source == "gcs":
        raise RuntimeError("MODEL_SOURCE=gcs is configured but GCS downloads are disabled in this build")
    elif source == "s3":
        _download_from_s3(group, name, version, dst)
    elif source == "local":
        _copy_from_local(group, name, version, dst)
    else:
        raise RuntimeError(f"Invalid MODEL_SOURCE={source}. Must be local | gcs | s3")

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
    """Return all model specs from config as a list of (group, name, version) tuples."""
    models = _STORE.get("models", {})
    specs = []
    for model_key, spec in models.items():
        specs.append((
            spec["group"],
            spec["name"],
            spec["version"],
        ))
    return specs


def get_model_spec(model_key: str) -> dict:
    """
    Read a model specification from configuration and validate required fields.

    Returns a dict with keys: group, name, version.
    Raises RuntimeError with a descriptive message if the model_key is missing or invalid.
    """
    models = _STORE.get("models", {})
    if model_key not in models:
        raise RuntimeError(f"Model key not found in configuration: '{model_key}'")
    spec = models[model_key]
    if not isinstance(spec, dict):
        raise RuntimeError(f"Model spec for '{model_key}' must be a mapping/dict")
    for field in ("group", "name", "version"):
        if field not in spec or not spec[field]:
            raise RuntimeError(f"Model '{model_key}' missing required field: {field}")
    # Return a shallow copy to avoid accidental mutation of config
    return {"group": spec["group"], "name": spec["name"], "version": spec["version"]}


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


