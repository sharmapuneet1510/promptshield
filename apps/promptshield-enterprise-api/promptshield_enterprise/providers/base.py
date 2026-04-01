"""
Abstract provider adapter base class.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProviderResponse:
    """Normalized response from a model provider."""

    content: str
    """The model's text response."""

    model: str
    """The model identifier that was used."""

    input_tokens: int = 0
    """Actual input tokens used (from provider response headers/body)."""

    output_tokens: int = 0
    """Actual output tokens used."""

    raw_response: dict[str, Any] = field(default_factory=dict)
    """The raw provider response body for debugging."""

    provider: str = "unknown"
    """The provider identifier."""


class ProviderAdapter(ABC):
    """
    Abstract base class for model provider adapters.

    Each adapter handles authentication, request formatting, and response
    normalization for a specific provider.
    """

    @abstractmethod
    async def forward(
        self,
        prompt: str,
        model: str,
        api_key: str,
        *,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> ProviderResponse:
        """
        Forward a prompt to the provider and return a normalized response.

        Args:
            prompt:     The prompt text to send.
            model:      The model identifier.
            api_key:    The provider API key.
            max_tokens: Maximum output tokens.
            temperature: Sampling temperature.
            kwargs:     Additional provider-specific parameters.

        Returns:
            Normalized ProviderResponse.

        Raises:
            ProviderError: If the provider request fails.
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider's identifier string."""
        ...
