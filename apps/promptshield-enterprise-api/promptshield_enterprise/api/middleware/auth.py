"""
API key authentication middleware and dependency functions.
"""

from __future__ import annotations

import logging

from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

from promptshield_enterprise.settings import get_settings

logger = logging.getLogger(__name__)

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(
    request: Request,
    api_key: str | None = Security(_api_key_header),
) -> str:
    """
    FastAPI dependency: require a valid API key.

    Returns the validated API key on success.
    Raises HTTP 401 if the key is missing or invalid.
    """
    settings = get_settings()
    expected_key = settings.PROMPTSHIELD_API_KEY

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide it via the X-API-Key header.",
        )

    if api_key not in (expected_key, settings.PROMPTSHIELD_ADMIN_KEY):
        logger.warning("Invalid API key attempt from %s", request.client)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )

    return api_key


async def require_admin_key(
    api_key: str | None = Security(_api_key_header),
) -> str:
    """
    FastAPI dependency: require the admin API key.

    Raises HTTP 403 if a non-admin key is provided.
    """
    settings = get_settings()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required.",
        )

    if api_key != settings.PROMPTSHIELD_ADMIN_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin API key required for this operation.",
        )

    return api_key
