#!/usr/bin/env python3
"""
Download all models from the configured model store to local cache.
Runs at container startup before Flask or ML worker starts.

Usage (called automatically from Docker entrypoint):
    python Backend/scripts/download_models.py

Can also be run manually to pre-warm the cache:
    MODEL_SOURCE=gcs MODEL_GCS_BUCKET=my-bucket python Backend/scripts/download_models.py
"""

import logging
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_BACKEND = _HERE.parent
sys.path.insert(0, str(_BACKEND))

logging.basicConfig(
    level="INFO",
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger()

from config_loader import get_config
from ml.utils.model_loader import ensure_model, get_all_model_specs

_CFG = get_config()
_STORE = _CFG["ml"]["model_store"]

# Groups to skip — these are loaded automatically at runtime
SKIP_GROUPS = {"embedding"}  # sentence-transformers handles embedding model downloads automatically


def main():
    if not _STORE.get("download_on_startup", True):
        logger.info("MODEL_DOWNLOAD_ON_STARTUP=false — skipping model download")
        return

    source = _STORE["source"]
    cache_dir = _STORE["cache_dir"]
    specs = get_all_model_specs()

    logger.info("Model store startup download")
    logger.info("  source:    %s", source)
    logger.info("  cache_dir: %s", cache_dir)
    logger.info("  models:    %d", len(specs))

    if source == "gcs" and not _STORE.get("gcs_bucket"):
        logger.error("MODEL_SOURCE=gcs but MODEL_GCS_BUCKET is not set")
        sys.exit(1)

    if source == "s3" and not _STORE.get("s3_bucket"):
        logger.error("MODEL_SOURCE=s3 but MODEL_S3_BUCKET is not set")
        sys.exit(1)

    failed = []
    for group, name, version in specs:
        if group in SKIP_GROUPS:
            logger.info(
                "  ⊘ %s/%s/%s — skipped (loaded automatically at runtime)",
                group, name, version
            )
            continue
        start = time.time()
        try:
            path = ensure_model(group, name, version)
            duration = time.time() - start
            logger.info("  ✓ %s/%s/%s → %s (%.1fs)", group, name, version, path, duration)
        except Exception as e:
            duration = time.time() - start
            logger.error("  ✗ %s/%s/%s FAILED: %s (%.1fs)", group, name, version, str(e), duration)
            failed.append(f"{group}/{name}/{version}")

    if failed:
        logger.error("Failed to download models: %s", failed)
        logger.error("Container will not start until all models are available")
        sys.exit(1)

    logger.info("All models ready — container startup can proceed")


if __name__ == "__main__":
    main()




