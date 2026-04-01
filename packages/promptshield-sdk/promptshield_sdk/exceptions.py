"""
PromptShield SDK exception types.
"""

from __future__ import annotations


class PromptShieldClientError(Exception):
    """Base exception for all SDK errors."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class AuthenticationError(PromptShieldClientError):
    """Raised when the API key is missing or invalid (HTTP 401)."""


class ForbiddenError(PromptShieldClientError):
    """Raised when the operation is not permitted (HTTP 403)."""


class RateLimitError(PromptShieldClientError):
    """Raised when the API rate limit has been exceeded (HTTP 429)."""


class BlockedError(PromptShieldClientError):
    """
    Raised when the precheck decision is BLOCK and the caller has opted
    to raise on block (raise_on_block=True).
    """

    def __init__(self, message: str, *, decision_result: object | None = None) -> None:
        super().__init__(message, status_code=None)
        self.decision_result = decision_result
