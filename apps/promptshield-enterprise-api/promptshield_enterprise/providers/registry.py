"""
Provider registry - maps model names to provider adapters.
"""

from __future__ import annotations

import logging

from promptshield_enterprise.providers.anthropic_adapter import AnthropicAdapter
from promptshield_enterprise.providers.base import ProviderAdapter
from promptshield_enterprise.providers.openai_adapter import OpenAIAdapter

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """
    Maps model names to their corresponding provider adapters.

    Model detection uses prefix matching, e.g. 'gpt-' → OpenAI adapter.
    """

    def __init__(self) -> None:
        self._adapters: dict[str, ProviderAdapter] = {
            "openai": OpenAIAdapter(),
            "anthropic": AnthropicAdapter(),
        }
        self._model_overrides: dict[str, str] = {}

    def register(self, provider_name: str, adapter: ProviderAdapter) -> None:
        """Register a custom provider adapter."""
        self._adapters[provider_name] = adapter

    def map_model(self, model: str, provider_name: str) -> None:
        """Map a specific model name to a provider."""
        self._model_overrides[model.lower()] = provider_name

    def get_adapter(self, model: str) -> ProviderAdapter | None:
        """
        Return the appropriate adapter for a model name.

        Returns None if no adapter is found (e.g. for local/web models).
        """
        model_lower = model.lower()

        # Check explicit overrides first
        if model_lower in self._model_overrides:
            provider = self._model_overrides[model_lower]
            return self._adapters.get(provider)

        # Auto-detect by prefix
        if model_lower.startswith(("gpt-", "o1", "o3", "text-embedding")):
            return self._adapters.get("openai")
        if model_lower.startswith("claude"):
            return self._adapters.get("anthropic")

        logger.debug("No adapter found for model '%s'", model)
        return None


# Module-level singleton
_registry: ProviderRegistry | None = None


def get_registry() -> ProviderRegistry:
    """Return the global provider registry."""
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
    return _registry
