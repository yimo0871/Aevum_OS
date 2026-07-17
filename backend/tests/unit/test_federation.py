"""Unit tests for FederationService - 联邦网络."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.federation.federation_service import FederationService


# ── Helpers ──


def _make_mock_response(
    status_code: int = 200, json_data: list | dict | None = None
) -> MagicMock:
    """Build a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or []
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    return resp


# ── Initialization & peer management tests ──


class TestFederationInit:
    """Test FederationService initialization and peer management."""

    def test_init_sets_node_info(self) -> None:
        service = FederationService("http://node1:8000/", "node-1")
        assert service.node_url == "http://node1:8000"
        assert service.node_id == "node-1"

    def test_init_strips_trailing_slash(self) -> None:
        service = FederationService("http://node1:8000///", "node-1")
        assert service.node_url == "http://node1:8000"

    def test_list_peers_empty_by_default(self) -> None:
        service = FederationService("http://node1:8000", "node-1")
        assert service.list_peers() == []

    def test_register_peer(self) -> None:
        service = FederationService("http://node1:8000", "node-1")
        peer = service.register_peer("http://node2:8000/", "node-2")
        assert peer["url"] == "http://node2:8000"
        assert peer["id"] == "node-2"
        assert len(service.list_peers()) == 1

    def test_register_multiple_peers(self) -> None:
        service = FederationService("http://node1:8000", "node-1")
        service.register_peer("http://node2:8000", "node-2")
        service.register_peer("http://node3:8000", "node-3")
        assert len(service.list_peers()) == 2

    def test_register_peer_overwrites_same_id(self) -> None:
        service = FederationService("http://node1:8000", "node-1")
        service.register_peer("http://node2:8000", "node-2")
        service.register_peer("http://node2:9000", "node-2")
        assert len(service.list_peers()) == 1
        assert service.list_peers()[0]["url"] == "http://node2:9000"

    def test_unregister_peer(self) -> None:
        service = FederationService("http://node1:8000", "node-1")
        service.register_peer("http://node2:8000", "node-2")
        result = service.unregister_peer("node-2")
        assert result is True
        assert service.list_peers() == []

    def test_unregister_peer_not_found(self) -> None:
        service = FederationService("http://node1:8000", "node-1")
        result = service.unregister_peer("unknown")
        assert result is False


# ── sync_experience tests ──


