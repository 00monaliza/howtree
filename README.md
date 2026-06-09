# howTree — Tree Detection Platform

Urban tree detection and analysis platform powered by DeepForest ML model, FastAPI, and Next.js.

## Architecture

```
┌─────────────────┐     ┌──────────────────────────────────────────┐
│  Next.js 16     │────▶│  FastAPI  (port 8000)                    │
│  (port 3000)    │     │  ├── /analyze  – sync YOLO detection     │
└─────────────────┘     │  ├── /jobs     – async Celery jobs        │
                        │  ├── /trees    – stored tree data         │
                        │  └── /stats    – statistics               │
                        └───────┬──────────────────┬───────────────┘
                                │                  │
                         ┌──────▼──────┐   ┌──────▼──────┐
                         │  PostgreSQL  │   │    Redis     │
                         │  + PostGIS  │   │  (broker +   │
                         │  (port 5433)│   │   cache)     │
                         └─────────────┘   └──────┬───────┘
                                                  │
                                          ┌───────▼───────┐
                                          │ Celery Worker  │
                                          │ (DeepForest)   │
                                          └───────────────┘
```

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) 24+ and Docker Compose v2
- [Node.js](https://nodejs.org/) 20+
- [Git](https://git-scm.com/)

## Quick Start (Docker + Next.js)

### 1. Clone the repository

```bash
git clone <repo-url>
cd howTree
```

### 2. Configure backend environment

```bash
cp backend/.env.example backend/.env
```

Open `backend/.env` and fill in the required values:

| Variable | Required | Description |
|---|---|---|
| `APP_SECRET_KEY` | Yes | Random 32-byte secret (use `openssl rand -hex 32`) |
| `POSTGRES_PASSWORD` | Yes | Any strong password |
| `YANDEX_MAPS_API_KEY` | Optional | For Yandex satellite tiles |
| `MAPBOX_TOKEN` | Optional | Fallback imagery provider |
| `MAP_PROVIDER` | No | `esri` (default), `yandex`, or `mapbox` |

> The ML model file `deepforest_urban_trees_FULL.pt` must be present in the project root (`/howTree/deepforest_urban_trees_FULL.pt`). It is referenced via `YOLO_MODEL_PATH=../deepforest_urban_trees_FULL.pt` in `.env`.

### 3. Start backend services

```bash
cd backend
docker compose up -d
```

This starts:
- **PostgreSQL + PostGIS** on `localhost:5433`
- **Redis** on `localhost:6379`
- **FastAPI** on `http://localhost:8000`
- **Celery Worker** (background analysis jobs)

Wait for all containers to be healthy:

```bash
docker compose ps
```

All services should show `healthy` or `running`. First run takes several minutes — Docker builds the Python image with GDAL, PyTorch, and DeepForest.

Check the API is up:

```bash
curl http://localhost:8000/health
```

### 4. Start the frontend

In a new terminal, from the project root:

```bash
npm install
npm run dev
```

Open **http://localhost:3000** in your browser.

---

## Local Development (without Docker)

Use this if you want to run Python services directly (e.g. for faster iteration or debugging).

### System dependencies

macOS:
```bash
brew install gdal proj geos spatialindex postgresql redis
```

Ubuntu/Debian:
```bash
sudo apt-get install libgdal-dev gdal-bin libproj-dev libgeos-dev libspatialindex-dev
```

### Python environment

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install torch==2.1.2 torchvision==0.16.2 --index-url https://download.pytorch.org/whl/cpu
pip install "albumentations>=1.3.0,<2.0"
pip install -r requirements.txt
```

### Database

Start PostgreSQL and Redis (via Docker is easiest):

```bash
docker compose up -d postgres redis
```

Run database migrations:

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
```

### Run FastAPI

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

### Run Celery worker

```bash
cd backend
source .venv/bin/activate
celery -A worker.celery_app worker --loglevel=info --concurrency=1 -Q analysis
```

### Run frontend

```bash
# from project root
npm install
npm run dev
```

---

## Optional: Celery Flower (job monitoring)

```bash
cd backend
docker compose --profile monitoring up -d flower
```

Open **http://localhost:5555** to monitor background tasks.

---

## Environment Variables Reference

Full list with descriptions is in `backend/.env.example`.

Key variables:

```env
# API keys
YANDEX_MAPS_API_KEY=     # Yandex Static Maps API (yandex provider)
MAPBOX_TOKEN=            # Mapbox token (mapbox provider)
MAP_PROVIDER=esri        # esri | yandex | mapbox

# ML detection
YOLO_MODEL_PATH=../deepforest_urban_trees_FULL.pt
YOLO_CONFIDENCE=0.25
DETECTION_CONFIDENCE_THRESHOLD=0.4
MAX_BBOX_AREA_KM2=50.0

# CORS (must include your frontend origin)
CORS_ORIGINS=["http://localhost:3000","http://localhost:3001"]
```

---

## Deploying the Detectron2 Model Weights

The trained Mask R-CNN model (`model_best.pth`, ~200 MB) is **not committed to git**. After cloning the repo on the server, place the weights manually:

```bash
# 1. Create the weights directory
mkdir -p backend/weights

# 2. Upload from your local machine
scp /local/path/to/model_best.pth user@server:/path/to/howTree/backend/weights/model_best.pth

# 3. Run the setup script (creates the dir, installs detectron2)
bash backend/setup.sh
```

The direct inference server reads weights from `backend/weights/model_best.pth`. If the file is missing, the `/predict` and `/predict/bbox` endpoints return HTTP 503.

### Starting the direct inference server (port 8001)

```bash
cd backend
source .venv/bin/activate
uvicorn api:app --port 8001 --host 0.0.0.0
```

Set `NEXT_PUBLIC_DIRECT_API_URL=http://your-server:8001` in the frontend `.env.local` if the server is remote.

---

## API Endpoints

### Main app (port 8000)

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/analyze` | Submit async analysis job |
| `GET` | `/api/v1/jobs/{id}` | Get job status and results |
| `GET` | `/api/v1/trees` | Query stored tree records |
| `GET` | `/api/v1/stats` | Detection statistics |

Interactive API docs: **http://localhost:8000/docs**

### Direct inference server (port 8001)

| Method | Path | Description |
|---|---|---|
| `POST` | `/predict` | Upload image → Detectron2 polygon GeoJSON |
| `POST` | `/predict/bbox` | Bbox + tile source → Detectron2 polygon GeoJSON |
| `POST` | `/detect/bbox` | Bbox + tile source → YOLO detection (legacy) |
| `POST` | `/detect/image` | Image upload → YOLO detection (legacy) |

Interactive docs: **http://localhost:8001/docs**

---

## Stopping Services

```bash
# Stop Docker services
cd backend && docker compose down

# Stop Next.js: Ctrl+C in the terminal running npm run dev
```

To remove volumes (database data):

```bash
cd backend && docker compose down -v
```
