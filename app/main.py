"""
app/main.py

FastAPI application factory and entry point.
Responsibilities:
  - Configure logging before anything else runs
  - Create DB tables on startup (dev only — production uses Alembic migrations)
  - Register middleware (CORS)
  - Mount the v1 API router
  - Expose health and readiness probes (required by Docker HEALTHCHECK and K8s probes)
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging_config import configure_logging
from app.db.session import Base, engine

# Configure logging before any other module emits a log line
configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Runs startup logic before the server accepts requests,
    and cleanup logic on shutdown.

    NOTE: In production, table creation is handled by Alembic migrations
    (alembic upgrade head), not by create_all. This is kept here for
    local development convenience.
    """
    logger.info("Starting up — environment: %s", settings.ENVIRONMENT)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables verified/created")
    yield
    logger.info("Shutting down — closing database connections")
    await engine.dispose()


# ── Application Factory ───────────────────────────────────
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Enterprise-grade FinTech ledger API demonstrating JWT authentication, "
        "async PostgreSQL, structured logging, and clean architecture. "
        "Built as a DevSecOps portfolio project."
    ),
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
)

# ── CORS Middleware ───────────────────────────────────────
# In production, replace "*" with your actual frontend domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"] if settings.ENVIRONMENT == "development" else [],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Routers ───────────────────────────────────────────────
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# ── Observability Endpoints ───────────────────────────────
@app.get("/health", tags=["Observability"], include_in_schema=False)
async def health_check():
    """
    Liveness probe — confirms the process is running.
    Used by: Docker HEALTHCHECK, K8s livenessProbe.
    """
    return {"status": "healthy", "version": settings.VERSION}


@app.get("/ready", tags=["Observability"], include_in_schema=False)
async def readiness_check():
    """
    Readiness probe — confirms the app is ready to serve traffic.
    Used by: K8s readinessProbe (prevents routing to unready pods).
    """
    return {"status": "ready", "environment": settings.ENVIRONMENT}
