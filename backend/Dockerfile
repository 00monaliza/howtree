# ================================================================
# Tree Detection Platform — Multi-stage Dockerfile
# ================================================================

FROM python:3.11-slim AS base

# System dependencies for geospatial libraries + OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgdal-dev \
    gdal-bin \
    libproj-dev \
    proj-data \
    proj-bin \
    libgeos-dev \
    libspatialindex-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install PyTorch CPU-only first (avoids pulling CUDA binaries)
RUN pip install --no-cache-dir \
    torch==2.1.2+cpu \
    torchvision==0.16.2+cpu \
    --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ── API stage ─────────────────────────────────────────────────
FROM base AS api
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--loop", "uvloop", "--workers", "2"]

# ── Worker stage ──────────────────────────────────────────────
FROM base AS worker
# Pre-download DeepForest model weights at build time (optional — comment out to pull at runtime)
# RUN python -c "from deepforest import main; m = main.deepforest(); m.use_release()"
CMD ["celery", "-A", "worker.celery_app", "worker", "--loglevel=info", "--concurrency=1", "-Q", "analysis"]
