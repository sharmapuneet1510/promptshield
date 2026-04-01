"""
SDK response models mirroring the Enterprise API response types.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_config


class DecisionResult(BaseModel):
    """
    Mirrors PromptDecisionResponse from the Enterprise API.
    Returned by PromptShieldClient.precheck() and precheck_sync().
    """

    model_config = model_config(frozen=True)

    request_id: UUID
    decision: str
    classifications: list[str] = Field(default_factory=list)
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_total_tokens: int
    estimated_cost_usd: float
    messages: list[str] = Field(default_factory=list)
    suggested_route: str
    misuse_score: float
    policy_rules_triggered: list[str] = Field(default_factory=list)
    timestamp: datetime

    @property
    def is_allowed(self) -> bool:
        """True if the request is permitted (ALLOW or WARN)."""
        return self.decision in ("ALLOW", "WARN")

    @property
    def is_blocked(self) -> bool:
        """True if the request is blocked."""
        return self.decision == "BLOCK"

    @property
    def requires_reroute(self) -> bool:
        """True if the decision suggests rerouting."""
        return self.decision in ("REROUTE_WEBSEARCH", "REROUTE_CHEAPER_MODEL")


class ProxyResult(BaseModel):
    """
    Combined precheck decision + provider response.
    Returned by PromptShieldClient.proxy() and proxy_sync().
    """

    model_config = model_config(frozen=True)

    decision: DecisionResult
    content: str | None = None
    provider: str | None = None
    actual_model: str | None = None
    actual_input_tokens: int = 0
    actual_output_tokens: int = 0
    forwarded: bool = False
    message: str | None = None
