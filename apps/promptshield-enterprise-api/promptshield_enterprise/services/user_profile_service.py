"""
UserProfileService — computes and updates behavioral profiles for users.

This service is called after every precheck request is saved to the database.
It maintains a running ``UserBehaviorProfile`` row per user by incrementing
counters, recomputing effectiveness and misuse scores, and re-classifying the
user's persona.

Scoring model
-------------

Effectiveness Score (0.0 = wasted, 1.0 = highly productive):
    coding_ratio        * 0.40  — using AI for actual coding work
    documentation_ratio * 0.20  — structured output generation
    allow_rate          * 0.25  — prompts that pass policy (clean usage)
    token_efficiency    * 0.15  — avg tokens per request is in a productive range

Misuse Score (0.0 = clean, 1.0 = high misuse):
    block_rate          * 0.35  — frequently blocked
    search_like_ratio   * 0.30  — using LLM as a search engine
    oversized_ratio     * 0.20  — repeatedly submitting huge prompts
    reroute_web_ratio   * 0.15  — frequently told to use web search

Persona classification (priority-ordered):
    abuser            — misuse >= 0.50 OR block_rate >= 0.30
    web_searcher      — search_like_ratio >= 0.40 OR reroute_web_ratio >= 0.30
    power_user        — effectiveness >= 0.65, total_requests >= 100, misuse < 0.30
    productive_coder  — effectiveness >= 0.65, coding_ratio >= 0.40
    occasional_user   — total_requests < 20
    unknown           — none of the above
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from promptshield_enterprise.storage.models import PromptRecord, UserBehaviorProfile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Token efficiency breakpoints
# ---------------------------------------------------------------------------
_TOKEN_EFFICIENCY_TABLE: list[tuple[int, float]] = [
    (50, 0.2),    # < 50 tokens  — trivially short
    (200, 0.6),   # 50–199       — short but potentially useful
    (2000, 1.0),  # 200–1999     — ideal range
    (5000, 0.7),  # 2000–4999    — long but may be legitimate
]
_TOKEN_EFFICIENCY_DEFAULT = 0.3  # >= 5000 tokens — consistently oversized

# ---------------------------------------------------------------------------
# Score component weights
# ---------------------------------------------------------------------------
_EFF_WEIGHTS = {
    "coding_ratio": 0.40,
    "documentation_ratio": 0.20,
    "allow_rate": 0.25,
    "token_efficiency": 0.15,
}

_MISUSE_WEIGHTS = {
    "block_rate": 0.35,
    "search_like_ratio": 0.30,
    "oversized_ratio": 0.20,
    "reroute_web_ratio": 0.15,
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp *value* to the closed interval [lo, hi]."""
    return max(lo, min(hi, value))


def _token_efficiency(avg_tokens: float) -> float:
    """Map average tokens per request to a 0.0–1.0 efficiency score."""
    for threshold, score in _TOKEN_EFFICIENCY_TABLE:
        if avg_tokens < threshold:
            return score
    return _TOKEN_EFFICIENCY_DEFAULT


