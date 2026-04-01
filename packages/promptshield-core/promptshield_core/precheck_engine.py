"""
PreCheckEngine - the main orchestration engine for PromptShield.

Coordinates token estimation, cost estimation, classification, policy
evaluation, and misuse scoring to produce a PromptDecisionResponse.
Used by both Lite and Enterprise editions.
"""

from __future__ import annotations

import logging
from typing import Any

from promptshield_core.classifier import classify_prompt, get_primary_category
from promptshield_core.contracts.request import PromptRequest
from promptshield_core.contracts.response import PromptDecisionResponse
from promptshield_core.cost_estimator import PricingTable, estimate_cost
from promptshield_core.enums import Decision, RouteTarget
from promptshield_core.misuse_detector import MisuseDetector, UsageStats
from promptshield_core.policy_engine import PolicyEngine
from promptshield_core.token_estimator import estimate_output_tokens, estimate_tokens

logger = logging.getLogger(__name__)


class PreCheckEngine:
    """
    Orchestrates the full PromptShield decision flow for a single request.

    The engine is stateless with respect to individual requests. Quota counters
    and usage stats are injected via `usage_stats` at construction time or
    per-call via kwargs.

    Typical usage::

        engine = PreCheckEngine(config=config, pricing_table=pricing)
        response = engine.run(request)
    """

    def __init__(
        self,
        config: dict[str, Any],
        pricing_table: PricingTable,
        usage_stats: UsageStats | None = None,
        daily_requests: int = 0,
        daily_spend_usd: float = 0.0,
    ) -> None:
        """
        Initialise the engine.

        Args:
            config:          Merged policy/routing/threshold configuration dict.
            pricing_table:   Pricing table mapping model names to per-1k costs.
            usage_stats:     Optional UsageStats for misuse score computation.
            daily_requests:  Current daily request count for the user (for quota checks).
            daily_spend_usd: Current daily spend in USD for the user (for quota checks).
        """
        self._config = config
        self._pricing_table = pricing_table
        self._usage_stats = usage_stats or UsageStats()
        self._daily_requests = daily_requests
        self._daily_spend_usd = daily_spend_usd

        messages_config: dict[str, str] = config.get("messages", {})
        self._policy_engine = PolicyEngine(config=config, messages_config=messages_config)
        self._misuse_detector = MisuseDetector()

    def run(self, request: PromptRequest) -> PromptDecisionResponse:
        """
        Execute the full precheck pipeline for a single PromptRequest.

        Pipeline steps:
            1. Estimate input tokens
            2. Classify the prompt
            3. Estimate output tokens (category-aware)
            4. Estimate cost
            5. Evaluate policy rules
            6. Compute misuse score
            7. Assemble and return PromptDecisionResponse

        Args:
            request: The validated PromptRequest to evaluate.

        Returns:
            A fully-populated PromptDecisionResponse.
        """
        logger.debug("PreCheckEngine.run: request_id=%s model=%s user=%s", request.request_id, request.model, request.user_id)

        # Step 1: Estimate input tokens
        input_tokens = estimate_tokens(request.prompt_text, request.model)
        logger.debug("Input token estimate: %d", input_tokens)

        # Step 2: Classify the prompt
        classifications = classify_prompt(request.prompt_text, input_tokens)
        primary_category = get_primary_category(classifications)
        logger.debug("Classifications: %s (primary: %s)", classifications, primary_category)

        # Step 3: Estimate output tokens (uses primary category)
        output_tokens = estimate_output_tokens(input_tokens, primary_category.value)
        logger.debug("Output token estimate: %d", output_tokens)

        # Step 4: Estimate cost
        cost_usd = estimate_cost(
            model=request.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            pricing_table=self._pricing_table,
        )
        logger.debug("Estimated cost: $%.6f", cost_usd)

        # Step 5: Evaluate policy
        policy_result = self._policy_engine.evaluate(
            model=request.model,
            input_tokens=input_tokens,
            estimated_cost_usd=cost_usd,
            classifications=classifications,
            daily_requests=self._daily_requests,
            daily_spend_usd=self._daily_spend_usd,
        )
        logger.debug("Policy decision: %s rules=%s", policy_result.decision, policy_result.triggered_rules)

        # Step 6: Compute misuse score
        misuse_score = self._misuse_detector.compute_score(self._usage_stats)

        # Step 7: Build response
        response = PromptDecisionResponse(
            request_id=request.request_id,
            decision=policy_result.decision,
            classifications=classifications,
            estimated_input_tokens=input_tokens,
            estimated_output_tokens=output_tokens,
            estimated_total_tokens=input_tokens + output_tokens,
            estimated_cost_usd=cost_usd,
            messages=policy_result.messages,
            suggested_route=policy_result.suggested_route,
            misuse_score=misuse_score,
            policy_rules_triggered=policy_result.triggered_rules,
        )

        logger.info(
            "PreCheck complete: request_id=%s decision=%s tokens=%d cost=$%.4f misuse=%.2f",
            request.request_id,
            response.decision,
            response.estimated_total_tokens,
            response.estimated_cost_usd,
            response.misuse_score,
        )
        return response

    @classmethod
    def from_full_config(
        cls,
        full_config: Any,
        usage_stats: UsageStats | None = None,
        daily_requests: int = 0,
        daily_spend_usd: float = 0.0,
    ) -> "PreCheckEngine":
        """
        Construct a PreCheckEngine from a FullConfig object (from promptshield-config).

        Args:
            full_config:     A FullConfig pydantic model instance.
            usage_stats:     Optional usage stats for misuse scoring.
            daily_requests:  Current daily request count.
            daily_spend_usd: Current daily spend.
        """
        # Build a unified flat config dict from the structured config
        config: dict[str, Any] = {}

        if hasattr(full_config, "thresholds"):
            t = full_config.thresholds
            config.update({
                "max_input_tokens": t.max_input_tokens,
                "max_cost_usd": t.max_cost_usd,
                "max_daily_requests": t.max_daily_requests,
                "max_daily_spend_usd": t.max_daily_spend_usd,
                "warn_at_token_pct": t.warn_at_token_pct,
                "warn_at_cost_pct": t.warn_at_cost_pct,
            })

        if hasattr(full_config, "routing"):
            r = full_config.routing
            config.update({
                "warn_on_search_like": r.warn_on_search_like,
                "block_oversized": r.block_oversized,
                "reroute_search_to_web": r.reroute_search_to_web,
                "cheaper_model_fallback": r.cheaper_model_fallback,
                "local_model_fallback": r.local_model_fallback,
                "blocked_models": r.blocked_models,
            })

        if hasattr(full_config, "exceptions") and hasattr(full_config.exceptions, "messages"):
            config["messages"] = full_config.exceptions.messages

        # Build pricing table
        pricing_table: PricingTable = {}
        if hasattr(full_config, "providers") and hasattr(full_config.providers, "models"):
            for model_name, pricing in full_config.providers.models.items():
                if hasattr(pricing, "model_dump"):
                    pricing_table[model_name.lower()] = pricing.model_dump()
                elif isinstance(pricing, dict):
                    pricing_table[model_name.lower()] = pricing

        return cls(
            config=config,
            pricing_table=pricing_table,
            usage_stats=usage_stats,
            daily_requests=daily_requests,
            daily_spend_usd=daily_spend_usd,
        )
