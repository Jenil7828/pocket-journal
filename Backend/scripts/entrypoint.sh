#!/bin/bash
set -e

echo "[entrypoint] Starting Pocket Journal container"
echo "[entrypoint] MODEL_SOURCE=${MODEL_SOURCE}"
echo "[entrypoint] MODEL_CACHE_DIR=${MODEL_CACHE_DIR}"

# Step 1: Download models from configured source
echo "[entrypoint] Downloading models..."
python3 /app/scripts/download_models.py

# Step 2: Start the application
echo "[entrypoint] Models ready — starting application"
exec gunicorn -w 1 --threads 4 -b 0.0.0.0:8080 --worker-tmp-dir /tmp/gunicorn app:app


