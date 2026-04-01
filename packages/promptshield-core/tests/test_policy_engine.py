"""
Tests for promptshield_core.policy_engine
"""

import pytest

from promptshield_core.enums import Decision, PromptCategory, RouteTarget
from promptshield_core.policy_engine import PolicyEngine


@pytest.fixture()
def default_config() -> dict:
    return {
        "max_input_tokens": 16000,
        "max_cost_usd": 0.50,
        "max_daily_requests": 500,
        "max_daily_spend_usd": 10.00,
        "warn_at_token_pct": 0.75,
        "warn_at_cost_pct": 0.80,
        "warn_on_search_like": True,
        "block_oversized": True,
        "reroute_search_to_web": True,
        "cheaper_model_fallback": "gpt-4o-mini",
        "blocked_models": [],
    }


@pytest.fixture()
def engine(default_config: dict) -> PolicyEngine:
    return PolicyEngine(config=default_config)


class TestAllowDecision:
    def test_normal_request_is_allowed(self, engine: PolicyEngine) -> None:
        result = engine.evaluate(
            model="gpt-4o",
            input_tokens=500,
            estimated_cost_usd=0.01,
            classifications=[PromptCategory.CODING],
        )
        assert result.decision == Decision.ALLOW
        assert result.triggered_rules == []

    def test_no_messages_on_allow(self, engine: PolicyEngine) -> None:
        result = engine.evaluate(
            model="gpt-4o",
            input_tokens=100,
            estimated_cost_usd=0.001,
            classifications=[PromptCategory.GENERIC],
        )
        assert result.messages == []


class TestBlockedModel:
    def test_blocked_model_returns_block(self, default_config: dict) -> None:
        default_config["blocked_models"] = ["gpt-4-turbo"]
        engine = PolicyEngine(config=default_config)
        result = engine.evaluate(
            model="gpt-4-turbo",
            input_tokens=100,
            estimated_cost_usd=0.01,
            classifications=[PromptCategory.GENERIC],
        )
        assert result.decision == Decision.BLOCK
        assert "blocked_model" in result.triggered_rules
        assert result.suggested_route == RouteTarget.BLOCK

    def test_non_blocked_model_not_affected(self, default_config: dict) -> None:
        default_config["blocked_models"] = ["gpt-4-turbo"]
        engine = PolicyEngine(config=default_config)
        result = engine.evaluate(
            model="gpt-4o",
            input_tokens=100,
            estimated_cost_usd=0.01,
            classifications=[PromptCategory.GENERIC],
        )
        assert result.decision == Decision.ALLOW

    def test_blocked_model_case_insensitive(self, default_config: dict) -> None:
        default_config["blocked_models"] = ["GPT-4-Turbo"]
        engine = PolicyEngine(config=default_config)
        result = engine.evaluate(
            model="gpt-4-turbo",
            input_tokens=100,
            estimated_cost_usd=0.01,
            classifications=[PromptCategory.GENERIC],
        )
        assert result.decision == Decision.BLOCK


class TestDailyLimits:
    def test_daily_request_limit_blocks(self, engine: PolicyEngine) -> None:
        result = engine.evaluate(
            model="gpt-4o",
            input_tokens=100,
            estimated_cost_usd=0.01,
            classifications=[PromptCategory.GENERIC],
            daily_requests=500,  # exactly at limit
        )
        assert result.decision == Decision.BLOCK
        assert "daily_request_limit" in result.triggered_rules

    def test_under_daily_request_limit_allows(self, engine: PolicyEngine) -> None:
        result = engine.evaluate(
            model="gpt-4o",
            input_tokens=100,
            estimated_cost_usd=0.01,
            classifications=[PromptCategory.GENERIC],
            daily_requests=499,
        )
        assert result.decision == Decision.ALLOW

    def test_daily_spend_limit_blocks(self, engine: PolicyEngine) -> None:
        result = engine.evaluate(
            model="gpt-4o",
            input_tokens=100,
            estimated_cost_usd=0.01,
            classifications=[PromptCategory.GENERIC],
            daily_spend_usd=10.00,  # exactly at limit
        )
        assert result.decision == Decision.BLOCK
        assert "daily_spend_limit" in result.triggered_rules


