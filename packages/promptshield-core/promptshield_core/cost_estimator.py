"""
Cost estimation utilities.

Computes estimated USD cost from token counts and a pricing table.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Type alias for pricing table
# Format: {model_name: {"input_per_1k": float, "output_per_1k": float}}
PricingTable = dict[str, dict[str, float]]


def estimate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    pricing_table: PricingTable,
) -> float:
    """
    Estimate the USD cost for a model call given token counts.

    If the model is not found in the pricing table, returns 0.0 and logs
    a debug message. This is intentional – unknown models should not block
    the flow.

    Args:
        model:         The model identifier to look up in the pricing table.
        input_tokens:  Number of estimated input tokens.
        output_tokens: Number of estimated output tokens.
        pricing_table: Mapping of model name to per-1k-token prices.

    Returns:
        Estimated cost in USD as a float. Returns 0.0 if model not found.
    """
    if not pricing_table:
        return 0.0

    pricing = _find_model_pricing(model, pricing_table)
    if pricing is None:
        logger.debug("Model '%s' not found in pricing table, cost estimated as 0.0", model)
        return 0.0

    input_price_per_1k = pricing.get("input_per_1k_usd", pricing.get("input_per_1k", 0.0))
    output_price_per_1k = pricing.get("output_per_1k_usd", pricing.get("output_per_1k", 0.0))

    input_cost = (input_tokens / 1000.0) * input_price_per_1k
    output_cost = (output_tokens / 1000.0) * output_price_per_1k
    total = input_cost + output_cost

    return round(total, 8)


def _find_model_pricing(model: str, pricing_table: PricingTable) -> dict[str, float] | None:
    """
    Look up model pricing with exact match first, then prefix match.

    This allows entries like 'gpt-4o' to match requests for 'gpt-4o-2024-11-20'.
    """
    model_lower = model.lower()

    # Exact match
    if model_lower in pricing_table:
        return pricing_table[model_lower]

    # Try case-insensitive match
    for key, value in pricing_table.items():
        if key.lower() == model_lower:
            return value

    # Prefix match – find the longest matching prefix
    best_match: str | None = None
    for key in pricing_table:
        if model_lower.startswith(key.lower()):
            if best_match is None or len(key) > len(best_match):
                best_match = key

    if best_match is not None:
        return pricing_table[best_match]

    return None


def build_pricing_table_from_config(models_config: dict[str, dict[str, float]]) -> PricingTable:
    """
    Build a normalized pricing table from the providers config dict.

    Args:
        models_config: Dict from providers.yaml models section.

    Returns:
        Normalized PricingTable with lowercase keys.
    """
    return {k.lower(): v for k, v in models_config.items()}
