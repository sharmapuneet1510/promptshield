"""
PromptDecisionResponse contract - the output schema of the precheck engine.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from promptshield_core.enums import Decision, PromptCategory, RouteTarget


class PromptDecisionResponse(BaseModel):
    """
    The full result of a PromptShield precheck evaluation.

    Contains the governance decision, token and cost estimates, prompt
    classifications, policy rules that fired, and routing suggestions.
    """

    model_config = ConfigDict(frozen=True)

    request_id: UUID = Field(
        ...,
        description="The request_id echoed from the original PromptRequest.",
    )
    decision: Decision = Field(
        ...,
        description="The final governance decision for this request.",
    )
    classifications: list[PromptCategory] = Field(
        default_factory=list,
        description="List of prompt categories assigned to this request.",
    )
    estimated_input_tokens: int = Field(
        ...,
        ge=0,
        description="Estimated number of input tokens in the prompt.",
    )
    estimated_output_tokens: int = Field(
        ...,
        ge=0,
        description="Estimated number of output tokens the model will generate.",
    )
    estimated_total_tokens: int = Field(
        ...,
        ge=0,
        description="Sum of estimated input and output tokens.",
    )
    estimated_cost_usd: float = Field(
        ...,
        ge=0.0,
        description="Estimated cost in USD for this request.",
    )
    messages: list[str] = Field(
        default_factory=list,
        description="Human-readable messages explaining the decision (warnings, tips, block reasons).",
    )
    suggested_route: RouteTarget = Field(
        ...,
        description="The recommended routing target based on the decision.",
    )
    misuse_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Misuse likelihood score from 0.0 (clean) to 1.0 (high misuse risk).",
    )
    policy_rules_triggered: list[str] = Field(
        default_factory=list,
        description="Names of policy rules that were triggered during evaluation.",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when this decision was produced.",
    )

    @field_validator("estimated_total_tokens", mode="before")
    @classmethod
    def compute_total_if_zero(cls, v: int) -> int:
        """Allow total to be provided directly."""
        return v

    @property
    def is_permitted(self) -> bool:
        """Returns True if the request may proceed (ALLOW or WARN)."""
        return self.decision in (Decision.ALLOW, Decision.WARN)

    @property
    def is_blocked(self) -> bool:
        """Returns True if the request must not be forwarded."""
        return self.decision == Decision.BLOCK
