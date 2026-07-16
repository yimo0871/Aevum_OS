"""Unit tests for Aevum SDK."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from aevum import AevumClient, Experience, SearchResult
from aevum.client import MemoryContext


class TestSearchResult:
    """Test SearchResult model."""

    def test_from_api(self) -> None:
        data = {
            "id": "exp-1",
            "intent": "deploy app",
            "similarity": 0.85,
            "confidence_score": 0.9,
            "context": {"domain": "devops", "task_type": "deployment"},
            "outcome": {"success": True, "metrics": {}},
            "reflection": {"what_worked": ["docker build"], "what_failed": [], "why": "worked"},
            "execution": {"tools": ["docker"], "steps": [], "trace": {}},
            "reusable_patterns": [],
        }
        r = SearchResult.from_api(data)
        assert r.id == "exp-1"
        assert r.intent == "deploy app"
        assert r.similarity == 0.85
        assert r.domain == "devops"
        assert r.task_type == "deployment"
        assert r.success is True
        assert r.what_worked == ["docker build"]
        assert r.tools == ["docker"]

    def test_from_api_empty(self) -> None:
        r = SearchResult.from_api({})
        assert r.id == ""
        assert r.similarity == 0.0
        assert r.domain == ""

    def test_summary(self) -> None:
        r = SearchResult(
            id="1", intent="test", similarity=0.8,
            confidence_score=0.9, domain="dev", task_type="test",
            success=True, what_worked=["a"], what_failed=["b"],
            why="reason", reusable_patterns=[], tools=["t"],
        )
        s = r.summary()
        assert "80% match" in s
        assert "test" in s
        assert "worked: a" in s
        assert "failed: b" in s
        assert "tools: t" in s


class TestExperience:
    """Test Experience model."""

    def test_defaults(self) -> None:
        exp = Experience(context={"domain": "d", "task_type": "t"}, intent="test")
        assert exp.outcome == {"success": False, "metrics": {}}
        assert exp.reflection == {"what_worked": [], "what_failed": [], "why": ""}
        assert exp.confidence_score == 0.5
        assert exp.visibility == "private"

    def test_to_api(self) -> None:
        exp = Experience(
            context={"domain": "devops", "task_type": "deploy"},
            intent="deploy app",
            outcome={"success": True, "metrics": {"time": 10}},
            confidence_score=0.8,
            visibility="public",
        )
        d = exp.to_api()
        assert d["context"]["domain"] == "devops"
        assert d["intent"] == "deploy app"
        assert d["outcome"]["success"] is True
        assert d["confidence_score"] == 0.8
        assert d["visibility"] == "public"


class TestAevumClient:
    """Test AevumClient."""

    @patch("aevum.client.httpx.Client")
    def test_init(self, mock_client_cls: Mock) -> None:
        client = AevumClient(api_key="ak_test", base_url="http://test:8000")
        mock_client_cls.assert_called_once()
        call_kwargs = mock_client_cls.call_args[1]
        assert call_kwargs["base_url"] == "http://test:8000"
        assert call_kwargs["headers"]["X-API-Key"] == "ak_test"

    @patch("aevum.client.httpx.Client")
    def test_search(self, mock_client_cls: Mock) -> None:
        mock_resp = Mock()
        mock_resp.json.return_value = [
            {
                "id": "1", "intent": "deploy", "similarity": 0.9,
                "confidence_score": 0.8,
                "context": {"domain": "devops", "task_type": "deploy"},
                "outcome": {"success": True, "metrics": {}},
                "reflection": {"what_worked": [], "what_failed": [], "why": ""},
                "execution": {"tools": [], "steps": [], "trace": {}},
                "reusable_patterns": [],
            }
        ]
        mock_resp.raise_for_status = Mock()
        mock_client = Mock()
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        client = AevumClient(api_key="ak_test")
        results = client.search("deploy app", domain="devops")

        assert len(results) == 1
        assert results[0].intent == "deploy"
        assert results[0].similarity == 0.9
        mock_client.get.assert_called_once()

    @patch("aevum.client.httpx.Client")
    def test_search_empty(self, mock_client_cls: Mock) -> None:
        mock_resp = Mock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = Mock()
        mock_client = Mock()
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        client = AevumClient(api_key="ak_test")
        results = client.search("nothing")
        assert results == []

    @patch("aevum.client.httpx.Client")
    def test_create_experience(self, mock_client_cls: Mock) -> None:
        mock_resp = Mock()
        mock_resp.json.return_value = {"id": "exp-123", "intent": "test"}
        mock_resp.raise_for_status = Mock()
        mock_client = Mock()
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        client = AevumClient(api_key="ak_test")
        result = client.create_experience(
            context={"domain": "dev", "task_type": "test"},
            intent="run tests",
            outcome={"success": True, "metrics": {}},
        )

        assert result["id"] == "exp-123"
        mock_client.post.assert_called_once()
        # Verify request body
        call_kwargs = mock_client.post.call_args[1]
        body = call_kwargs["json"]
        assert body["intent"] == "run tests"
        assert body["context"]["domain"] == "dev"
        assert body["outcome"]["success"] is True

    @patch("aevum.client.httpx.Client")
    def test_get_experience(self, mock_client_cls: Mock) -> None:
        mock_resp = Mock()
        mock_resp.json.return_value = {"id": "exp-1", "intent": "test"}
        mock_resp.raise_for_status = Mock()
        mock_client = Mock()
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        client = AevumClient(api_key="ak_test")
        result = client.get_experience("exp-1")
        assert result["id"] == "exp-1"


class TestMemoryContext:
    """Test MemoryContext (auto-memory)."""

    @patch("aevum.client.httpx.Client")
    def test_memory_full_loop(self, mock_client_cls: Mock) -> None:
        """Test the full memory loop: search -> execute -> store."""
        # Mock search response
        search_resp = Mock()
        search_resp.json.return_value = []
        search_resp.raise_for_status = Mock()

        # Mock create response
        create_resp = Mock()
        create_resp.json.return_value = {"id": "new-exp", "intent": "test"}
        create_resp.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.get.return_value = search_resp
        mock_client.post.return_value = create_resp
        mock_client_cls.return_value = mock_client

        client = AevumClient(api_key="ak_test")

        with client.memory("deploy app", domain="devops") as mem:
            # Initially no relevant experiences
            assert mem.relevant_experiences == []

            # Record outcome
            mem.record_outcome(
                success=True,
                what_worked=["docker build"],
                what_failed=[],
                tools=["docker"],
                confidence=0.9,
            )

        # After exit, create_experience should have been called
        assert mock_client.post.called
        post_body = mock_client.post.call_args[1]["json"]
        assert post_body["intent"] == "deploy app"
        assert post_body["outcome"]["success"] is True
        assert post_body["reflection"]["what_worked"] == ["docker build"]
        assert post_body["confidence_score"] == 0.9

    @patch("aevum.client.httpx.Client")
    def test_memory_with_existing_experience(self, mock_client_cls: Mock) -> None:
        """Test memory when similar experiences exist."""
        search_resp = Mock()
        search_resp.json.return_value = [
            {
                "id": "exp-1", "intent": "deploy", "similarity": 0.85,
                "confidence_score": 0.8,
                "context": {"domain": "devops", "task_type": "deploy"},
                "outcome": {"success": True, "metrics": {}},
                "reflection": {"what_worked": ["docker"], "what_failed": [], "why": ""},
                "execution": {"tools": ["docker"], "steps": [], "trace": {}},
                "reusable_patterns": [],
            }
        ]
        search_resp.raise_for_status = Mock()

        create_resp = Mock()
        create_resp.json.return_value = {"id": "new"}
        create_resp.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.get.return_value = search_resp
        mock_client.post.return_value = create_resp
        mock_client_cls.return_value = mock_client

        client = AevumClient(api_key="ak_test")

        with client.memory("deploy app", domain="devops") as mem:
            assert len(mem.relevant_experiences) == 1
            assert mem.relevant_experiences[0].intent == "deploy"
            assert mem.relevant_experiences[0].similarity == 0.85
            mem.record_outcome(success=True)

    @patch("aevum.client.httpx.Client")
    def test_memory_search_failure_no_block(self, mock_client_cls: Mock) -> None:
        """Search failure should not block execution."""
        mock_client = Mock()
        mock_client.get.side_effect = Exception("Network error")

        create_resp = Mock()
        create_resp.json.return_value = {"id": "new"}
        create_resp.raise_for_status = Mock()
        mock_client.post.return_value = create_resp
        mock_client_cls.return_value = mock_client

        client = AevumClient(api_key="ak_test")

        with client.memory("task") as mem:
            assert mem.relevant_experiences == []
            mem.record_outcome(success=True)

        # Experience still stored
        assert mock_client.post.called

    @patch("aevum.client.httpx.Client")
    def test_memory_store_failure_no_crash(self, mock_client_cls: Mock) -> None:
        """Store failure should not crash the program."""
        search_resp = Mock()
        search_resp.json.return_value = []
        search_resp.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.get.return_value = search_resp
        mock_client.post.side_effect = Exception("Store failed")
        mock_client_cls.return_value = mock_client

        client = AevumClient(api_key="ak_test")

        # Should not raise
        with client.memory("task") as mem:
            mem.record_outcome(success=True)


class TestAevumClientContextManager:
    """Test AevumClient as context manager."""

    @patch("aevum.client.httpx.Client")
    def test_context_manager(self, mock_client_cls: Mock) -> None:
        mock_client = Mock()
        mock_client_cls.return_value = mock_client

        with AevumClient(api_key="ak_test") as client:
            assert client is not None

        # Client should be closed
        mock_client.close.assert_called_once()
