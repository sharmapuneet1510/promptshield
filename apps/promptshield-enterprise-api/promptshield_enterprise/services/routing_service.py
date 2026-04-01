"""
Routing service - determines actual provider URL based on decision.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from promptshield_core.enums import Decision, RouteTarget

logger = logging.getLogger(__name__)

_OPENAI_BASE_URL = "https://api.openai.com/v1"
_ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1"


@dataclass
class RouteInfo:
    """The resolved routing target with provider details."""

    target: RouteTarget
    provider: str | None
    base_url: str | None
    model: str
    should_forward: bool


class RoutingService:
    """
    Determines the actual routing target based on decision and configuration.
    """

    def __init__(self, routing_config: dict) -> None:
        """
        Args:
            routing_config: Routing config dict (from RoutingConfig.model_dump()).
        """
        self._config = routing_config

    def resolve(
        self,
        decision: Decision,
        requested_model: str,
        suggested_route: RouteTarget,
    ) -> RouteInfo:
        """
        Resolve the final routing target.

        Args:
            decision:        The governance decision.
            requested_model: The originally requested model.
            suggested_route: The suggested route from the policy engine.

        Returns:
            RouteInfo with the actual routing target and provider details.
        """
        if decision == Decision.BLOCK:
            return RouteInfo(
                target=RouteTarget.BLOCK,
                provider=None,
                base_url=None,
                model=requested_model,
                should_forward=False,
            )

        if decision == Decision.REQUIRE_CONFIRMATION:
            return RouteInfo(
                target=RouteTarget.REQUIRE_CONFIRMATION,
                provider=None,
                base_url=None,
                model=requested_model,
                should_forward=False,
            )

        if decision == Decision.REROUTE_WEBSEARCH:
            return RouteInfo(
                target=RouteTarget.WEB_SEARCH,
                provider="web_search",
                base_url=None,
                model="web",
                should_forward=False,
            )

        if decision == Decision.REROUTE_CHEAPER_MODEL:
            cheaper = self._config.get("cheaper_model_fallback", requested_model)
            return RouteInfo(
                target=RouteTarget.CHEAPER_MODEL,
                provider=self._detect_provider(cheaper),
                base_url=self._get_base_url(cheaper),
                model=cheaper or requested_model,
                should_forward=True,
            )

        # ALLOW or WARN - forward to requested model
        return RouteInfo(
            target=RouteTarget.REQUESTED_MODEL,
            provider=self._detect_provider(requested_model),
            base_url=self._get_base_url(requested_model),
            model=requested_model,
            should_forward=True,
        )

    @staticmethod
    def _detect_provider(model: str) -> str:
        """Infer the provider from the model name."""
        m = model.lower()
        if m.startswith("gpt") or m.startswith("o1") or m.startswith("o3"):
            return "openai"
        if m.startswith("claude"):
            return "anthropic"
        if m.startswith("ollama/") or m.startswith("llama") or m.startswith("mistral"):
            return "ollama"
        return "unknown"

    @staticmethod
    def _get_base_url(model: str) -> str | None:
        """Return the provider base URL for the given model."""
        provider = RoutingService._detect_provider(model)
        mapping = {
            "openai": _OPENAI_BASE_URL,
            "anthropic": _ANTHROPIC_BASE_URL,
            "ollama": "http://localhost:11434",
        }
        return mapping.get(provider)
