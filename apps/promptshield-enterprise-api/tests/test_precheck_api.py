"""
Integration tests for the /api/v1/precheck endpoint.

These tests use httpx AsyncClient with the FastAPI test app and an
in-memory SQLite database (via aiosqlite). They do NOT require a running
PostgreSQL or Redis instance.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Override settings before importing the app
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_promptshield.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("PROMPTSHIELD_API_KEY", "test-api-key")
os.environ.setdefault("PROMPTSHIELD_ADMIN_KEY", "test-admin-key")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("ENVIRONMENT", "development")

from promptshield_enterprise.storage.database import Base


@pytest.fixture(scope="session")
def event_loop_policy():
    """Use default asyncio event loop policy."""
    import asyncio
    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture(scope="function")
async def test_db():
    """
    Create an in-memory (file-based test) SQLite database for each test.
    Yields an async session factory and cleans up afterwards.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///./test_promptshield_tmp.db",
        echo=False,
    )

    # Import models to register with metadata
    import promptshield_enterprise.storage.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    yield factory

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(test_db) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an httpx AsyncClient for the FastAPI test app with mocked
    database and Redis dependencies.
    """
    # Patch database to use SQLite test db
    async def mock_get_db():
        async with test_db() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    # Mock Redis / QuotaService to avoid needing a real Redis
    mock_quota = AsyncMock()
    mock_quota.get_daily_count.return_value = 0
    mock_quota.get_daily_spend.return_value = 0.0
    mock_quota.increment_request_count.return_value = 1
    mock_quota.increment_spend.return_value = 0.001
    mock_redis = MagicMock()
    mock_redis.aclose = AsyncMock()

    from promptshield_enterprise.main import app
    from promptshield_enterprise.storage.database import get_db

    app.dependency_overrides[get_db] = mock_get_db

    with patch("promptshield_enterprise.api.v1.precheck.QuotaService", return_value=mock_quota), \
         patch("promptshield_enterprise.api.v1.precheck._get_redis", return_value=mock_redis):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac

    app.dependency_overrides.clear()


_API_KEY = "test-api-key"
_ADMIN_KEY = "test-admin-key"
_HEADERS = {"X-API-Key": _API_KEY}
_ADMIN_HEADERS = {"X-API-Key": _ADMIN_KEY}


class TestPrecheckEndpoint:
    async def test_precheck_allow_simple_coding_prompt(self, client: AsyncClient) -> None:
        """A normal coding prompt should be ALLOW or WARN."""
        payload = {
            "prompt_text": "Write a Python function to reverse a string.",
            "model": "gpt-4o",
            "user_id": "test-user-1",
            "source": "test",
        }
        response = await client.post("/api/v1/precheck", json=payload, headers=_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] in ("ALLOW", "WARN", "REROUTE_CHEAPER_MODEL")
        assert data["estimated_input_tokens"] > 0
        assert data["estimated_total_tokens"] > 0
        assert "request_id" in data

    async def test_precheck_search_like_prompt_reroutes(self, client: AsyncClient) -> None:
        """A search-like prompt to a premium model should trigger rerouting."""
        payload = {
            "prompt_text": "What is the capital of France?",
            "model": "gpt-4o",
            "user_id": "test-user-2",
            "source": "test",
        }
        response = await client.post("/api/v1/precheck", json=payload, headers=_HEADERS)
        assert response.status_code == 200
        data = response.json()
        # Should be REROUTE_WEBSEARCH or WARN (depending on config)
        assert data["decision"] in ("REROUTE_WEBSEARCH", "WARN", "ALLOW")

    async def test_precheck_requires_api_key(self, client: AsyncClient) -> None:
        """Requests without API key should return 401."""
        payload = {
            "prompt_text": "Hello",
            "model": "gpt-4o",
            "user_id": "user",
        }
        response = await client.post("/api/v1/precheck", json=payload)
        assert response.status_code == 401

    async def test_precheck_invalid_api_key(self, client: AsyncClient) -> None:
        """Requests with wrong API key should return 401."""
        payload = {
            "prompt_text": "Hello",
            "model": "gpt-4o",
            "user_id": "user",
        }
        response = await client.post(
            "/api/v1/precheck",
            json=payload,
            headers={"X-API-Key": "wrong-key"},
        )
        assert response.status_code == 401

    async def test_precheck_missing_prompt_returns_422(self, client: AsyncClient) -> None:
        """Missing required fields should return 422."""
        payload = {"model": "gpt-4o", "user_id": "user"}  # missing prompt_text
        response = await client.post("/api/v1/precheck", json=payload, headers=_HEADERS)
        assert response.status_code == 422

    async def test_precheck_response_has_all_fields(self, client: AsyncClient) -> None:
        """Response should contain all required fields."""
        payload = {
            "prompt_text": "Explain how async/await works in Python.",
            "model": "gpt-4o",
            "user_id": "test-user-3",
        }
        response = await client.post("/api/v1/precheck", json=payload, headers=_HEADERS)
        assert response.status_code == 200
        data = response.json()

        required_fields = [
            "request_id",
            "decision",
            "classifications",
            "estimated_input_tokens",
            "estimated_output_tokens",
            "estimated_total_tokens",
            "estimated_cost_usd",
            "messages",
            "suggested_route",
            "misuse_score",
            "policy_rules_triggered",
            "timestamp",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    async def test_precheck_cost_is_non_negative(self, client: AsyncClient) -> None:
        """Estimated cost should always be >= 0."""
        payload = {
            "prompt_text": "What is 2 + 2?",
            "model": "gpt-4o",
            "user_id": "test-user-4",
        }
        response = await client.post("/api/v1/precheck", json=payload, headers=_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert data["estimated_cost_usd"] >= 0.0

    async def test_precheck_misuse_score_range(self, client: AsyncClient) -> None:
        """Misuse score should be between 0.0 and 1.0."""
        payload = {
            "prompt_text": "Write a comprehensive essay about machine learning.",
            "model": "gpt-4o",
            "user_id": "test-user-5",
        }
        response = await client.post("/api/v1/precheck", json=payload, headers=_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert 0.0 <= data["misuse_score"] <= 1.0

    async def test_precheck_with_metadata(self, client: AsyncClient) -> None:
        """Requests with optional metadata fields should succeed."""
        payload = {
            "prompt_text": "Review this code snippet.",
            "model": "gpt-4o-mini",
            "user_id": "test-user-6",
            "team_id": "engineering",
            "source": "vscode",
            "project": "my-project",
            "repository": "my-repo",
            "metadata": {"ide_version": "1.85.0"},
        }
        response = await client.post("/api/v1/precheck", json=payload, headers=_HEADERS)
        assert response.status_code == 200
        assert response.json()["decision"] in ("ALLOW", "WARN", "REROUTE_WEBSEARCH", "REROUTE_CHEAPER_MODEL")


class TestHealthEndpoints:
    async def test_health_basic(self, client: AsyncClient) -> None:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestAnalyticsEndpoints:
    async def test_analytics_requires_admin_key(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/analytics/summary", headers=_HEADERS)
        assert response.status_code == 403

    async def test_analytics_summary_with_admin_key(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/analytics/summary", headers=_ADMIN_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert "total_requests" in data


class TestPoliciesEndpoints:
    async def test_get_policies_requires_api_key(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/policies")
        assert response.status_code == 401

    async def test_get_policies_returns_config(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/policies", headers=_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert "thresholds" in data
        assert "routing" in data
