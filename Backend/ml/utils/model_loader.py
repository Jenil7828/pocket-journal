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

logger = logging.getLogger("pocket_journal.model_loader")

_CFG = get_config()
_STORE = _CFG["ml"]["model_store"]


def _cache_path(group: str, name: str, version: str) -> Path:
    """Return the local cache path for a model regardless of source."""
    cache_root = Path(_STORE["cache_dir"])
    return cache_root / group / name / version


def _is_cached(group: str, name: str, version: str) -> bool:
    """Return True if model exists in local cache and has config.json."""
    path = _cache_path(group, name, version)
    return path.exists() and (path / "config.json").exists()


def _download_from_gcs(group: str, name: str, version: str, dst: Path) -> None:
    """Download model from GCS bucket to local cache path."""
    from google.cloud import storage

    bucket_name = _STORE["gcs_bucket"]
    if not bucket_name:
        raise RuntimeError("MODEL_GCS_BUCKET is not set")

    prefix = f"{group}/{name}/{version}/"
    dst.mkdir(parents=True, exist_ok=True)

    logger.info("Downloading model from GCS gs://%s/%s", bucket_name, prefix)
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blobs = list(bucket.list_blobs(prefix=prefix))

    if not blobs:
        raise RuntimeError(f"No files found in GCS at gs://{bucket_name}/{prefix}")

    for blob in blobs:
        # Strip prefix to get relative filename
        relative = blob.name[len(prefix):]
        if not relative:
            continue
        dest_file = dst / relative
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        logger.info("  Downloading %s → %s", blob.name, dest_file)
        blob.download_to_filename(str(dest_file))

    logger.info("GCS download complete: %d files → %s", len(blobs), dst)


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

    if source == "gcs":
        _download_from_gcs(group, name, version, dst)
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
