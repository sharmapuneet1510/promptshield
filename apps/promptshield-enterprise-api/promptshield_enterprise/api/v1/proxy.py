"""
Proxy endpoint - precheck + forward to provider.
"""

from __future__ import annotations

import logging
import os
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from promptshield_core.contracts.request import PromptRequest
from promptshield_core.contracts.response import PromptDecisionResponse
from promptshield_core.enums import Decision
from promptshield_enterprise.api.middleware.auth import require_api_key
from promptshield_enterprise.api.v1.precheck import precheck
from promptshield_enterprise.providers.registry import get_registry
from promptshield_enterprise.services.routing_service import RoutingService
from promptshield_enterprise.settings import get_settings
from promptshield_enterprise.storage.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(tags=["proxy"])


class ProxyResponse(BaseModel):
    """Combined precheck decision + provider response."""

    decision: PromptDecisionResponse
    content: str | None = None
    provider: str | None = None
    actual_model: str | None = None
    actual_input_tokens: int = 0
    actual_output_tokens: int = 0
    forwarded: bool = False
    message: str | None = None


@router.post(
    "/proxy",
    summary="Precheck and optionally forward to provider",
    description=(
        "Runs the governance precheck, and if the decision allows it, "
        "forwards the prompt to the appropriate provider. "
        "Requires provider API keys to be configured via environment variables."
    ),
    response_model=ProxyResponse,
    status_code=status.HTTP_200_OK,
)
async def proxy(
    request: PromptRequest,
    api_key: Annotated[str, Depends(require_api_key)],
    db: AsyncSession = Depends(get_db),
) -> ProxyResponse:
    """
    Precheck + forward to provider in a single call.

    The request is evaluated against policy first. If ALLOW or WARN,
    it is forwarded to the appropriate provider. BLOCK requests are
    returned without forwarding.
    """
    settings = get_settings()

    # Run precheck first
    decision_response = await precheck(request=request, api_key=api_key, db=db)

    # Determine routing
    from promptshield_config.loader import ConfigLoader
    loader = ConfigLoader(config_dir=settings.CONFIG_DIR)
    full_config = loader.load_all()
    routing_service = RoutingService(full_config.routing.model_dump())
    route_info = routing_service.resolve(
        decision=decision_response.decision,
        requested_model=request.model,
        suggested_route=decision_response.suggested_route,
    )

    if not route_info.should_forward:
        return ProxyResponse(
            decision=decision_response,
            forwarded=False,
            message=f"Request was not forwarded: decision={decision_response.decision.value}",
        )

    # Get provider adapter
    registry = get_registry()
    adapter = registry.get_adapter(route_info.model)

    if adapter is None:
        return ProxyResponse(
            decision=decision_response,
            forwarded=False,
            message=f"No provider adapter found for model '{route_info.model}'",
        )

    # Determine API key for the provider
    provider_api_key = _get_provider_api_key(route_info.provider or "")
    if not provider_api_key:
        logger.warning("No API key configured for provider '%s'", route_info.provider)
        return ProxyResponse(
            decision=decision_response,
            forwarded=False,
            message=f"No API key configured for provider '{route_info.provider}'",
        )

    # Forward to provider
    try:
        provider_response = await adapter.forward(
            prompt=request.prompt_text,
            model=route_info.model,
            api_key=provider_api_key,
        )
        return ProxyResponse(
            decision=decision_response,
            content=provider_response.content,
            provider=provider_response.provider,
            actual_model=provider_response.model,
            actual_input_tokens=provider_response.input_tokens,
            actual_output_tokens=provider_response.output_tokens,
            forwarded=True,
        )
    except Exception as e:
        logger.error("Provider forwarding failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Provider error: {e}",
        )


def _get_provider_api_key(provider: str) -> str | None:
    """Retrieve the API key for a provider from environment variables."""
    mapping = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
    }
    env_var = mapping.get(provider.lower(), "")
    return os.environ.get(env_var) if env_var else None
