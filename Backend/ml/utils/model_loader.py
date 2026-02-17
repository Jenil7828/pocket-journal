import os
import shutil
from pathlib import Path

def ensure_model(model_group: str, model_name: str, version: str) -> str:
    """
    model_group: mood_detection | summarization
    model_name: roberta | bart
    version: v1
    """

    source = os.getenv("MODEL_SOURCE", "local")
    cache_root = Path(os.getenv("MODEL_CACHE_DIR", "/tmp/models"))
    cache_path = cache_root / model_group / model_name / version

    if cache_path.exists():
        return str(cache_path)

    cache_path.mkdir(parents=True, exist_ok=True)

    if source == "local":
        store_root = Path(os.getenv("MODEL_STORE_PATH"))
        src = store_root / model_group / model_name / version
        if not src.exists():
            raise RuntimeError(f"Model not found: {src}")

        shutil.copytree(src, cache_path, dirs_exist_ok=True)

    elif source == "gcs":
        from google.cloud import storage

        bucket_name = os.getenv("MODEL_GCS_BUCKET")
        client = storage.Client()
        bucket = client.bucket(bucket_name)

        prefix = f"{model_group}/{model_name}/{version}/"
        blobs = bucket.list_blobs(prefix=prefix)
        for blob in blobs:
            dest = cache_path / Path(blob.name).name
            blob.download_to_filename(dest)
    else:
        raise RuntimeError(f"Invalid MODEL_SOURCE={source}")
    return str(cache_path)