"""
promptshield-sdk
================

Python SDK client for the PromptShield Enterprise API.

Quick start::

    from promptshield_sdk import PromptShieldClient

    client = PromptShieldClient(
        base_url="http://localhost:8000",
        api_key="your-api-key",
    )
    result = await client.precheck(
        prompt="Write a Python quicksort implementation",
        model="gpt-4o",
        user_id="alice",
    )
    print(result.decision, result.estimated_cost_usd)
"""

from promptshield_sdk.client import PromptShieldClient
from promptshield_sdk.exceptions import (
    AuthenticationError,
    BlockedError,
    ForbiddenError,
    PromptShieldClientError,
    RateLimitError,
)
from promptshield_sdk.models import DecisionResult, ProxyResult

__version__ = "0.1.0"

__all__ = [
    "PromptShieldClient",
    "DecisionResult",
    "ProxyResult",
    "PromptShieldClientError",
    "AuthenticationError",
    "ForbiddenError",
    "BlockedError",
    "RateLimitError",
]