class TestSyncExperience:
    """Test FederationService.sync_experience."""

    @pytest.mark.asyncio
    async def test_sync_to_single_peer_success(self) -> None:
        service = FederationService("http://node1:8000", "node-1")
        service.register_peer("http://node2:8000", "node-2")

        mock_resp = _make_mock_response(status_code=201, json_data={"id": "abc"})
        with patch("app.services.federation.federation_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            results = await service.sync_experience(uuid.uuid4())

        assert results["node-2"] is True

    @pytest.mark.asyncio
    async def test_sync_to_multiple_peers(self) -> None:
        service = FederationService("http://node1:8000", "node-1")
        service.register_peer("http://node2:8000", "node-2")
        service.register_peer("http://node3:8000", "node-3")

        mock_resp = _make_mock_response(status_code=200)
        with patch("app.services.federation.federation_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            results = await service.sync_experience(uuid.uuid4())

        assert results["node-2"] is True
        assert results["node-3"] is True

    @pytest.mark.asyncio
    async def test_sync_no_peers_returns_empty(self) -> None:
        service = FederationService("http://node1:8000", "node-1")
        results = await service.sync_experience(uuid.uuid4())
        assert results == {}

    @pytest.mark.asyncio
    async def test_sync_peer_failure_does_not_break(self) -> None:
        service = FederationService("http://node1:8000", "node-1")
        service.register_peer("http://node2:8000", "node-2")
        service.register_peer("http://node3:8000", "node-3")

        with patch("app.services.federation.federation_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            # First call (node-2) raises, second (node-3) succeeds
            mock_client.post = AsyncMock(
                side_effect=[httpx.ConnectError("connection refused"), _make_mock_response(201)]
            )
            mock_client_cls.return_value = mock_client

            results = await service.sync_experience(uuid.uuid4())

        assert results["node-2"] is False
        assert results["node-3"] is True


# ── fetch_from_peer tests ──


class TestFetchFromPeer:
    """Test FederationService.fetch_from_peer."""

    @pytest.mark.asyncio
    async def test_fetch_success(self) -> None:
        service = FederationService("http://node1:8000", "node-1")
        service.register_peer("http://node2:8000", "node-2")

        peer_results = [{"experience": {"id": "abc"}, "score": 0.9}]
        mock_resp = _make_mock_response(status_code=200, json_data=peer_results)
        with patch("app.services.federation.federation_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            results = await service.fetch_from_peer("node-2", "deploy", limit=5)

        assert results == peer_results

    @pytest.mark.asyncio
    async def test_fetch_unregistered_peer_raises(self) -> None:
        service = FederationService("http://node1:8000", "node-1")
        with pytest.raises(ValueError, match="未注册"):
            await service.fetch_from_peer("unknown", "deploy")

    @pytest.mark.asyncio
    async def test_fetch_peer_connection_error_returns_empty(self) -> None:
        service = FederationService("http://node1:8000", "node-1")
        service.register_peer("http://node2:8000", "node-2")

        with patch("app.services.federation.federation_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(
                side_effect=httpx.ConnectError("connection refused")
            )
            mock_client_cls.return_value = mock_client

            results = await service.fetch_from_peer("node-2", "deploy")

        assert results == []


# ── federated_search tests ──


class TestFederatedSearch:
    """Test FederationService.federated_search."""

    @pytest.mark.asyncio
    async def test_federated_search_combines_local_and_peer(self) -> None:
        service = FederationService("http://node1:8000", "node-1")
        service.register_peer("http://node2:8000", "node-2")

        peer_results = [{"experience": {"id": "abc"}, "score": 0.9}]
        mock_resp = _make_mock_response(status_code=200, json_data=peer_results)
        with patch("app.services.federation.federation_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            local = [{"experience_id": "local-1", "intent": "test"}]
            result = await service.federated_search(
                "deploy", local_search=local, limit=5
            )

        assert result["query"] == "deploy"
        assert result["local_results"] == local
        assert result["peer_results"]["node-2"] == peer_results
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_federated_search_no_peers(self) -> None:
        service = FederationService("http://node1:8000", "node-1")
        local = [{"experience_id": "local-1"}]
        result = await service.federated_search("deploy", local_search=local)

        assert result["local_results"] == local
        assert result["peer_results"] == {}
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_federated_search_peer_failure_graceful(self) -> None:
        service = FederationService("http://node1:8000", "node-1")
        service.register_peer("http://node2:8000", "node-2")
        service.register_peer("http://node3:8000", "node-3")

        with patch("app.services.federation.federation_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(
                side_effect=httpx.ConnectError("connection refused")
            )
            mock_client_cls.return_value = mock_client

            result = await service.federated_search("deploy")

        # Both peers failed but search still returns
        assert len(result["errors"]) == 2
        assert "node-2" in result["errors"]
        assert "node-3" in result["errors"]
        assert result["peer_results"] == {}

    @pytest.mark.asyncio
    async def test_federated_search_partial_peer_failure(self) -> None:
        service = FederationService("http://node1:8000", "node-1")
        service.register_peer("http://node2:8000", "node-2")
        service.register_peer("http://node3:8000", "node-3")

        good_resp = _make_mock_response(status_code=200, json_data=[{"id": "ok"}])
        with patch("app.services.federation.federation_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(
                side_effect=[httpx.ConnectError("down"), good_resp]
            )
            mock_client_cls.return_value = mock_client

            result = await service.federated_search("deploy")

        assert "node-2" in result["errors"]
        assert "node-3" not in result["errors"]
        assert result["peer_results"]["node-3"] == [{"id": "ok"}]
