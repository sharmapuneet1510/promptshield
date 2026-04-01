"""
SQLAlchemy ORM models for the Enterprise API.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from promptshield_enterprise.storage.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PromptRecord(Base):
    """
    Persistent record of a single precheck request and its decision.
    """

    __tablename__ = "prompt_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    team_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    model: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    # Token and cost metrics
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Decision
    decision: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    classifications: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    misuse_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Prompt data
    prompt_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    redacted_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Routing
    route_taken: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        index=True,
    )


class AuditRecord(Base):
    """
    Immutable audit log for policy changes and admin actions.
    """

    __tablename__ = "audit_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        index=True,
    )


class UserQuota(Base):
    """
    Per-user quota overrides. Rows here override the global policy defaults.
    """

    __tablename__ = "user_quotas"

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    daily_request_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    daily_spend_limit_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )
