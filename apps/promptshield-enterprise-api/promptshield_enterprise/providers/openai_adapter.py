"""
OpenAI-compatible provider adapter.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from promptshield_core.exceptions import ProviderError
from promptshield_enterprise.providers.base import ProviderAdapter, ProviderResponse

logger = logging.getLogger(__name__)

_OPENAI_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIAdapter(ProviderAdapter):
    """
    Adapter for OpenAI Chat Completions API.
    Compatible with any OpenAI-compatible endpoint (including Azure OpenAI,
    LiteLLM, etc.) by overriding base_url.
    """

    def __init__(
        self,
        base_url: str = _OPENAI_COMPLETIONS_URL,
        timeout: float = 60.0,
    ) -> None:
        self._base_url = base_url
        self._timeout = timeout

    @property
    def provider_name(self) -> str:
        return "openai"

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
        """Forward a prompt to the OpenAI Chat Completions API."""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(self._base_url, json=payload, headers=headers)
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise ProviderError(
                    f"OpenAI API error: {e.response.status_code} {e.response.text[:200]}",
                    provider="openai",
                    status_code=e.response.status_code,
                ) from e
            except httpx.RequestError as e:
                raise ProviderError(
                    f"OpenAI network error: {e}",
                    provider="openai",
                ) from e

        data = response.json()
        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        usage = data.get("usage", {})

        return ProviderResponse(
            content=content,
            model=data.get("model", model),
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            raw_response=data,
            provider=self.provider_name,
        )
