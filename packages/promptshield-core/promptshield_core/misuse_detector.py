"""
Misuse detection utility.

Computes a misuse_score (0.0 – 1.0) from recent behavioral signals.
The score is advisory and is included in every PromptDecisionResponse for
observability and escalation purposes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Weights for each signal contribution to the total score (sum = 1.0)
_WEIGHT_BLOCK_RATE = 0.40
_WEIGHT_SEARCH_LIKE_RATE = 0.25
_WEIGHT_OVERSIZED_RATE = 0.20
_WEIGHT_HIGH_VOLUME = 0.15

# Thresholds to consider a rate "high"
_HIGH_BLOCK_RATE = 0.20        # 20% of recent requests were blocked
_HIGH_SEARCH_LIKE_RATE = 0.50  # 50% of recent requests were search-like on premium models
_HIGH_OVERSIZED_RATE = 0.15    # 15% of recent requests were oversized
_HIGH_VOLUME_THRESHOLD = 100   # >100 requests in the recent window is a high-volume signal


@dataclass
class UsageStats:
    """
    Container for recent behavioral signals used in misuse detection.

    All counts refer to the same recent time window (e.g. last 24 hours
    or last 100 requests) as managed by the caller.
    """

    recent_block_count: int = 0
    """Number of requests that resulted in a BLOCK decision."""

    recent_search_like_count: int = 0
    """Number of requests classified as SEARCH_LIKE sent to a premium model."""

    recent_oversized_count: int = 0
    """Number of requests classified as OVERSIZED."""

    total_recent_requests: int = 0
    """Total number of requests in the measurement window."""


class MisuseDetector:
    """
    Stateless misuse score calculator.

    Scores are computed from a UsageStats snapshot. Higher scores indicate
    higher likelihood of wasteful or abusive usage patterns.
    """

    def compute_score(self, stats: UsageStats) -> float:
        """
        Compute a misuse score from usage statistics.

        Args:
            stats: A UsageStats snapshot for the user/team.

        Returns:
            Float between 0.0 (no misuse signals) and 1.0 (maximum misuse risk).
        """
        total = stats.total_recent_requests
        if total <= 0:
            return 0.0

        score = 0.0

        # Signal 1: Block rate
        block_rate = stats.recent_block_count / total
        score += _WEIGHT_BLOCK_RATE * min(1.0, block_rate / _HIGH_BLOCK_RATE)

        # Signal 2: Search-like rate (premium model waste)
        search_like_rate = stats.recent_search_like_count / total
        score += _WEIGHT_SEARCH_LIKE_RATE * min(1.0, search_like_rate / _HIGH_SEARCH_LIKE_RATE)

        # Signal 3: Oversized rate
        oversized_rate = stats.recent_oversized_count / total
        score += _WEIGHT_OVERSIZED_RATE * min(1.0, oversized_rate / _HIGH_OVERSIZED_RATE)

        # Signal 4: High-volume usage (absolute count)
        volume_score = min(1.0, total / _HIGH_VOLUME_THRESHOLD)
        score += _WEIGHT_HIGH_VOLUME * volume_score

        result = round(min(1.0, max(0.0, score)), 4)
        logger.debug(
            "Misuse score: %.4f (block_rate=%.2f, search_like_rate=%.2f, "
            "oversized_rate=%.2f, total=%d)",
            result,
            block_rate,
            search_like_rate,
            oversized_rate,
            total,
        )
        return result


def compute_misuse_score(
    recent_block_count: int,
    recent_search_like_count: int,
    recent_oversized_count: int,
    total_recent_requests: int,
) -> float:
    """
    Convenience function for one-off misuse score computation.

    Args:
        recent_block_count:        Number of recent blocked requests.
        recent_search_like_count:  Number of recent search-like requests to premium models.
        recent_oversized_count:    Number of recent oversized requests.
        total_recent_requests:     Total requests in the measurement window.

    Returns:
        Misuse score between 0.0 and 1.0.
    """
    detector = MisuseDetector()
    stats = UsageStats(
        recent_block_count=recent_block_count,
        recent_search_like_count=recent_search_like_count,
        recent_oversized_count=recent_oversized_count,
        total_recent_requests=total_recent_requests,
    )
    return detector.compute_score(stats)
