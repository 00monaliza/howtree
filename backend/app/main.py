"""
FastAPI application factory.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

import orjson
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import analyze, jobs, stats, trees
from app.core.config import get_settings
from app.core.database import async_engine, Base
from app.core.logging import configure_logging, get_logger

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger = get_logger(__name__)

    logger.info("startup", env=settings.app_env, provider=settings.map_provider)

    # Ensure tables exist (idempotent — Alembic handles schema in production)
    if settings.app_debug:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    yield

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

    # ── Middleware ────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Custom JSON renderer (faster, handles UUIDs natively) ────
    @app.middleware("http")
    async def orjson_middleware(request: Request, call_next):
        response = await call_next(request)
        return response

    # ── Routes ────────────────────────────────────────────────────
    prefix = settings.api_prefix

    app.include_router(analyze.router, prefix=f"{prefix}/analyze", tags=["Analysis"])
    app.include_router(jobs.router, prefix=f"{prefix}/jobs", tags=["Jobs"])
    app.include_router(trees.router, prefix=f"{prefix}/trees", tags=["Trees"])
    app.include_router(stats.router, prefix=f"{prefix}/stats", tags=["Statistics"])

    # ── Health check ──────────────────────────────────────────────
    @app.get("/health", tags=["Health"], include_in_schema=False)
    async def health():
        return {"status": "ok", "version": "1.0.0"}

    @app.get(f"{prefix}/health", tags=["Health"])
    async def api_health():
        return {"status": "ok", "env": settings.app_env}

    # ── Exception handlers ────────────────────────────────────────
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc)},
        )

    return app


app = create_app()
