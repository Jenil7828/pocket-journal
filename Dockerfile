# Multi-stage Dockerfile for Pocket Journal
# Stages:
# 1) deps    - build wheels from Backend/requirements.txt (cached)
# 2) trainer - install from wheels, run training (must succeed), emit deterministic artifacts
# 3) runtime - install from wheels, copy only runtime code + artifacts, run Gunicorn as non-root

# Multi-stage Dockerfile tailored to the repository layout
# Stages:
#   1. deps    - build wheels from Backend/requirements.txt (cacheable)
#   2. trainer - install from wheels, optionally run training at build-time (off by default)
#   3. runtime - minimal runtime image with only runtime code + trained models

############################
# Stage 1 — deps: build wheels (cache invalidates only when requirements change)
############################
FROM python:3.11-slim AS deps

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ARG DEBIAN_FRONTEND=noninteractive

# Install only the system packages required to build wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        git \
        curl \
        ca-certificates \
        libffi-dev \
        libssl-dev \
        libpq-dev \
        python3-dev \
        && rm -rf /var/lib/apt/lists/*

WORKDIR /wheels

# Copy only the requirements file to leverage layer caching: this layer is rebuilt
# only when Backend/requirements.txt changes.
COPY Backend/requirements.txt ./requirements.txt

# Build wheels for all Python dependencies into /wheels
RUN python -m pip install --upgrade pip setuptools wheel && \
        mkdir -p /wheels/dist && \
        pip wheel --no-cache-dir --wheel-dir /wheels/dist -r requirements.txt


############################
# Stage 2 — trainer: install from wheels and optionally train at build time
############################
FROM python:3.11-slim AS trainer

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ENV ARTIFACT_DIR=/src/Backend/Mood_Detection/outputs/models
WORKDIR /src

# Copy built wheels and the requirements file (so installs come from wheels only)
COPY --from=deps /wheels/dist /wheels
COPY Backend/requirements.txt /src/Backend/requirements.txt

# Create a venv and install dependencies strictly from the prebuilt wheels (no network)
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --upgrade pip setuptools wheel && \
        /opt/venv/bin/pip install --no-index --find-links /wheels -r /src/Backend/requirements.txt

ENV PATH="/opt/venv/bin:$PATH"

# Copy application source code for training and artifact packaging. Training scripts
# will not be copied into the final runtime image; a runtime-only tar is produced below.
COPY . /src

# Ensure artifact dir exists (deterministic path)
RUN mkdir -p ${ARTIFACT_DIR}

# Training is optional and controlled with build-arg TRAIN (default: "false").
# On Render free tier, builds should skip training by default.
ARG TRAIN=false
ARG TRAIN_SCRIPT=Backend/Mood_Detection/mood_detection_roberta/train.py

# If TRAIN=true, require the training script to exist and run it. Any failure here
# must fail the Docker build (no silent failures). If TRAIN is not "true", skip training.
RUN if [ "${TRAIN}" = "true" ]; then \
            if [ -f "${TRAIN_SCRIPT}" ]; then \
                python "${TRAIN_SCRIPT}" --output_dir "${ARTIFACT_DIR}"; \
            else \
                echo "Training requested but script not found: ${TRAIN_SCRIPT}" >&2; exit 1; \
            fi; \
        else \
            echo "TRAIN build-arg not set to 'true'; skipping training."; \
        fi

# Package artifacts (if any) into a deterministic tarball for copying into runtime
RUN if [ -d "${ARTIFACT_DIR}" ] && [ "$(ls -A ${ARTIFACT_DIR})" ]; then \
            tar -C "${ARTIFACT_DIR}" -czf /artifacts.tar.gz .; \
        else \
            # create an empty deterministic tarball when artifacts are absent
            mkdir -p /empty && printf '' > /empty/.empty && tar -C /empty -czf /artifacts.tar.gz .; \
        fi

# Create a runtime-only application tarball that excludes training code so the final
# image never contains training scripts or large training-related folders.
RUN tar -C /src -czf /app_runtime.tar.gz Backend app.py --exclude='Backend/Mood_Detection/mood_detection_roberta' --exclude='Backend/Mood_Detection/mood_detection_roberta/*'


############################
# Stage 3 — runtime: minimal final image for serving
############################
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 FLASK_ENV=production FLASK_DEBUG=0 PORT=8080
ARG APP_USER=app

# Minimal OS packages
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install runtime dependencies from the prebuilt wheels; do this before copying app
# code so dependency layers remain cacheable and are not invalidated by app changes.
COPY --from=deps /wheels/dist /wheels
COPY Backend/requirements.txt /tmp/requirements.txt

# Install strictly from wheels (no network). Failure should stop the build.
RUN python -m pip install --upgrade pip setuptools wheel && \
        pip install --no-index --find-links /wheels -r /tmp/requirements.txt && \
        rm -rf /wheels /root/.cache/pip

# Extract runtime-only application snapshot prepared in the trainer stage. This
# guarantees training scripts are not present in the final image.
COPY --from=trainer /app_runtime.tar.gz /tmp/app_runtime.tar.gz
RUN tar -xzf /tmp/app_runtime.tar.gz -C /app && rm /tmp/app_runtime.tar.gz

# Extract trained model artifacts into expected inference path
COPY --from=trainer /artifacts.tar.gz /tmp/artifacts.tar.gz
RUN mkdir -p /app/Backend/Mood_Detection/outputs/models && tar -xzf /tmp/artifacts.tar.gz -C /app/Backend/Mood_Detection/outputs/models && rm /tmp/artifacts.tar.gz

# Create non-root user and set permissions
RUN useradd --create-home --shell /bin/bash ${APP_USER} && chown -R ${APP_USER}:${APP_USER} /app
USER ${APP_USER}

EXPOSE ${PORT}

# Run Gunicorn with 1 worker and threads enabled (ML-friendly). Bind to $PORT.
# The Flask app object is expected at Backend/app.py as `app` (module path: Backend.app:app).
CMD ["/bin/sh", "-c", "exec gunicorn -w 1 --threads 4 -b 0.0.0.0:${PORT} Backend.app:app"]
