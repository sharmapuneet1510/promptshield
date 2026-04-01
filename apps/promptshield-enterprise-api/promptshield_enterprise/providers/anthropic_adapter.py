"""
Anthropic Messages API adapter.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from promptshield_core.exceptions import ProviderError
from promptshield_enterprise.providers.base import ProviderAdapter, ProviderResponse

logger = logging.getLogger(__name__)

_ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"


class AnthropicAdapter(ProviderAdapter):
    """
    Adapter for the Anthropic Messages API.
    """

    def __init__(self, timeout: float = 60.0) -> None:
        self._timeout = timeout

    @property
    def provider_name(self) -> str:
        return "anthropic"

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
        """Forward a prompt to the Anthropic Messages API."""
        headers = {
            "x-api-key": api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            **kwargs,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(_ANTHROPIC_MESSAGES_URL, json=payload, headers=headers)
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise ProviderError(
                    f"Anthropic API error: {e.response.status_code} {e.response.text[:200]}",
                    provider="anthropic",
                    status_code=e.response.status_code,
                ) from e
            except httpx.RequestError as e:
                raise ProviderError(
                    f"Anthropic network error: {e}",
                    provider="anthropic",
                ) from e

        data = response.json()
        content_blocks = data.get("content", [])
        content = "".join(
            block.get("text", "") for block in content_blocks if block.get("type") == "text"
        )
        usage = data.get("usage", {})

        return ProviderResponse(
            content=content,
            model=data.get("model", model),
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            raw_response=data,
            provider=self.provider_name,
        )
