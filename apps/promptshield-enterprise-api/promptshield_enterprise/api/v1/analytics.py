"""
Analytics API endpoints.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from promptshield_enterprise.api.middleware.auth import require_admin_key
from promptshield_enterprise.services.analytics_service import AnalyticsService
from promptshield_enterprise.storage.database import get_db

from sqlalchemy import select
from promptshield_enterprise.storage.models import PromptRecord

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get(
    "/summary",
    summary="Aggregate usage summary",
    description="Returns total requests, tokens, cost, decision counts, and block rate.",
    response_model=dict,
)
async def get_summary(
    _: Annotated[str, Depends(require_admin_key)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """High-level usage summary across all requests."""
    service = AnalyticsService(db)
    return await service.get_summary()


@router.get(
    "/users",
    summary="Per-user usage statistics",
    description="Returns request count, token usage, cost, and misuse score per user.",
    response_model=list,
)
async def get_user_stats(
    _: Annotated[str, Depends(require_admin_key)],
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Usage statistics grouped by user_id."""
    service = AnalyticsService(db)
    return await service.get_user_stats()


@router.get(
    "/models",
    summary="Per-model usage statistics",
    description="Returns request count, token usage, and cost grouped by model.",
    response_model=list,
)
async def get_model_stats(
    _: Annotated[str, Depends(require_admin_key)],
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Usage statistics grouped by model."""
    service = AnalyticsService(db)
    return await service.get_model_stats()


@router.get(
    "/misuse",
    summary="Misuse detection report",
    description="Returns users with high misuse scores above the configured threshold.",
    response_model=list,
)
async def get_misuse_report(
    _: Annotated[str, Depends(require_admin_key)],
    threshold: float = 0.5,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Users with misuse scores above the threshold."""
    service = AnalyticsService(db)
    return await service.get_misuse_report(threshold=threshold)


@router.get(
    "/requests",
    summary="Recent prompt records",
    description="Returns recent prompt check records with optional decision filter.",
    response_model=list,
)
async def get_requests(
    _: Annotated[str, Depends(require_admin_key)],
    decision: str | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List recent prompt records, optionally filtered by decision."""
    stmt = select(PromptRecord).order_by(PromptRecord.created_at.desc()).limit(limit)
    if decision and decision != "ALL":
        stmt = stmt.where(PromptRecord.decision == decision)
    result = await db.execute(stmt)
    records = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "request_id": str(r.request_id),
            "user_id": r.user_id,
            "team_id": r.team_id,
            "source": r.source,
            "model": r.model,
            "input_tokens": r.input_tokens,
            "output_tokens": r.output_tokens,
            "total_tokens": r.total_tokens,
            "cost_usd": r.cost_usd,
            "decision": r.decision,
            "classifications": r.classifications,
            "misuse_score": r.misuse_score,
            "route_taken": r.route_taken,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]
