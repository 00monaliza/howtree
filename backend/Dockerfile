# ================================================================
# Tree Detection Platform — Multi-stage Dockerfile
# ================================================================

# Pin Debian to bookworm. The floating python:3.11-slim tag can move to newer
# Debian releases whose system GnuTLS stack conflicts with older torchvision
# CPU wheels used by DeepForest.
FROM python:3.11-slim-bookworm AS base

# System dependencies for geospatial libraries + OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libgdal-dev \
    gdal-bin \
    libproj-dev \
    proj-data \
    proj-bin \
    libgeos-dev \
    libspatialindex-dev \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install PyTorch CPU-only first (avoids pulling CUDA binaries)
RUN pip install --no-cache-dir \
    torch==2.1.2 \
    torchvision==0.16.2 \
    --index-url https://download.pytorch.org/whl/cpu
# Remove torchvision's bundled libgnutls — on ARM64/aarch64 it conflicts with
# the system's libngtcp2_crypto_gnutls which requires GNUTLS_3_7_2
RUN find /usr/local/lib -path "*/torchvision.libs/libgnutls*.so*" -delete 2>/dev/null || true

COPY requirements.txt .
# Pin albumentations to 1.x — deepforest 1.4.1 uses albumentations.functional
# which was removed in albumentations 2.0
RUN pip install --no-cache-dir "albumentations>=1.3.0,<2.0"
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ── API stage ─────────────────────────────────────────────────
FROM base AS api
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--loop", "uvloop", "--workers", "1"]

# ── Worker stage ──────────────────────────────────────────────
FROM base AS worker
# Pre-download DeepForest model weights at build time (optional — comment out to pull at runtime)
# RUN python -c "from deepforest import main; m = main.deepforest(); m.use_release()"
CMD ["celery", "-A", "worker.celery_app", "worker", "--loglevel=info", "--concurrency=1", "-Q", "analysis"]