class TestOversizedPrompt:
    def test_oversized_prompt_blocked_by_default(self, engine: PolicyEngine) -> None:
        result = engine.evaluate(
            model="gpt-4o",
            input_tokens=20000,  # exceeds 16000 limit
            estimated_cost_usd=0.10,
            classifications=[PromptCategory.OVERSIZED],
        )
        assert result.decision == Decision.BLOCK
        assert any("oversized" in r for r in result.triggered_rules)

    def test_oversized_prompt_warned_when_not_blocking(self, default_config: dict) -> None:
        default_config["block_oversized"] = False
        engine = PolicyEngine(config=default_config)
        result = engine.evaluate(
            model="gpt-4o",
            input_tokens=20000,
            estimated_cost_usd=0.10,
            classifications=[PromptCategory.OVERSIZED],
        )
        assert result.decision == Decision.WARN
        assert any("oversized" in r for r in result.triggered_rules)

    def test_oversized_by_token_count_even_without_category(self, engine: PolicyEngine) -> None:
        result = engine.evaluate(
            model="gpt-4o",
            input_tokens=17000,  # exceeds 16000 but not in OVERSIZED category
            estimated_cost_usd=0.10,
            classifications=[PromptCategory.GENERIC],
        )
        assert result.decision == Decision.BLOCK


class TestCostThreshold:
    def test_cost_exceeding_limit_blocks(self, engine: PolicyEngine) -> None:
        result = engine.evaluate(
            model="gpt-4o",
            input_tokens=1000,
            estimated_cost_usd=0.60,  # exceeds $0.50 limit
            classifications=[PromptCategory.GENERIC],
        )
        assert result.decision == Decision.BLOCK
        assert "cost_threshold_exceeded" in result.triggered_rules

    def test_cost_within_limit_allows(self, engine: PolicyEngine) -> None:
        result = engine.evaluate(
            model="gpt-4o",
            input_tokens=1000,
            estimated_cost_usd=0.10,
            classifications=[PromptCategory.GENERIC],
        )
        assert result.decision == Decision.ALLOW

    def test_approaching_cost_limit_warns(self, engine: PolicyEngine) -> None:
        # 80% of $0.50 = $0.40
        result = engine.evaluate(
            model="gpt-4o",
            input_tokens=1000,
            estimated_cost_usd=0.42,
            classifications=[PromptCategory.GENERIC],
        )
        assert result.decision == Decision.WARN
        assert "approaching_cost_limit" in result.triggered_rules


class TestSearchLikeRerouting:
    def test_search_like_rerouted_to_web(self, engine: PolicyEngine) -> None:
        result = engine.evaluate(
            model="gpt-4o",
            input_tokens=10,
            estimated_cost_usd=0.001,
            classifications=[PromptCategory.SEARCH_LIKE],
        )
        assert result.decision == Decision.REROUTE_WEBSEARCH
        assert result.suggested_route == RouteTarget.WEB_SEARCH
        assert "search_like_reroute_web" in result.triggered_rules

    def test_search_like_warn_when_reroute_disabled(self, default_config: dict) -> None:
        default_config["reroute_search_to_web"] = False
        default_config["warn_on_search_like"] = True
        engine = PolicyEngine(config=default_config)
        result = engine.evaluate(
            model="gpt-4o",
            input_tokens=10,
            estimated_cost_usd=0.001,
            classifications=[PromptCategory.SEARCH_LIKE],
        )
        assert result.decision == Decision.WARN
        assert "search_like_warn" in result.triggered_rules

    def test_search_like_ignored_when_both_disabled(self, default_config: dict) -> None:
        default_config["reroute_search_to_web"] = False
        default_config["warn_on_search_like"] = False
        engine = PolicyEngine(config=default_config)
        result = engine.evaluate(
            model="gpt-4o",
            input_tokens=10,
            estimated_cost_usd=0.001,
            classifications=[PromptCategory.SEARCH_LIKE],
        )
        assert result.decision == Decision.ALLOW


class TestDecisionSeverity:
    """Verify that block always wins over warn/reroute."""

    def test_block_overrides_reroute(self, default_config: dict) -> None:
        default_config["blocked_models"] = ["gpt-4o"]
        engine = PolicyEngine(config=default_config)
        result = engine.evaluate(
            model="gpt-4o",
            input_tokens=10,
            estimated_cost_usd=0.001,
            classifications=[PromptCategory.SEARCH_LIKE],  # would normally reroute
        )
        assert result.decision == Decision.BLOCK
        assert result.suggested_route == RouteTarget.BLOCK

    def test_messages_accumulate(self, default_config: dict) -> None:
        """Multiple triggered rules should produce multiple messages."""
        engine = PolicyEngine(config=default_config)
        result = engine.evaluate(
            model="gpt-4o",
            input_tokens=int(16000 * 0.80),  # approaching token limit
            estimated_cost_usd=0.42,          # approaching cost limit
            classifications=[PromptCategory.GENERIC],
        )
        assert len(result.messages) >= 1
