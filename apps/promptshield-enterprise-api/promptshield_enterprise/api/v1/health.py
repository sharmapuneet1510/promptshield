"""
Health check endpoints.
"""

from __future__ import annotations

import logging
from typing import Any

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from promptshield_enterprise.storage.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="Basic health check",
    description="Returns 200 if the API process is running.",
    response_model=dict,
)
async def health_basic() -> dict[str, str]:
    """Simple liveness probe."""
    return {"status": "ok"}


@router.get(
    "/health/ready",
    summary="Readiness check",
    description="Verifies database and Redis connectivity.",
    response_model=dict,
)
async def health_ready(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """
    Readiness probe that checks all backing services.

    Returns 200 with component statuses if all are healthy,
    503 if any component is unavailable.
    """
    from promptshield_enterprise.settings import get_settings

    checks: dict[str, str] = {}
    all_healthy = True

    # Check database
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        logger.error("Database health check failed: %s", e)
        checks["database"] = f"error: {e}"
        all_healthy = False

    # Check Redis
    try:
        settings = get_settings()
        client = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await client.ping()
        await client.aclose()
        checks["redis"] = "ok"
    except Exception as e:
        logger.error("Redis health check failed: %s", e)
        checks["redis"] = f"error: {e}"
        all_healthy = False

    if not all_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "degraded", "checks": checks},
        )

    return {"status": "ready", "checks": checks}
