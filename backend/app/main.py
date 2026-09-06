"""
SAGAR-VIEW FastAPI application entry point.
"""
from __future__ import annotations
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.services import cache_service
from app.routers import datasets, fields, observations, profiles, export

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("SAGAR-VIEW API starting up...")

    # Initialise Redis if configured
    if settings.redis_url:
        cache_service.init_redis(settings.redis_url)

    # Pre-warm dataset registry if demo data exists
    from app.services.dataset_service import list_datasets
    datasets_loaded = list_datasets()
    logger.info("Loaded %d dataset(s)", len(datasets_loaded))

    yield

    # Cleanup
    from app.services.dataset_service import registry
    registry.close_all()
    logger.info("SAGAR-VIEW API shut down.")


app = FastAPI(
    title="SAGAR-VIEW API",
    description=(
        "Backend API for the SAGAR-VIEW interactive 3D ocean visualization platform (SIH26067). "
        "Provides ocean model field data, Argo/Glider observations, and model-observation collocation."
    ),
    version="1.0.0-mvp",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(datasets.router)
app.include_router(fields.router)
app.include_router(observations.router)
app.include_router(profiles.router)
app.include_router(export.router)


# ── Health / root ─────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
def root():
    return {"service": "SAGAR-VIEW API", "version": "1.0.0-mvp", "status": "ok"}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "cache": cache_service.cache_stats(),
        "demo_mode": settings.demo_mode,
    }
