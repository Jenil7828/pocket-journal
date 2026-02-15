FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Minimal system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip
RUN python3 -m pip install --upgrade pip

# 🔥 Install heavy GPU ML stack directly here
RUN pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cu121 \
    torch==2.5.1+cu121 \
    transformers==4.48.3 \
    sentence-transformers==5.1.0 \
    accelerate>=1.3.0 \
    numpy>=2.1.0 \
    safetensors>=0.4.5 \
    huggingface-hub>=0.28.0 \
    protobuf==5.28.3

# Copy lightweight app requirements
COPY Backend/requirements.txt .

# Install remaining app dependencies only
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (models excluded via .dockerignore)
COPY Backend /app

EXPOSE 8080

CMD ["gunicorn", "-w", "1", "--threads", "4", "-b", "0.0.0.0:8080", "app:app"]

# FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

# ENV DEBIAN_FRONTEND=noninteractive \
#     PYTHONDONTWRITEBYTECODE=1 \
#     PYTHONUNBUFFERED=1 \
#     PORT=8080

# RUN apt-get update && apt-get install -y --no-install-recommends \
#     python3 \
#     python3-pip \
#     ca-certificates \
#     && rm -rf /var/lib/apt/lists/*

# WORKDIR /app

# RUN python3 -m pip install --upgrade pip

# COPY Backend/requirements.txt .

# RUN pip install --no-cache-dir -r requirements.prod.txt

# COPY Backend /app

# EXPOSE 8080

# CMD ["gunicorn", "-w", "1", "--threads", "4", "-b", "0.0.0.0:8080", "app:app"]
