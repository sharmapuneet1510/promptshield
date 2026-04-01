"""
Analytics service - async database queries for reporting.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from promptshield_enterprise.storage.repository import PromptRepository


class AnalyticsService:
    """
    Provides aggregated analytics queries over the prompt history.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._repo = PromptRepository(session)

    async def get_summary(self) -> dict[str, Any]:
        """
        Get high-level summary statistics.

        Returns:
            Dict with total_requests, total_tokens, total_cost_usd,
            decision_counts, and block_rate.
        """
        stats = await self._repo.get_stats()
        total = stats["total_requests"]
        blocked = stats["decision_counts"].get("BLOCK", 0)
        block_rate = round(blocked / total, 4) if total > 0 else 0.0

        return {
            **stats,
            "block_rate": block_rate,
        }

    async def get_user_stats(self) -> list[dict[str, Any]]:
        """Get per-user usage statistics."""
        return await self._repo.get_user_stats()

    async def get_model_stats(self) -> list[dict[str, Any]]:
        """Get per-model usage statistics."""
        return await self._repo.get_model_stats()

    async def get_misuse_report(self, threshold: float = 0.5) -> list[dict[str, Any]]:
        """
        Get users with misuse score above threshold.

        Args:
            threshold: Minimum misuse score to include (default: 0.5).
        """
        user_stats = await self._repo.get_user_stats()
        return [u for u in user_stats if u.get("avg_misuse_score", 0) >= threshold]
