"""
Policy management endpoints.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from promptshield_enterprise.api.middleware.auth import require_admin_key, require_api_key
from promptshield_enterprise.storage.database import get_db
from promptshield_enterprise.storage.repository import AuditRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/policies", tags=["policies"])


class PolicyUpdateRequest(BaseModel):
    """Request body for updating policy configuration."""

    thresholds: dict[str, Any] | None = None
    routing: dict[str, Any] | None = None
    exceptions: dict[str, Any] | None = None


@router.get(
    "",
    summary="Get current policy configuration",
    description="Returns the effective policy configuration (defaults + overrides).",
    response_model=dict,
)
async def get_policies(
    _: Annotated[str, Depends(require_api_key)],
) -> dict[str, Any]:
    """Return the current active policy configuration."""
    from promptshield_config.loader import ConfigLoader
    from promptshield_enterprise.settings import get_settings

    settings = get_settings()
    loader = ConfigLoader(config_dir=settings.CONFIG_DIR)
    config = loader.load_all()
    return config.model_dump()


@router.put(
    "",
    summary="Update policy configuration",
    description=(
        "Update one or more policy sections. "
        "Changes are logged in the audit trail. Admin key required."
    ),
    response_model=dict,
)
async def update_policies(
    update: PolicyUpdateRequest,
    admin_key: Annotated[str, Depends(require_admin_key)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Update policy configuration sections.

    Note: In this implementation, config changes are written to the audit
    log. For persistent overrides, configure a CONFIG_DIR with writable
    YAML files.
    """
    changes: dict[str, Any] = {}
    if update.thresholds:
        changes["thresholds"] = update.thresholds
    if update.routing:
        changes["routing"] = update.routing
    if update.exceptions:
        changes["exceptions"] = update.exceptions

    # Log to audit trail
    audit_repo = AuditRepository(db)
    await audit_repo.log_event(
        event_type="policy_update",
        actor="admin",
        payload={"changes": changes},
    )

    logger.info("Policy updated by admin: sections=%s", list(changes.keys()))

    return {
        "status": "accepted",
        "message": "Policy update logged. Apply changes by updating the config files in CONFIG_DIR.",
        "changes": changes,
    }


@router.get(
    "/audit",
    summary="Policy audit trail",
    description="Returns recent policy change audit records. Admin key required.",
    response_model=list,
)
async def get_audit_trail(
    _: Annotated[str, Depends(require_admin_key)],
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List recent policy audit log entries."""
    audit_repo = AuditRepository(db)
    records = await audit_repo.get_recent(limit=limit)
    return [
        {
            "id": str(r.id),
            "event_type": r.event_type,
            "actor": r.actor,
            "payload": r.payload,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]
