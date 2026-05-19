# Tree Detection Platform — Progress

## Frontend — Completed ✅

### [1/7] Next.js init + shadcn setup + folder structure ✅
### [2/7] MapContainer with Mapbox satellite + bbox draw tool ✅
### [3/7] AnalysisPanel + API integration + WebSocket progress ✅
### [4/7] Tree points GeoJSON layer + heatmap toggle ✅
### [5/7] /analytics page with Recharts ✅
### [6/7] PDF report generation ✅
### [7/7] Mobile responsive + dark mode polish ✅

Frontend runs at: `npm run dev` → http://localhost:3000
Set `NEXT_PUBLIC_MAPBOX_TOKEN` in `.env.local`

---

## Backend — Completed ✅

### Architecture: FastAPI + Celery + Redis + PostgreSQL/PostGIS + DeepForest

### Step 1: Folder structure + Docker infrastructure ✅
- `backend/` inside monorepo
- Full docker-compose.yml: postgres (PostGIS 16), redis, fastapi, celery worker
- `docker compose up` starts everything

### Step 2: Core layer ✅
- Pydantic Settings (config.py)
- Async SQLAlchemy engine + sync engine for Celery
- Structured logging (structlog, JSON in prod)
- WebSocket manager with Redis pub/sub

### Step 3: DB models + Alembic ✅
- `trees`: PostGIS Point + Polygon, GIST indexes
- `analysis_jobs`: full job lifecycle
- `districts`: MultiPolygon with GIST index

### Step 4: Pydantic schemas + API routes ✅
- POST /api/v1/analyze → 202 Accepted, dispatches Celery task
- GET /api/v1/jobs/{job_id} → poll status
- WS /api/v1/jobs/ws/{job_id} → real-time progress stream
- GET /api/v1/trees/geojson → streaming GeoJSON response
- GET /api/v1/stats/{district} and /stats/bbox

### Step 5: Map provider abstraction ✅
- YandexProvider (primary, Kazakhstan coverage)
- MapboxProvider (fallback)
- Async TileDownloader with retries (tenacity)
- bbox → overlapping tile grid (20% overlap)

### Step 6: Detection pipeline ✅
- DeepForest loaded ONCE at worker process init
- CPU-only inference (no CUDA dependency)
- Pixel → geographic coordinate transform
- IoU-based NMS deduplication (0.3 threshold)
- Canopy area estimation per detection

### Step 7: Celery tasks ✅
- `run_analysis_task`: full async pipeline in sync Celery context
- Redis pub/sub progress relay
- Batch DB inserts (500 trees/batch)
- Model warm-up at worker startup via `@worker_process_init`

### Step 8: GIS analytics ✅
- PostGIS ST_Within spatial queries
- Streaming GeoJSON (no full-load into memory)
- District stats via ST_Intersects + ST_Area
- Confidence distribution binning

### Step 9: Tests ✅
- 32 unit tests, all passing
- Coverage: bbox validation, tile grid, coord transform, NMS/IoU, statistics

---

## Next Steps
- [ ] Set environment variables in `.env` (copy from `.env.example`)
- [ ] Set YANDEX_MAPS_API_KEY
- [ ] Run: `cd backend && docker compose up`
- [ ] Run Alembic migration: `alembic upgrade head`
- [ ] Test end-to-end: draw bbox on frontend → analysis runs → trees appear on map
- [ ] Load district boundaries (GeoJSON → PostGIS import script)
- [ ] Fine-tune DeepForest if Kazakhstan imagery detection accuracy is low
