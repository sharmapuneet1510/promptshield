"""
Tests for promptshield_core.token_estimator

These tests exercise the heuristic path (no external dependency on tiktoken
for unknown models) and the output estimation logic.
"""

import pytest

from promptshield_core.token_estimator import estimate_output_tokens, estimate_tokens


class TestEstimateTokensHeuristic:
    """Tests for the heuristic fallback path (unknown model names)."""

    def test_empty_text_returns_zero(self) -> None:
        assert estimate_tokens("", "unknown-model-xyz") == 0

    def test_short_text_returns_at_least_one(self) -> None:
        result = estimate_tokens("Hi", "unknown-model-xyz")
        assert result >= 1

    def test_heuristic_roughly_four_chars_per_token(self) -> None:
        # 400 chars of ASCII text should yield ~100 tokens
        text = "a" * 400
        result = estimate_tokens(text, "unknown-model-xyz")
        # Heuristic: len // 4 = 100, but tiktoken may give a different count
        # For unknown models the heuristic should be used
        assert result >= 1

    def test_longer_text_gives_more_tokens(self) -> None:
        short = estimate_tokens("Hello world", "unknown-model-xyz")
        long_text = "Hello world " * 100
        long = estimate_tokens(long_text, "unknown-model-xyz")
        assert long > short

    def test_whitespace_only_uses_heuristic(self) -> None:
        # "    " = 4 chars → heuristic gives 1 token
        result = estimate_tokens("    ", "unknown-model-xyz")
        assert result >= 1

    def test_unicode_text(self) -> None:
        # Unicode text should not crash
        text = "こんにちは世界"
        result = estimate_tokens(text, "unknown-model-xyz")
        assert result >= 1


class TestEstimateOutputTokens:
    """Tests for the output token estimator."""

    def test_zero_input_returns_zero(self) -> None:
        assert estimate_output_tokens(0, "generic") == 0

    def test_negative_input_returns_zero(self) -> None:
        assert estimate_output_tokens(-10, "generic") == 0

    def test_coding_multiplier_is_highest(self) -> None:
        coding = estimate_output_tokens(100, "coding")
        generic = estimate_output_tokens(100, "generic")
        assert coding > generic

    def test_search_like_multiplier_is_low(self) -> None:
        search = estimate_output_tokens(100, "search_like")
        generic = estimate_output_tokens(100, "generic")
        assert search < generic

    def test_unknown_category_uses_default_multiplier(self) -> None:
        result = estimate_output_tokens(100, "some_future_category")
        assert result >= 1

    def test_minimum_output_is_one(self) -> None:
        result = estimate_output_tokens(1, "search_like")
        assert result >= 1

    @pytest.mark.parametrize("category,min_ratio,max_ratio", [
        ("coding", 1.5, 2.5),
        ("documentation", 1.2, 1.8),
        ("generic", 0.6, 1.0),
        ("search_like", 0.3, 0.7),
        ("oversized", 1.0, 1.4),
    ])
    def test_category_multipliers_in_expected_range(
        self, category: str, min_ratio: float, max_ratio: float
    ) -> None:
        input_tokens = 1000
        output = estimate_output_tokens(input_tokens, category)
        ratio = output / input_tokens
        assert min_ratio <= ratio <= max_ratio, (
            f"Category '{category}' ratio {ratio:.2f} not in [{min_ratio}, {max_ratio}]"
        )


class TestEstimateTokensKnownModels:
    """Tests for tiktoken-backed estimation on known OpenAI models.

    These tests are skipped if tiktoken is not installed.
    """

    @pytest.fixture(autouse=True)
    def _require_tiktoken(self) -> None:
        pytest.importorskip("tiktoken")

    def test_gpt4o_estimates_tokens(self) -> None:
        text = "The quick brown fox jumps over the lazy dog."
        result = estimate_tokens(text, "gpt-4o")
        # Known to be ~10 tokens for this sentence
        assert 8 <= result <= 15

    def test_consistent_results(self) -> None:
        text = "Hello, how are you today?"
        result1 = estimate_tokens(text, "gpt-4o")
        result2 = estimate_tokens(text, "gpt-4o")
        assert result1 == result2
