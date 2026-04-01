"""
PromptShield Enterprise API - FastAPI application factory.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from promptshield_enterprise.api.middleware.logging import RequestLoggingMiddleware
from promptshield_enterprise.api.router import api_router
from promptshield_enterprise.settings import get_settings
from promptshield_enterprise.telemetry.logging import configure_logging

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    On startup: configure logging, initialize database, verify Redis.
    On shutdown: close connections.
    """
    settings = get_settings()

    # Configure structured logging
    configure_logging(
        log_level=settings.LOG_LEVEL,
        is_production=settings.is_production,
    )

    logger.info(
        "PromptShield Enterprise API starting",
        environment=settings.ENVIRONMENT,
        log_level=settings.LOG_LEVEL,
        store_raw_prompts=settings.STORE_RAW_PROMPTS,
    )

    # Initialize database
    try:
        from promptshield_enterprise.storage.database import init_db
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error("Database initialization failed", error=str(e))
        # Don't crash – let health endpoint report degraded status

    # Verify Redis connectivity
    try:
        import redis.asyncio as aioredis
        client = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=3)
        await client.ping()
        await client.aclose()
        logger.info("Redis connection verified")
    except Exception as e:
        logger.warning("Redis not available at startup", error=str(e))

    yield

    logger.info("PromptShield Enterprise API shutting down")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    settings = get_settings()

    app = FastAPI(
        title="PromptShield Enterprise API",
        description=(
            "Centralized prompt governance and query intelligence platform. "
            "Evaluate, route, and audit AI prompt requests at scale."
        ),
        version="0.1.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request logging middleware
    app.add_middleware(RequestLoggingMiddleware)

    # Include all routers
    app.include_router(api_router)

    # Prometheus metrics endpoint
    try:
        from prometheus_client import make_asgi_app
        metrics_app = make_asgi_app()
        app.mount("/metrics", metrics_app)
    except ImportError:
        pass

    return app


# Module-level app instance for uvicorn
app = create_app()
