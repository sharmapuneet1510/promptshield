"""
Pydantic v2 configuration models for PromptShield.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_config


class ThresholdsConfig(BaseModel):
    """Token and cost threshold configuration."""

    model_config = model_config(frozen=False)

    max_input_tokens: int = Field(
        default=16000,
        gt=0,
        description="Maximum allowed input tokens per request.",
    )
    max_cost_usd: float = Field(
        default=0.50,
        gt=0.0,
        description="Maximum allowed estimated cost per request in USD.",
    )
    max_daily_requests: int = Field(
        default=500,
        gt=0,
        description="Maximum allowed requests per user per day.",
    )
    max_daily_spend_usd: float = Field(
        default=10.00,
        gt=0.0,
        description="Maximum allowed total spend per user per day in USD.",
    )
    warn_at_token_pct: float = Field(
        default=0.75,
        gt=0.0,
        le=1.0,
        description="Fraction of max_input_tokens at which to issue a warning.",
    )
    warn_at_cost_pct: float = Field(
        default=0.80,
        gt=0.0,
        le=1.0,
        description="Fraction of max_cost_usd at which to issue a warning.",
    )


class RoutingConfig(BaseModel):
    """Routing and rerouting configuration."""

    model_config = model_config(frozen=False)

    warn_on_search_like: bool = Field(
        default=True,
        description="Issue a warning when the prompt looks like a web-search query.",
    )
    block_oversized: bool = Field(
        default=True,
        description="Block requests when the prompt exceeds max_input_tokens.",
    )
    reroute_search_to_web: bool = Field(
        default=True,
        description="Suggest web-search rerouting for search-like prompts.",
    )
    cheaper_model_fallback: str | None = Field(
        default="gpt-4o-mini",
        description="Model identifier to suggest when rerouting to a cheaper model.",
    )
    local_model_fallback: str | None = Field(
        default=None,
        description="Local model identifier to suggest when rerouting to a local model.",
    )
    blocked_models: list[str] = Field(
        default_factory=list,
        description="List of model identifiers that are not allowed.",
    )

    @field_validator("blocked_models", mode="before")
    @classmethod
    def normalize_blocked_models(cls, v: list[str] | None) -> list[str]:
        if v is None:
            return []
        return [m.lower() for m in v]


class ExceptionsConfig(BaseModel):
    """Message template configuration."""

    model_config = model_config(frozen=False)

    messages: dict[str, str] = Field(
        default_factory=dict,
        description="Message templates keyed by rule name. Supports .format() interpolation.",
    )


class ModelPricing(BaseModel):
    """Per-model pricing configuration."""

    model_config = model_config(frozen=False)

    input_per_1k_usd: float = Field(
        default=0.0,
        ge=0.0,
        description="Cost per 1,000 input tokens in USD.",
    )
    output_per_1k_usd: float = Field(
        default=0.0,
        ge=0.0,
        description="Cost per 1,000 output tokens in USD.",
    )


class ProvidersConfig(BaseModel):
    """Provider and model pricing configuration."""

    model_config = model_config(frozen=False)

    models: dict[str, ModelPricing] = Field(
        default_factory=dict,
        description="Mapping of model identifier to pricing configuration.",
    )

    def get_pricing_table(self) -> dict[str, dict[str, float]]:
        """Return a flat pricing table suitable for cost_estimator."""
        return {k.lower(): v.model_dump() for k, v in self.models.items()}


class FullConfig(BaseModel):
    """Aggregated configuration combining all config sections."""

    model_config = model_config(frozen=False)

    thresholds: ThresholdsConfig = Field(default_factory=ThresholdsConfig)
    routing: RoutingConfig = Field(default_factory=RoutingConfig)
    exceptions: ExceptionsConfig = Field(default_factory=ExceptionsConfig)
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)

    def to_flat_dict(self) -> dict:
        """
        Return a flat dictionary representation suitable for PolicyEngine.
        """
        result: dict = {}
        result.update(self.thresholds.model_dump())
        result.update(self.routing.model_dump())
        result["messages"] = self.exceptions.messages
        return result
