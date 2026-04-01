"""
Token estimation utilities.

Uses tiktoken for known OpenAI-compatible models with a heuristic
fallback (~4 characters per token) for unknown models.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Output multipliers by prompt category - heuristic based on expected response length
_OUTPUT_MULTIPLIERS: dict[str, float] = {
    "coding": 2.0,
    "documentation": 1.5,
    "generic": 0.8,
    "search_like": 0.5,
    "oversized": 1.2,
    "broad_scope": 1.5,
    "repetitive": 0.8,
    "unknown": 1.0,
}

# Cache for tiktoken encoders to avoid repeated construction
_ENCODER_CACHE: dict[str, object] = {}


def estimate_tokens(text: str, model: str) -> int:
    """
    Estimate the number of tokens in *text* for the given *model*.

    Tries to use tiktoken for accurate counting; falls back to a
    character-based heuristic (~4 chars/token) for unsupported models.

    Args:
        text:  The text to measure.
        model: The model identifier (e.g. 'gpt-4o', 'claude-sonnet-4').

    Returns:
        Estimated token count (always >= 1 for non-empty text).
    """
    if not text:
        return 0

    # Try tiktoken for known models
    try:
        import tiktoken  # type: ignore[import-untyped]

        if model not in _ENCODER_CACHE:
            try:
                _ENCODER_CACHE[model] = tiktoken.encoding_for_model(model)
            except KeyError:
                # Try common model families before giving up
                _ENCODER_CACHE[model] = _get_fallback_encoder(model)

        encoder = _ENCODER_CACHE.get(model)
        if encoder is not None:
            return len(encoder.encode(text))  # type: ignore[union-attr]
    except ImportError:
        logger.debug("tiktoken not available, using heuristic estimator")
    except Exception as exc:
        logger.debug("tiktoken failed for model '%s': %s – using heuristic", model, exc)

    # Heuristic fallback: ~4 characters per token (conservative)
    return max(1, len(text) // 4)


def _get_fallback_encoder(model: str) -> object | None:
    """
    Attempt to find an appropriate tiktoken encoder for an unknown model
    by checking common model family prefixes.
    """
    import tiktoken  # type: ignore[import-untyped]

    # Map known prefixes to encoder names
    family_map = [
        ("gpt-4", "cl100k_base"),
        ("gpt-3.5", "cl100k_base"),
        ("text-embedding", "cl100k_base"),
        ("claude", "cl100k_base"),  # Approximate – Claude uses similar tokenization
        ("o1", "o200k_base"),
        ("o3", "o200k_base"),
    ]
    for prefix, encoding_name in family_map:
        if model.startswith(prefix):
            try:
                return tiktoken.get_encoding(encoding_name)
            except Exception:
                pass

    logger.debug("No tiktoken encoder found for model '%s', using heuristic", model)
    return None


def estimate_output_tokens(input_tokens: int, prompt_category: str) -> int:
    """
    Estimate expected output tokens based on the input size and prompt category.

    The multipliers are heuristic approximations of typical response lengths
    per category type. They are intentionally conservative.

    Args:
        input_tokens:    The estimated number of input tokens.
        prompt_category: The PromptCategory string value.

    Returns:
        Estimated output token count (always >= 1 for non-zero input).
    """
    if input_tokens <= 0:
        return 0

    multiplier = _OUTPUT_MULTIPLIERS.get(prompt_category.lower(), 1.0)
    result = int(input_tokens * multiplier)
    return max(1, result)
