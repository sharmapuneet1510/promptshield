"""
PromptShield Python SDK client.

Provides both async and sync interfaces to the PromptShield Enterprise API.

Usage (async)::

    from promptshield_sdk import PromptShieldClient

    client = PromptShieldClient(
        base_url="http://localhost:8000",
        api_key="your-api-key",
    )
    result = await client.precheck(
        prompt="Write a Python quicksort",
        model="gpt-4o",
        user_id="alice",
    )
    if result.is_blocked:
        raise RuntimeError("Request blocked by policy")

Usage (sync)::

    result = client.precheck_sync(prompt="...", model="gpt-4o", user_id="alice")
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from promptshield_sdk.exceptions import (
    AuthenticationError,
    BlockedError,
    ForbiddenError,
    PromptShieldClientError,
    RateLimitError,
)
from promptshield_sdk.models import DecisionResult, ProxyResult

_DEFAULT_TIMEOUT = 10.0
_PRECHECK_PATH = "/api/v1/precheck"
_PROXY_PATH = "/api/v1/proxy"


class PromptShieldClient:
    """
    Async-first client for the PromptShield Enterprise API.

    Provides both async (await) and sync convenience methods.

    Args:
        base_url: Base URL of the Enterprise API (e.g. 'http://localhost:8000').
        api_key:  API key (sent as X-API-Key header).
        timeout:  Request timeout in seconds (default: 10.0).
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
            "User-Agent": "promptshield-sdk/0.1.0",
        }

    # ------------------------------------------------------------------
    # Async methods
    # ------------------------------------------------------------------

    async def precheck(
        self,
        prompt: str,
        model: str,
        user_id: str,
        *,
        raise_on_block: bool = False,
        **kwargs: Any,
    ) -> DecisionResult:
        """
        Run a precheck on a prompt.

        Args:
            prompt:         The prompt text to evaluate.
            model:          Target model identifier.
            user_id:        User identifier for quota tracking.
            raise_on_block: If True, raises BlockedError when decision is BLOCK.
            kwargs:         Additional request fields (team_id, source, etc.).

        Returns:
            DecisionResult with the governance decision.

        Raises:
            BlockedError:             If raise_on_block=True and decision is BLOCK.
            AuthenticationError:      On 401 responses.
            ForbiddenError:           On 403 responses.
            RateLimitError:           On 429 responses.
            PromptShieldClientError:  On other errors.
        """
        payload = {
            "prompt_text": prompt,
            "model": model,
            "user_id": user_id,
            **kwargs,
        }
        data = await self._post(_PRECHECK_PATH, payload)
        result = DecisionResult.model_validate(data)

        if raise_on_block and result.is_blocked:
            messages = "; ".join(result.messages) if result.messages else "Request blocked by policy"
            raise BlockedError(messages, decision_result=result)

        return result

    async def proxy(
        self,
        prompt: str,
        model: str,
        user_id: str,
        *,
        raise_on_block: bool = False,
        **kwargs: Any,
    ) -> ProxyResult:
        """
        Run a precheck and optionally forward to the provider.

        Args:
            prompt:         The prompt text.
            model:          Target model identifier.
            user_id:        User identifier.
            raise_on_block: If True, raises BlockedError when decision is BLOCK.
            kwargs:         Additional request fields.

        Returns:
            ProxyResult with the decision and (if forwarded) the model response.
        """
        payload = {
            "prompt_text": prompt,
            "model": model,
            "user_id": user_id,
            **kwargs,
        }
        data = await self._post(_PROXY_PATH, payload)
        result = ProxyResult.model_validate(data)

        if raise_on_block and result.decision.is_blocked:
            messages = "; ".join(result.decision.messages) if result.decision.messages else "Request blocked"
            raise BlockedError(messages, decision_result=result.decision)

        return result

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute an authenticated POST request and return the JSON response."""
        url = f"{self._base_url}{path}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(url, json=payload, headers=self._headers)
            except httpx.RequestError as e:
                raise PromptShieldClientError(f"Network error: {e}") from e

        return self._handle_response(response)

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Parse and raise for HTTP error status codes."""
        if response.status_code == 401:
            raise AuthenticationError("Authentication failed. Check your API key.", status_code=401)
        if response.status_code == 403:
            raise ForbiddenError("Forbidden. You don't have permission for this operation.", status_code=403)
        if response.status_code == 429:
            raise RateLimitError("Rate limit exceeded.", status_code=429)
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except Exception:
                detail = response.text
            raise PromptShieldClientError(
                f"API error {response.status_code}: {detail}",
                status_code=response.status_code,
            )

        try:
            return response.json()
        except Exception as e:
            raise PromptShieldClientError(f"Failed to parse response: {e}") from e

    # ------------------------------------------------------------------
    # Sync convenience wrappers
    # ------------------------------------------------------------------

    def precheck_sync(
        self,
        prompt: str,
        model: str,
        user_id: str,
        *,
        raise_on_block: bool = False,
        **kwargs: Any,
    ) -> DecisionResult:
        """
        Synchronous wrapper for precheck().

        Creates a temporary event loop if none is running.
        Prefer the async version in async code.
        """
        return asyncio.run(
            self.precheck(prompt, model, user_id, raise_on_block=raise_on_block, **kwargs)
        )

    def proxy_sync(
        self,
        prompt: str,
        model: str,
        user_id: str,
        *,
        raise_on_block: bool = False,
        **kwargs: Any,
    ) -> ProxyResult:
        """
        Synchronous wrapper for proxy().
        """
        return asyncio.run(
            self.proxy(prompt, model, user_id, raise_on_block=raise_on_block, **kwargs)
        )
