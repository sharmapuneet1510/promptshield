"""
Precheck API endpoint - the core governance endpoint.
"""

from __future__ import annotations

import logging
import uuid
from typing import Annotated, Any

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from promptshield_core.contracts.request import PromptRequest
from promptshield_core.contracts.response import PromptDecisionResponse
from promptshield_core.enums import Decision
from promptshield_core.precheck_engine import PreCheckEngine
from promptshield_core.utils.hashing import hash_prompt
from promptshield_core.utils.redaction import redact_prompt
from promptshield_enterprise.api.middleware.auth import require_api_key
from promptshield_enterprise.services.quota_service import QuotaService
from promptshield_enterprise.settings import get_settings
from promptshield_enterprise.storage.database import get_db
from promptshield_enterprise.storage.models import PromptRecord
from promptshield_enterprise.storage.repository import PromptRepository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["precheck"])


def _get_redis() -> aioredis.Redis:
    settings = get_settings()
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


def _get_engine() -> PreCheckEngine:
    """Build a PreCheckEngine from the current configuration."""
    from promptshield_config.loader import ConfigLoader
    settings = get_settings()
    loader = ConfigLoader(config_dir=settings.CONFIG_DIR)
    full_config = loader.load_all()
    return PreCheckEngine.from_full_config(full_config)


@router.post(
    "/precheck",
    summary="Run a prompt governance precheck",
    description=(
        "Evaluates a prompt request against configured policy rules and returns "
        "a governance decision with token/cost estimates, classifications, and routing suggestions."
    ),
    response_model=PromptDecisionResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "Missing or invalid API key"},
        422: {"description": "Request validation error"},
    },
)
async def precheck(
    request: PromptRequest,
    api_key: Annotated[str, Depends(require_api_key)],
    db: AsyncSession = Depends(get_db),
) -> PromptDecisionResponse:
    """
    Run the PromptShield precheck engine on the provided request.

    This is the primary endpoint for integrating PromptShield into an
    application. Call this before sending a prompt to an LLM provider.
    """
    settings = get_settings()
    engine = _get_engine()

    # Fetch quota data and run policy with live counters
    redis_client = _get_redis()
    quota_service = QuotaService(redis_client)

    try:
        daily_requests = await quota_service.get_daily_count(request.user_id)
        daily_spend = await quota_service.get_daily_spend(request.user_id)
    except Exception as e:
        logger.warning("Failed to fetch quota for user %s: %s", request.user_id, e)
        daily_requests = 0
        daily_spend = 0.0

    # Rebuild engine with quota context
    from promptshield_config.loader import ConfigLoader
    loader = ConfigLoader(config_dir=settings.CONFIG_DIR)
    full_config = loader.load_all()
    engine = PreCheckEngine.from_full_config(
        full_config,
        daily_requests=daily_requests,
        daily_spend_usd=daily_spend,
    )

    # Run the precheck
    response = engine.run(request)

    # Update quota counters for this request
    try:
        await quota_service.increment_request_count(request.user_id)
        if response.decision not in (Decision.BLOCK,):
            await quota_service.increment_spend(request.user_id, response.estimated_cost_usd)
    except Exception as e:
        logger.warning("Failed to update quota for user %s: %s", request.user_id, e)
    finally:
        await redis_client.aclose()

    # Persist to database
    try:
        prompt_hash = hash_prompt(request.prompt_text)
        record = PromptRecord(
            id=uuid.uuid4(),
            request_id=request.request_id,
            user_id=request.user_id,
            team_id=request.team_id,
            source=request.source,
            model=request.model,
            input_tokens=response.estimated_input_tokens,
            output_tokens=response.estimated_output_tokens,
            total_tokens=response.estimated_total_tokens,
            cost_usd=response.estimated_cost_usd,
            decision=response.decision.value,
            classifications=[c.value for c in response.classifications],
            misuse_score=response.misuse_score,
            prompt_hash=prompt_hash,
            redacted_prompt=redact_prompt(request.prompt_text, max_chars=200),
            raw_prompt=request.prompt_text if settings.STORE_RAW_PROMPTS else None,
            route_taken=response.suggested_route.value,
        )
        repo = PromptRepository(db)
        await repo.save(record)
    except Exception as e:
        logger.error("Failed to persist precheck record: %s", e)
        # Don't fail the response because of storage issues

    return response
