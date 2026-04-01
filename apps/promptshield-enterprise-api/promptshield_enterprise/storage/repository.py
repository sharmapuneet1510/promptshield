"""
Async repository pattern for database access.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from promptshield_enterprise.storage.models import AuditRecord, PromptRecord


class PromptRepository:
    """
    Async repository for PromptRecord persistence and queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, record: PromptRecord) -> PromptRecord:
        """Persist a new PromptRecord."""
        self._session.add(record)
        await self._session.flush()
        return record

    async def get_by_id(self, record_id: uuid.UUID) -> PromptRecord | None:
        """Retrieve a record by its primary key."""
        result = await self._session.execute(
            select(PromptRecord).where(PromptRecord.id == record_id)
        )
        return result.scalar_one_or_none()

    async def get_by_request_id(self, request_id: uuid.UUID) -> PromptRecord | None:
        """Retrieve a record by its request_id."""
        result = await self._session.execute(
            select(PromptRecord).where(PromptRecord.request_id == request_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: str, limit: int = 50) -> list[PromptRecord]:
        """Retrieve recent records for a specific user."""
        result = await self._session.execute(
            select(PromptRecord)
            .where(PromptRecord.user_id == user_id)
            .order_by(PromptRecord.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_stats(self) -> dict[str, Any]:
        """
        Compute aggregate statistics across all records.
        Returns dict with total_requests, total_tokens, total_cost_usd,
        and decision_counts.
        """
        total_row = await self._session.execute(
            select(
                func.count(PromptRecord.id),
                func.coalesce(func.sum(PromptRecord.total_tokens), 0),
                func.coalesce(func.sum(PromptRecord.cost_usd), 0),
            )
        )
        total_requests, total_tokens, total_cost = total_row.one()

        decision_rows = await self._session.execute(
            select(PromptRecord.decision, func.count(PromptRecord.id))
            .group_by(PromptRecord.decision)
        )
        decision_counts = {row[0]: row[1] for row in decision_rows.all()}

        return {
            "total_requests": total_requests,
            "total_tokens": int(total_tokens),
            "total_cost_usd": float(total_cost),
            "decision_counts": decision_counts,
        }

    async def get_user_stats(self) -> list[dict[str, Any]]:
        """Aggregate usage statistics grouped by user_id."""
        result = await self._session.execute(
            select(
                PromptRecord.user_id,
                func.count(PromptRecord.id).label("request_count"),
                func.coalesce(func.sum(PromptRecord.total_tokens), 0).label("total_tokens"),
                func.coalesce(func.sum(PromptRecord.cost_usd), 0).label("total_cost"),
                func.avg(PromptRecord.misuse_score).label("avg_misuse_score"),
            )
            .group_by(PromptRecord.user_id)
            .order_by(func.count(PromptRecord.id).desc())
        )
        return [
            {
                "user_id": row.user_id,
                "request_count": row.request_count,
                "total_tokens": int(row.total_tokens),
                "total_cost_usd": round(float(row.total_cost), 6),
                "avg_misuse_score": round(float(row.avg_misuse_score or 0), 4),
            }
            for row in result.all()
        ]

    async def get_model_stats(self) -> list[dict[str, Any]]:
        """Aggregate usage statistics grouped by model."""
        result = await self._session.execute(
            select(
                PromptRecord.model,
                func.count(PromptRecord.id).label("request_count"),
                func.coalesce(func.sum(PromptRecord.total_tokens), 0).label("total_tokens"),
                func.coalesce(func.sum(PromptRecord.cost_usd), 0).label("total_cost"),
            )
            .group_by(PromptRecord.model)
            .order_by(func.count(PromptRecord.id).desc())
        )
        return [
            {
                "model": row.model,
                "request_count": row.request_count,
                "total_tokens": int(row.total_tokens),
                "total_cost_usd": round(float(row.total_cost), 6),
            }
            for row in result.all()
        ]


class AuditRepository:
    """
    Async repository for AuditRecord persistence.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def log_event(
        self,
        event_type: str,
        actor: str,
        payload: dict[str, Any],
    ) -> AuditRecord:
        """
        Create and persist an immutable audit log entry.

        Args:
            event_type: Type of event (e.g. 'policy_update', 'quota_change').
            actor:      Identifier of who/what triggered the event.
            payload:    JSON-serializable details about the event.

        Returns:
            The persisted AuditRecord.
        """
        record = AuditRecord(
            event_type=event_type,
            actor=actor,
            payload=payload,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def get_recent(self, limit: int = 100) -> list[AuditRecord]:
        """Retrieve the most recent audit log entries."""
        result = await self._session.execute(
            select(AuditRecord)
            .order_by(AuditRecord.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