class UserProfileService:
    """
    Maintains and queries ``UserBehaviorProfile`` rows.

    All methods that modify state use PostgreSQL's ``INSERT … ON CONFLICT DO
    UPDATE`` (upsert) semantics so they are safe to call concurrently from
    multiple API workers.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Primary update entrypoint
    # ------------------------------------------------------------------

    async def update_profile(self, record: PromptRecord) -> UserBehaviorProfile:
        """
        Update (or create) the behavioral profile for the user referenced in
        *record*.

        The method performs an atomic upsert so concurrent API requests for the
        same user do not produce duplicate rows or lost counter increments.

        Args:
            record: The ``PromptRecord`` that was just saved to the database.

        Returns:
            The updated ``UserBehaviorProfile`` instance (fetched after upsert).
        """
        now = _utcnow()
        decision = (record.decision or "ALLOW").upper()
        classifications: list[str] = list(record.classifications or [])

        # --- build increment vectors ---
        allow_inc = 1 if decision == "ALLOW" else 0
        warn_inc = 1 if decision == "WARN" else 0
        block_inc = 1 if decision == "BLOCK" else 0
        reroute_web_inc = 1 if decision == "REROUTE_WEBSEARCH" else 0
        reroute_cheaper_inc = 1 if decision == "REROUTE_CHEAPER_MODEL" else 0

        coding_inc = 1 if "coding" in classifications else 0
        documentation_inc = 1 if "documentation" in classifications else 0
        search_like_inc = 1 if "search_like" in classifications else 0
        oversized_inc = 1 if "oversized" in classifications else 0
        generic_inc = 1 if "generic" in classifications else 0

        # --- upsert profile row (increment counters) ---
        stmt = pg_insert(UserBehaviorProfile).values(
            user_id=record.user_id,
            team_id=record.team_id,
            total_requests=1,
            allow_count=allow_inc,
            warn_count=warn_inc,
            block_count=block_inc,
            reroute_web_count=reroute_web_inc,
            reroute_cheaper_count=reroute_cheaper_inc,
            total_input_tokens=record.input_tokens,
            total_output_tokens=record.output_tokens,
            total_cost_usd=record.cost_usd,
            coding_count=coding_inc,
            documentation_count=documentation_inc,
            search_like_count=search_like_inc,
            oversized_count=oversized_inc,
            generic_count=generic_inc,
            effectiveness_score=0.0,
            misuse_score=0.0,
            persona="unknown",
            first_seen=now,
            last_seen=now,
            updated_at=now,
        ).on_conflict_do_update(
            index_elements=["user_id"],
            set_={
                "team_id": record.team_id,
                "total_requests": UserBehaviorProfile.total_requests + 1,
                "allow_count": UserBehaviorProfile.allow_count + allow_inc,
                "warn_count": UserBehaviorProfile.warn_count + warn_inc,
                "block_count": UserBehaviorProfile.block_count + block_inc,
                "reroute_web_count": UserBehaviorProfile.reroute_web_count + reroute_web_inc,
                "reroute_cheaper_count": UserBehaviorProfile.reroute_cheaper_count + reroute_cheaper_inc,
                "total_input_tokens": UserBehaviorProfile.total_input_tokens + record.input_tokens,
                "total_output_tokens": UserBehaviorProfile.total_output_tokens + record.output_tokens,
                "total_cost_usd": UserBehaviorProfile.total_cost_usd + record.cost_usd,
                "coding_count": UserBehaviorProfile.coding_count + coding_inc,
                "documentation_count": UserBehaviorProfile.documentation_count + documentation_inc,
                "search_like_count": UserBehaviorProfile.search_like_count + search_like_inc,
                "oversized_count": UserBehaviorProfile.oversized_count + oversized_inc,
                "generic_count": UserBehaviorProfile.generic_count + generic_inc,
                "last_seen": now,
                "updated_at": now,
            },
        )
        await self._session.execute(stmt)
        await self._session.flush()

        # --- reload to get accurate totals ---
        profile = await self.get_profile(record.user_id)
        if profile is None:  # should not happen after upsert, but be defensive
            raise RuntimeError(
                f"UserBehaviorProfile not found after upsert for user_id={record.user_id!r}"
            )

        # --- recompute scores and persona ---
        eff, mis = await self.compute_scores(profile)
        profile.effectiveness_score = eff
        profile.misuse_score = mis
        profile.persona = await self.classify_persona(profile)
        profile.updated_at = now
        self._session.add(profile)
        await self._session.flush()

        return profile

    # ------------------------------------------------------------------
    # Score computation
    # ------------------------------------------------------------------

    async def compute_scores(
        self, profile: UserBehaviorProfile
    ) -> tuple[float, float]:
        """
        Recompute effectiveness and misuse scores from raw profile counters.

        Args:
            profile: The ``UserBehaviorProfile`` instance with up-to-date counts.

        Returns:
            A ``(effectiveness_score, misuse_score)`` tuple, both clamped to
            [0.0, 1.0].
        """
        n = profile.total_requests
        if n == 0:
            return 0.0, 0.0

        # --- effectiveness components ---
        coding_ratio = profile.coding_count / n
        documentation_ratio = profile.documentation_count / n
        allow_rate = profile.allow_count / n

        avg_tokens = profile.total_input_tokens / n
        token_eff = _token_efficiency(avg_tokens)

        effectiveness = (
            coding_ratio * _EFF_WEIGHTS["coding_ratio"]
            + documentation_ratio * _EFF_WEIGHTS["documentation_ratio"]
            + allow_rate * _EFF_WEIGHTS["allow_rate"]
            + token_eff * _EFF_WEIGHTS["token_efficiency"]
        )

        # --- misuse components ---
        block_rate = profile.block_count / n
        search_like_ratio = profile.search_like_count / n
        oversized_ratio = profile.oversized_count / n
        reroute_web_ratio = profile.reroute_web_count / n

        misuse = (
            block_rate * _MISUSE_WEIGHTS["block_rate"]
            + search_like_ratio * _MISUSE_WEIGHTS["search_like_ratio"]
            + oversized_ratio * _MISUSE_WEIGHTS["oversized_ratio"]
            + reroute_web_ratio * _MISUSE_WEIGHTS["reroute_web_ratio"]
        )

        return _clamp(effectiveness), _clamp(misuse)

    # ------------------------------------------------------------------
    # Persona classification
    # ------------------------------------------------------------------

    async def classify_persona(self, profile: UserBehaviorProfile) -> str:
        """
        Classify the user's persona based on their profile scores and ratios.

        Rules are evaluated in priority order; the first matching rule wins.

        Args:
            profile: The ``UserBehaviorProfile`` with up-to-date scores.

        Returns:
            One of: ``abuser``, ``web_searcher``, ``power_user``,
            ``productive_coder``, ``occasional_user``, ``unknown``.
        """
        n = profile.total_requests
        if n == 0:
            return "unknown"

        block_rate = profile.block_count / n
        search_like_ratio = profile.search_like_count / n
        reroute_web_ratio = profile.reroute_web_count / n
        coding_ratio = profile.coding_count / n
        eff = profile.effectiveness_score
        mis = profile.misuse_score

        # Priority 1: abuser — strong misuse or frequent blocks
        if mis >= 0.50 or block_rate >= 0.30:
            return "abuser"

        # Priority 2: web_searcher — primary activity is search-like queries
        if search_like_ratio >= 0.40 or reroute_web_ratio >= 0.30:
            return "web_searcher"

        # Priority 3: power_user — high-volume, effective, clean
        if eff >= 0.65 and n >= 100 and mis < 0.30:
            return "power_user"

        # Priority 4: productive_coder — effective, coding-focused
        if eff >= 0.65 and coding_ratio >= 0.40:
            return "productive_coder"

        # Priority 5: occasional_user — not enough data for reliable classification
        if n < 20:
            return "occasional_user"

        # Default
        return "unknown"

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    async def get_profile(self, user_id: str) -> UserBehaviorProfile | None:
        """
        Fetch the behavioral profile for a single user.

        Args:
            user_id: The user identifier.

        Returns:
            The ``UserBehaviorProfile`` instance, or ``None`` if not found.
        """
        result = await self._session.execute(
            select(UserBehaviorProfile).where(UserBehaviorProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_all_profiles(
        self, min_requests: int = 1
    ) -> list[UserBehaviorProfile]:
        """
        Return all user profiles with at least *min_requests* total requests.

        Args:
            min_requests: Minimum ``total_requests`` value to include
                          (default: 1 — excludes zero-request phantom rows).

        Returns:
            List of ``UserBehaviorProfile`` instances ordered by
            ``total_requests`` descending.
        """
        result = await self._session.execute(
            select(UserBehaviorProfile)
            .where(UserBehaviorProfile.total_requests >= min_requests)
            .order_by(UserBehaviorProfile.total_requests.desc())
        )
        return list(result.scalars().all())

    async def get_profiles_by_persona(
        self, persona: str
    ) -> list[UserBehaviorProfile]:
        """
        Return all user profiles with the given persona label.

        Args:
            persona: One of ``productive_coder``, ``power_user``,
                     ``web_searcher``, ``abuser``, ``occasional_user``,
                     ``unknown``.

        Returns:
            List of matching ``UserBehaviorProfile`` instances ordered by
            ``effectiveness_score`` descending.
        """
        result = await self._session.execute(
            select(UserBehaviorProfile)
            .where(UserBehaviorProfile.persona == persona)
            .order_by(UserBehaviorProfile.effectiveness_score.desc())
        )
        return list(result.scalars().all())

    async def get_leaderboard(
        self,
        metric: str = "effectiveness_score",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Return the top users sorted by the requested metric.

        Args:
            metric: One of ``effectiveness_score``, ``misuse_score``,
                    ``total_requests``. Defaults to ``effectiveness_score``.
                    Results are always sorted descending.
            limit: Maximum number of rows to return (default: 20).

        Returns:
            List of dicts with ``rank``, ``user_id``, ``team_id``,
            ``effectiveness_score``, ``misuse_score``, ``total_requests``,
            and ``persona``.

        Raises:
            ValueError: If *metric* is not one of the accepted values.
        """
        allowed_metrics = {"effectiveness_score", "misuse_score", "total_requests"}
        if metric not in allowed_metrics:
            raise ValueError(
                f"Invalid metric {metric!r}. Must be one of: "
                + ", ".join(sorted(allowed_metrics))
            )

        # Map metric name to the ORM column
        order_col = {
            "effectiveness_score": UserBehaviorProfile.effectiveness_score,
            "misuse_score": UserBehaviorProfile.misuse_score,
            "total_requests": UserBehaviorProfile.total_requests,
        }[metric]

        result = await self._session.execute(
            select(UserBehaviorProfile)
            .where(UserBehaviorProfile.total_requests >= 1)
            .order_by(order_col.desc())
            .limit(limit)
        )
        profiles = result.scalars().all()

        return [
            {
                "rank": idx + 1,
                "user_id": p.user_id,
                "team_id": p.team_id,
                "effectiveness_score": round(p.effectiveness_score, 4),
                "misuse_score": round(p.misuse_score, 4),
                "total_requests": p.total_requests,
                "total_cost_usd": round(p.total_cost_usd, 6),
                "persona": p.persona,
                "last_seen": p.last_seen.isoformat(),
            }
            for idx, p in enumerate(profiles)
        ]
