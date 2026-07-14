"""API health and integration tests.

Tests that verify API endpoints are properly registered and respond correctly.
These tests use httpx ASGITransport to test without a running server.
"""

import pytest


@pytest.mark.asyncio
class TestAPIHealth:
    """Test API health and basic endpoints."""

    async def test_root_endpoint(self, client) -> None:
        """Test root endpoint returns app info."""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Aevum / 薪火 OS"
        assert "version" in data
        assert "tagline" in data

    async def test_health_endpoint(self, client) -> None:
        """Test health check endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    async def test_openapi_docs_available(self, client) -> None:
        """Test OpenAPI documentation is available."""
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert data["info"]["title"] == "Aevum / 薪火 OS"
        assert "paths" in data


@pytest.mark.asyncio
class TestAPIRoutes:
    """Test that all API routes are properly registered."""

    async def test_experience_routes_registered(self, client) -> None:
        """Test that experience CRUD routes are registered."""
        # GET /api/v1/experiences should return 200 or 500 (DB not connected)
        response = await client.get("/api/v1/experiences")
        assert response.status_code in (200, 500)

    async def test_execution_routes_registered(self, client) -> None:
        """Test that execution routes are registered."""
        # GET /api/v1/execution/tools should return 200 or 500
        response = await client.get("/api/v1/execution/tools")
        assert response.status_code in (200, 500)

    async def test_retrieval_routes_registered(self, client) -> None:
        """Test that retrieval routes are registered."""
        # POST /api/v1/retrieval/search with empty body should return 422
        response = await client.post("/api/v1/retrieval/search", json={})
        assert response.status_code == 422

    async def test_evaluation_routes_registered(self, client) -> None:
        """Test that evaluation routes are registered."""
        # GET /api/v1/evaluation/metrics should return 200 or 500
        response = await client.get("/api/v1/evaluation/metrics")
        assert response.status_code in (200, 500)

    async def test_evaluation_dashboard_registered(self, client) -> None:
        """Test that dashboard route is registered."""
        response = await client.get("/api/v1/evaluation/dashboard")
        assert response.status_code in (200, 500)


@pytest.mark.asyncio
class TestAPIValidation:
    """Test API input validation."""

    async def test_create_experience_requires_fields(self, client) -> None:
        """Test that creating an experience requires mandatory fields."""
        response = await client.post("/api/v1/experiences", json={})
        assert response.status_code == 422

    async def test_create_experience_rejects_empty_intent(self, client) -> None:
        """Test that empty intent is rejected."""
        response = await client.post("/api/v1/experiences", json={
            "context": {"domain": "test", "task_type": "test", "constraints": {}},
            "intent": "",
            "outcome": {"success": True, "metrics": {}},
        })
        assert response.status_code == 422

    async def test_submit_task_requires_intent(self, client) -> None:
        """Test that task submission requires intent."""
        response = await client.post("/api/v1/execution/tasks", json={})
        assert response.status_code == 422

    async def test_search_requires_query(self, client) -> None:
        """Test that search requires a query string."""
        response = await client.post("/api/v1/retrieval/search", json={})
        assert response.status_code == 422

    async def test_confidence_score_bounds_enforced(self, client) -> None:
        """Test that confidence_score is bounded [0, 1]."""
        response = await client.post("/api/v1/experiences", json={
            "context": {"domain": "test", "task_type": "test", "constraints": {}},
            "intent": "test",
            "outcome": {"success": True, "metrics": {}},
            "confidence_score": 1.5,  # Out of bounds
        })
        assert response.status_code == 422
