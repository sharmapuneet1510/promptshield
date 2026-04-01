"""
Enterprise PolicyEngine that integrates with Redis quota counters.
"""

from __future__ import annotations

import logging
from typing import Any

from promptshield_core.enums import PromptCategory
from promptshield_core.policy_engine import PolicyEngine as CorePolicyEngine, PolicyEvaluationResult

logger = logging.getLogger(__name__)


class EnterprisePolicyEngine:
    """
    Enterprise wrapper around the core PolicyEngine.

    Extends the core engine by fetching live quota counters from the
    QuotaService before evaluation.
    """

    def __init__(self, config: dict[str, Any], messages_config: dict[str, str] | None = None) -> None:
        self._core = CorePolicyEngine(config=config, messages_config=messages_config)
        self._config = config

    async def evaluate_with_quota(
        self,
        *,
        model: str,
        user_id: str,
        input_tokens: int,
        estimated_cost_usd: float,
        classifications: list[PromptCategory],
        quota_service: Any,
    ) -> PolicyEvaluationResult:
        """
        Evaluate policy with live quota counter lookup from Redis.

        Args:
            model:               Target model identifier.
            user_id:             The requesting user.
            input_tokens:        Estimated input token count.
            estimated_cost_usd:  Estimated cost for this request.
            classifications:     Prompt category labels.
            quota_service:       QuotaService instance for Redis lookups.

        Returns:
            PolicyEvaluationResult.
        """
        # Fetch current daily counts from Redis
        daily_requests = 0
        daily_spend = 0.0
        try:
            daily_requests = await quota_service.get_daily_count(user_id)
            daily_spend = await quota_service.get_daily_spend(user_id)
        except Exception as e:
            logger.warning("Failed to fetch quota counts for user %s: %s", user_id, e)

        return self._core.evaluate(
            model=model,
            input_tokens=input_tokens,
            estimated_cost_usd=estimated_cost_usd,
            classifications=classifications,
            daily_requests=daily_requests,
            daily_spend_usd=daily_spend,
        )
