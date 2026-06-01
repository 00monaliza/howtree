"""
FastAPI application factory.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import orjson
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import analyze, jobs, stats, trees
from app.api.routes.assistant import router as assistant_router  # ← новая строка
from app.core.config import get_settings
from app.core.database import async_engine, Base
from app.core.logging import configure_logging, get_logger

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger = get_logger(__name__)

    logger.info("startup", env=settings.app_env, provider=settings.map_provider)

    if settings.app_debug:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    from app.modules.detection.yolo_detector import YoloDetector

    # load YOLO model
    detector = YoloDetector(settings.yolo_model_path)
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, detector.load)
        app.state.yolo_model = detector
        logger.info("yolo_model_ready", path=settings.yolo_model_path)
    except Exception as exc:
        logger.error("yolo_model_load_failed", error=str(exc))
        app.state.yolo_model = None

    yield

    app.state.yolo_model = None

    logger.info("shutdown")
    await async_engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Tree Detection Platform API",
        description="Urban tree canopy analysis using satellite imagery and DeepForest ML.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def orjson_middleware(request: Request, call_next):
        response = await call_next(request)
        return response

    prefix = settings.api_prefix

    app.include_router(analyze.router, prefix=f"{prefix}/analyze", tags=["Analysis"])
    app.include_router(jobs.router, prefix=f"{prefix}/jobs", tags=["Jobs"])
    app.include_router(trees.router, prefix=f"{prefix}/trees", tags=["Trees"])
    app.include_router(stats.router, prefix=f"{prefix}/stats", tags=["Statistics"])
    app.include_router(assistant_router, prefix=f"{prefix}/assistant", tags=["Assistant"])  # ← новая строка

    @app.get("/health", tags=["Health"], include_in_schema=False)
    async def health():
        return {"status": "ok", "version": "1.0.0"}

    @app.get(f"{prefix}/health", tags=["Health"])
    async def api_health():
        return {"status": "ok", "env": settings.app_env}

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc)},
        )

    return app


app = create_app()