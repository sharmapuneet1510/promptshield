"""
Policy evaluation engine.

Evaluates a PromptRequest against a policy configuration and returns a
governance decision, triggered rules, routing suggestion, and messages.

Rules are evaluated in priority order; the most severe decision wins.
Decision severity: BLOCK > REQUIRE_CONFIRMATION > REROUTE_* > WARN > ALLOW
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from promptshield_core.enums import Decision, PromptCategory, RouteTarget

logger = logging.getLogger(__name__)

# Decision severity ranking (higher = more severe)
_SEVERITY: dict[Decision, int] = {
    Decision.ALLOW: 0,
    Decision.WARN: 1,
    Decision.REROUTE_WEBSEARCH: 2,
    Decision.REROUTE_CHEAPER_MODEL: 2,
    Decision.REQUIRE_CONFIRMATION: 3,
    Decision.BLOCK: 4,
}


@dataclass
class PolicyEvaluationResult:
    """Result of running the policy engine."""

    decision: Decision
    triggered_rules: list[str] = field(default_factory=list)
    suggested_route: RouteTarget = RouteTarget.REQUESTED_MODEL
    messages: list[str] = field(default_factory=list)


class PolicyEngine:
    """
    Evaluates a prompt request against a set of policy rules.

    The engine is stateless – all context needed for evaluation must be
    passed in to `evaluate()`. Usage counters (daily_requests, daily_spend)
    should be provided by the caller from a quota service.
    """

    def __init__(self, config: dict[str, Any], messages_config: dict[str, str] | None = None) -> None:
        """
        Initialise the policy engine.

        Args:
            config:          Policy configuration dict (maps to RoutingConfig + ThresholdsConfig).
            messages_config: Optional message templates keyed by rule name.
        """
        self._config = config
        self._messages = messages_config or {}

    def evaluate(
        self,
        *,
        model: str,
        input_tokens: int,
        estimated_cost_usd: float,
        classifications: list[PromptCategory],
        daily_requests: int = 0,
        daily_spend_usd: float = 0.0,
    ) -> PolicyEvaluationResult:
        """
        Run all policy rules and return the aggregate result.

        Args:
            model:             The target model identifier.
            input_tokens:      Estimated input token count.
            estimated_cost_usd: Estimated cost for this request.
            classifications:   List of PromptCategory labels for this prompt.
            daily_requests:    Number of requests made today by this user/team.
            daily_spend_usd:   Total USD spent today by this user/team.

        Returns:
            PolicyEvaluationResult with decision, triggered rules, route, and messages.
        """
        current_decision = Decision.ALLOW
        triggered_rules: list[str] = []
        messages: list[str] = []
        suggested_route = RouteTarget.REQUESTED_MODEL

        cfg = self._config

        # --- Rule 1: Blocked model ---
        blocked_models: list[str] = cfg.get("blocked_models", [])
        if blocked_models and model.lower() in [m.lower() for m in blocked_models]:
            msg = self._format_message("blocked_model", model=model)
            current_decision = self._escalate(current_decision, Decision.BLOCK)
            triggered_rules.append("blocked_model")
            messages.append(msg)
            suggested_route = RouteTarget.BLOCK

        # --- Rule 2: Daily request limit ---
        max_daily_requests = cfg.get("max_daily_requests")
        if max_daily_requests and daily_requests >= max_daily_requests:
            msg = self._format_message("daily_limit")
            current_decision = self._escalate(current_decision, Decision.BLOCK)
            triggered_rules.append("daily_request_limit")
            messages.append(msg)
            suggested_route = RouteTarget.BLOCK

        # --- Rule 3: Daily spend limit ---
        max_daily_spend = cfg.get("max_daily_spend_usd")
        if max_daily_spend and daily_spend_usd >= max_daily_spend:
            msg = self._format_message("daily_spend")
            current_decision = self._escalate(current_decision, Decision.BLOCK)
            triggered_rules.append("daily_spend_limit")
            messages.append(msg)
            suggested_route = RouteTarget.BLOCK

        # --- Rule 4: Oversized prompt ---
        max_input_tokens = cfg.get("max_input_tokens", 16000)
        block_oversized = cfg.get("block_oversized", True)

        if PromptCategory.OVERSIZED in classifications or input_tokens > max_input_tokens:
            if block_oversized:
                msg = self._format_message("oversized_prompt", tokens=input_tokens)
                current_decision = self._escalate(current_decision, Decision.BLOCK)
                triggered_rules.append("oversized_prompt_blocked")
                messages.append(msg)
                suggested_route = RouteTarget.BLOCK
            else:
                msg = self._format_message("oversized_prompt", tokens=input_tokens)
                current_decision = self._escalate(current_decision, Decision.WARN)
                triggered_rules.append("oversized_prompt_warned")
                messages.append(msg)

        # --- Rule 5: Cost threshold ---
        max_cost_usd = cfg.get("max_cost_usd")
        if max_cost_usd and estimated_cost_usd > max_cost_usd:
            msg = self._format_message("cost_threshold", cost=estimated_cost_usd, limit=max_cost_usd)
            current_decision = self._escalate(current_decision, Decision.BLOCK)
            triggered_rules.append("cost_threshold_exceeded")
            messages.append(msg)
            if suggested_route != RouteTarget.BLOCK:
                suggested_route = RouteTarget.CHEAPER_MODEL

        # --- Rule 6: Approaching token limit ---
        warn_at_token_pct = cfg.get("warn_at_token_pct", 0.75)
        if max_input_tokens and input_tokens >= (max_input_tokens * warn_at_token_pct):
            if "oversized_prompt_blocked" not in triggered_rules and "oversized_prompt_warned" not in triggered_rules:
                pct = input_tokens / max_input_tokens
                msg = self._format_message("approaching_token_limit", pct=pct)
                current_decision = self._escalate(current_decision, Decision.WARN)
                triggered_rules.append("approaching_token_limit")
                messages.append(msg)

        # --- Rule 7: Approaching cost limit ---
        warn_at_cost_pct = cfg.get("warn_at_cost_pct", 0.80)
        if max_cost_usd and estimated_cost_usd >= (max_cost_usd * warn_at_cost_pct):
            if "cost_threshold_exceeded" not in triggered_rules:
                pct = estimated_cost_usd / max_cost_usd
                msg = self._format_message("approaching_cost_limit", pct=pct)
                current_decision = self._escalate(current_decision, Decision.WARN)
                triggered_rules.append("approaching_cost_limit")
                messages.append(msg)

        # --- Rule 8: Search-like prompt rerouting ---
        warn_on_search_like = cfg.get("warn_on_search_like", True)
        reroute_search_to_web = cfg.get("reroute_search_to_web", True)

        if PromptCategory.SEARCH_LIKE in classifications and current_decision not in (Decision.BLOCK,):
            if reroute_search_to_web:
                msg = self._format_message("search_like_prompt")
                current_decision = self._escalate(current_decision, Decision.REROUTE_WEBSEARCH)
                triggered_rules.append("search_like_reroute_web")
                messages.append(msg)
                if suggested_route not in (RouteTarget.BLOCK,):
                    suggested_route = RouteTarget.WEB_SEARCH
            elif warn_on_search_like:
                msg = self._format_message("search_like_prompt")
                current_decision = self._escalate(current_decision, Decision.WARN)
                triggered_rules.append("search_like_warn")
                messages.append(msg)

        # --- Rule 9: Reroute to cheaper model ---
        cheaper_model_fallback = cfg.get("cheaper_model_fallback")
        if cheaper_model_fallback and current_decision not in (Decision.BLOCK, Decision.REROUTE_WEBSEARCH):
            # Only suggest cheaper model for high-cost requests
            if max_cost_usd and estimated_cost_usd >= (max_cost_usd * warn_at_cost_pct):
                if suggested_route not in (RouteTarget.BLOCK, RouteTarget.WEB_SEARCH):
                    current_decision = self._escalate(current_decision, Decision.REROUTE_CHEAPER_MODEL)
                    triggered_rules.append("cheaper_model_suggested")
                    suggested_route = RouteTarget.CHEAPER_MODEL

        return PolicyEvaluationResult(
            decision=current_decision,
            triggered_rules=triggered_rules,
            suggested_route=suggested_route,
            messages=messages,
        )

    @staticmethod
    def _escalate(current: Decision, new: Decision) -> Decision:
        """Return whichever decision is more severe."""
        return new if _SEVERITY.get(new, 0) > _SEVERITY.get(current, 0) else current

    def _format_message(self, key: str, **kwargs: Any) -> str:
        """
        Format a message template with the given keyword arguments.
        Falls back to a generic message if the template is not found.
        """
        template = self._messages.get(key, "")
        if not template:
            template = _DEFAULT_MESSAGES.get(key, f"Policy rule triggered: {key}")
        try:
            return template.format(**kwargs)
        except (KeyError, ValueError):
            return template


# Default messages used when no config is provided
_DEFAULT_MESSAGES: dict[str, str] = {
    "oversized_prompt": "Your prompt is too large ({tokens} tokens). Consider splitting it into smaller requests.",
    "search_like_prompt": "This looks like a general knowledge query. Consider using web search instead of a premium model.",
    "cost_threshold": "Estimated cost (${cost:.4f}) exceeds your configured limit of ${limit:.4f}.",
    "daily_limit": "You have reached your daily request limit.",
    "daily_spend": "You have reached your daily spend limit.",
    "approaching_token_limit": "Your prompt is {pct:.0%} of the maximum allowed size.",
    "approaching_cost_limit": "Estimated cost is {pct:.0%} of your configured limit.",
    "blocked_model": "The model '{model}' is not permitted by policy.",
}
