"""
Analytics API endpoints.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from promptshield_enterprise.api.middleware.auth import require_admin_key
from promptshield_enterprise.services.analytics_service import AnalyticsService
from promptshield_enterprise.services.user_profile_service import UserProfileService
from promptshield_enterprise.storage.database import get_db

from sqlalchemy import select
from promptshield_enterprise.storage.models import PromptRecord, UserBehaviorProfile

router = APIRouter(prefix="/analytics", tags=["analytics"])

_VALID_PERSONAS = {
    "productive_coder",
    "power_user",
    "web_searcher",
    "abuser",
    "occasional_user",
    "unknown",
}

_VALID_LEADERBOARD_METRICS = {"effectiveness_score", "misuse_score", "total_requests"}


def _profile_to_dict(p: UserBehaviorProfile) -> dict[str, Any]:
    """Serialize a UserBehaviorProfile ORM object to a plain dict."""
    return {
        "user_id": p.user_id,
        "team_id": p.team_id,
        "total_requests": p.total_requests,
        "allow_count": p.allow_count,
        "warn_count": p.warn_count,
        "block_count": p.block_count,
        "reroute_web_count": p.reroute_web_count,
        "reroute_cheaper_count": p.reroute_cheaper_count,
        "total_input_tokens": p.total_input_tokens,
        "total_output_tokens": p.total_output_tokens,
        "total_cost_usd": round(p.total_cost_usd, 6),
        "coding_count": p.coding_count,
        "documentation_count": p.documentation_count,
        "search_like_count": p.search_like_count,
        "oversized_count": p.oversized_count,
        "generic_count": p.generic_count,
        "effectiveness_score": round(p.effectiveness_score, 4),
        "misuse_score": round(p.misuse_score, 4),
        "persona": p.persona,
        "first_seen": p.first_seen.isoformat(),
        "last_seen": p.last_seen.isoformat(),
        "updated_at": p.updated_at.isoformat(),
    }


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


# ---------------------------------------------------------------------------
# User behavioral profile endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/profiles",
    summary="List all user behavioral profiles",
    description=(
        "Returns behavioral profiles for all users with at least min_requests "
        "requests. Each profile includes effectiveness and misuse scores, "
        "classification counts, and the user's current persona."
    ),
    response_model=list,
)
async def get_profiles(
    _: Annotated[str, Depends(require_admin_key)],
    min_requests: int = 1,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all user behavioral profiles."""
    svc = UserProfileService(db)
    profiles = await svc.get_all_profiles(min_requests=min_requests)
    return [_profile_to_dict(p) for p in profiles]


@router.get(
    "/profiles/persona/{persona}",
    summary="Get profiles filtered by persona",
    description=(
        "Returns all user profiles classified under the specified persona. "
        "Valid personas: productive_coder, power_user, web_searcher, abuser, "
        "occasional_user, unknown."
    ),
    response_model=list,
)
async def get_profiles_by_persona(
    persona: str,
    _: Annotated[str, Depends(require_admin_key)],
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return all profiles with the specified persona."""
    if persona not in _VALID_PERSONAS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Invalid persona {persona!r}. "
                f"Must be one of: {', '.join(sorted(_VALID_PERSONAS))}"
            ),
        )
    svc = UserProfileService(db)
    profiles = await svc.get_profiles_by_persona(persona)
    return [_profile_to_dict(p) for p in profiles]


@router.get(
    "/profiles/{user_id}",
    summary="Get a single user's behavioral profile",
    description=(
        "Returns the full behavioral profile for the specified user, including "
        "effectiveness score, misuse score, classification breakdown, and persona."
    ),
    response_model=dict,
)
async def get_profile(
    user_id: str,
    _: Annotated[str, Depends(require_admin_key)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Fetch the behavioral profile for a single user."""
    svc = UserProfileService(db)
    profile = await svc.get_profile(user_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No behavioral profile found for user_id={user_id!r}.",
        )
    return _profile_to_dict(profile)


@router.get(
    "/leaderboard",
    summary="Effectiveness leaderboard",
    description=(
        "Returns the top users ranked by the specified metric. "
        "Supported metrics: effectiveness_score (default), misuse_score, "
        "total_requests. Results are always sorted descending."
    ),
    response_model=list,
)
async def get_leaderboard(
    _: Annotated[str, Depends(require_admin_key)],
    metric: str = "effectiveness_score",
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return top users sorted by the requested metric."""
    if metric not in _VALID_LEADERBOARD_METRICS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Invalid metric {metric!r}. "
                f"Must be one of: {', '.join(sorted(_VALID_LEADERBOARD_METRICS))}"
            ),
        )
    if limit < 1 or limit > 200:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="limit must be between 1 and 200.",
        )
    svc = UserProfileService(db)
    return await svc.get_leaderboard(metric=metric, limit=limit)


@router.get(
    "/abuse",
    summary="High-misuse user report",
    description=(
        "Returns users whose misuse score exceeds the specified threshold. "
        "This is an alias for filtering profiles by misuse score and is intended "
        "for security review workflows."
    ),
    response_model=list,
)
async def get_abuse_report(
    _: Annotated[str, Depends(require_admin_key)],
    threshold: float = 0.5,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return users with a misuse score above the given threshold."""
    if not (0.0 <= threshold <= 1.0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="threshold must be between 0.0 and 1.0.",
        )
    result = await db.execute(
        select(UserBehaviorProfile)
        .where(UserBehaviorProfile.misuse_score >= threshold)
        .order_by(UserBehaviorProfile.misuse_score.desc())
    )
    profiles = result.scalars().all()
    return [_profile_to_dict(p) for p in profiles]
