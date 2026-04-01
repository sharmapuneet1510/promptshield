"""
Admin endpoints for user management and quota configuration.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from promptshield_enterprise.api.middleware.auth import require_admin_key
from promptshield_enterprise.storage.database import get_db
from promptshield_enterprise.storage.models import UserQuota
from promptshield_enterprise.storage.repository import PromptRepository

router = APIRouter(prefix="/admin", tags=["admin"])


class QuotaUpdateRequest(BaseModel):
    """Request body for updating a user's quota."""

    daily_request_limit: int | None = None
    daily_spend_limit_usd: float | None = None


@router.get(
    "/users",
    summary="List users with usage statistics",
    description="Returns all users with their request count, token usage, cost, and misuse scores.",
    response_model=list,
)
async def list_users(
    _: Annotated[str, Depends(require_admin_key)],
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all users with aggregated usage statistics."""
    repo = PromptRepository(db)
    user_stats = await repo.get_user_stats()

    # Enrich with quota info
    quota_result = await db.execute(select(UserQuota))
    quotas = {q.user_id: q for q in quota_result.scalars().all()}

    for user in user_stats:
        uid = user["user_id"]
        quota = quotas.get(uid)
        user["daily_request_limit"] = quota.daily_request_limit if quota else None
        user["daily_spend_limit_usd"] = quota.daily_spend_limit_usd if quota else None

    return user_stats


@router.get(
    "/quota/{user_id}",
    summary="Get user quota",
    description="Returns quota configuration for a specific user.",
    response_model=dict,
)
async def get_user_quota(
    user_id: str,
    _: Annotated[str, Depends(require_admin_key)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get the quota configuration for a specific user."""
    result = await db.execute(select(UserQuota).where(UserQuota.user_id == user_id))
    quota = result.scalar_one_or_none()

    if quota is None:
        return {
            "user_id": user_id,
            "daily_request_limit": None,
            "daily_spend_limit_usd": None,
            "note": "No custom quota set. Global defaults apply.",
        }

    return {
        "user_id": quota.user_id,
        "daily_request_limit": quota.daily_request_limit,
        "daily_spend_limit_usd": quota.daily_spend_limit_usd,
        "updated_at": quota.updated_at.isoformat(),
    }


@router.put(
    "/quota/{user_id}",
    summary="Set user quota",
    description="Override the daily request and/or spend limits for a specific user.",
    response_model=dict,
)
async def set_user_quota(
    user_id: str,
    request: QuotaUpdateRequest,
    _: Annotated[str, Depends(require_admin_key)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Set or update quota limits for a specific user."""
    result = await db.execute(select(UserQuota).where(UserQuota.user_id == user_id))
    quota = result.scalar_one_or_none()

    if quota is None:
        quota = UserQuota(
            user_id=user_id,
            daily_request_limit=request.daily_request_limit,
            daily_spend_limit_usd=request.daily_spend_limit_usd,
            updated_at=datetime.now(timezone.utc),
        )
        db.add(quota)
    else:
        if request.daily_request_limit is not None:
            quota.daily_request_limit = request.daily_request_limit
        if request.daily_spend_limit_usd is not None:
            quota.daily_spend_limit_usd = request.daily_spend_limit_usd
        quota.updated_at = datetime.now(timezone.utc)

    await db.flush()

    return {
        "user_id": user_id,
        "daily_request_limit": quota.daily_request_limit,
        "daily_spend_limit_usd": quota.daily_spend_limit_usd,
        "updated_at": quota.updated_at.isoformat(),
    }
