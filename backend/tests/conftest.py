"""Pytest configuration and fixtures."""

import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for testing API endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_experience_data() -> dict:
    """Sample Experience data for testing."""
    return {
        "context": {
            "domain": "devops",
            "task_type": "deployment",
            "constraints": {"env": "production", "timeout": 300},
        },
        "intent": "Deploy a Python FastAPI application to production",
        "execution": {
            "steps": [
                {"action": "build", "status": "success"},
                {"action": "test", "status": "success"},
                {"action": "deploy", "status": "success"},
            ],
            "tools": ["docker", "kubectl"],
            "trace": {"duration_ms": 45000, "commands_run": 12},
        },
        "outcome": {
            "success": True,
            "metrics": {"deploy_time_s": 45, "rollback_count": 0},
        },
        "reflection": {
            "what_worked": ["Docker multi-stage build", "Health check endpoint"],
            "what_failed": [],
            "why": "Standard deployment pattern with proper health checks",
        },
        "reusable_patterns": [
            {"pattern": "docker-multistage-build", "applicable": True}
        ],
        "confidence_score": 0.92,
        "provenance": {
            "human_signals": [],
            "agent_signals": [{"agent_id": "test-agent", "contribution": "execution"}],
            "external_sources": [],
        },
        "version": 1,
    }
