"""
PromptShield custom exception hierarchy.
"""


class PromptShieldError(Exception):
    """Base exception for all PromptShield errors."""

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code

    def __str__(self) -> str:
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message


class ConfigurationError(PromptShieldError):
    """Raised when configuration is invalid or cannot be loaded."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="CONFIGURATION_ERROR")


class PolicyViolationError(PromptShieldError):
    """Raised when a request violates a policy and must be blocked."""

    def __init__(self, message: str, *, rule: str | None = None) -> None:
        super().__init__(message, code="POLICY_VIOLATION")
        self.rule = rule


class ValidationError(PromptShieldError):
    """Raised when request validation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="VALIDATION_ERROR")


class ProviderError(PromptShieldError):
    """Raised when communication with an upstream provider fails."""

    def __init__(self, message: str, *, provider: str | None = None, status_code: int | None = None) -> None:
        super().__init__(message, code="PROVIDER_ERROR")
        self.provider = provider
        self.status_code = status_code
