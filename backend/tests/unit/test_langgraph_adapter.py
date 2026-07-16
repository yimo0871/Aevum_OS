"""Unit tests for LangGraph adapter."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from aevum.adapters.langgraph import AevumRunner, with_experience_context
from aevum.models import SearchResult


def _make_search_result(similarity=0.8, intent="test"):
    return SearchResult(
        id="exp-1", intent=intent, similarity=similarity,
        confidence_score=0.8, domain="dev", task_type="test",
        success=True, what_worked=["a"], what_failed=[],
        why="reason", reusable_patterns=[], tools=["t"],
    )


class TestAevumRunner:
    """Test AevumRunner wrapper."""

    @patch("aevum.adapters.langgraph.AevumClient")
    def test_invoke_searches_before_execution(self, mock_client_cls):
        """Runner should search Aevum before executing the graph."""
        mock_client = Mock()
        mock_client.search.return_value = [_make_search_result()]
        mock_client.create_experience.return_value = {"id": "new-exp"}

        mock_graph = Mock()
        mock_graph.invoke.return_value = {"success": True, "what_worked": ["x"]}

        runner = AevumRunner(mock_graph, mock_client, domain="devops")
        result = runner.invoke({"task": "deploy app"})

        # Search was called
        mock_client.search.assert_called_once_with("deploy app", domain="devops", limit=5)
        # Experience was stored
        mock_client.create_experience.assert_called_once()
        # Result contains Aevum metadata
        assert result["aevum_experiences_found"] == 1
        assert result["aevum_stored_experience_id"] == "new-exp"
        assert "aevum_duration_s" in result

    @patch("aevum.adapters.langgraph.AevumClient")
    def test_invoke_injects_experiences_into_state(self, mock_client_cls):
        """Runner should inject experience summaries into graph input."""
        mock_client = Mock()
        exp = _make_search_result(similarity=0.9, intent="deploy")
        mock_client.search.return_value = [exp]
        mock_client.create_experience.return_value = {"id": "new"}

        mock_graph = Mock()
        mock_graph.invoke.return_value = {"success": True}

        runner = AevumRunner(mock_graph, mock_client, domain="devops")
        runner.invoke({"task": "deploy"})

        # Check graph.invoke was called with experiences injected
        call_args = mock_graph.invoke.call_args[0][0]
        assert "aevum_experiences" in call_args
        assert len(call_args["aevum_experiences"]) == 1
        assert "aevum_experience_ids" in call_args
        assert call_args["aevum_experience_ids"] == ["exp-1"]

    @patch("aevum.adapters.langgraph.AevumClient")
    def test_invoke_no_experiences_found(self, mock_client_cls):
        """Runner should handle no experiences found gracefully."""
        mock_client = Mock()
        mock_client.search.return_value = []
        mock_client.create_experience.return_value = {"id": "new"}

        mock_graph = Mock()
        mock_graph.invoke.return_value = {"success": True}

        runner = AevumRunner(mock_graph, mock_client, domain="devops")
        result = runner.invoke({"task": "new task"})

        assert result["aevum_experiences_found"] == 0
        # State should have empty lists
        call_args = mock_graph.invoke.call_args[0][0]
        assert call_args["aevum_experiences"] == []

    @patch("aevum.adapters.langgraph.AevumClient")
    def test_invoke_search_failure_no_crash(self, mock_client_cls):
        """Search failure should not crash the execution."""
        mock_client = Mock()
        mock_client.search.side_effect = Exception("Network error")
        mock_client.create_experience.return_value = {"id": "new"}

        mock_graph = Mock()
        mock_graph.invoke.return_value = {"success": True}

        runner = AevumRunner(mock_graph, mock_client, domain="devops")
        result = runner.invoke({"task": "task"})

        # Graph still executed
        mock_graph.invoke.assert_called_once()
        assert result["aevum_experiences_found"] == 0

    @patch("aevum.adapters.langgraph.AevumClient")
    def test_invoke_store_failure_no_crash(self, mock_client_cls):
        """Store failure should not crash the result."""
        mock_client = Mock()
        mock_client.search.return_value = []
        mock_client.create_experience.side_effect = Exception("Store failed")

        mock_graph = Mock()
        mock_graph.invoke.return_value = {"success": True}

        runner = AevumRunner(mock_graph, mock_client, domain="devops")
        result = runner.invoke({"task": "task"})

        assert result["aevum_stored_experience_id"] is None
        # Duration still recorded
        assert "aevum_duration_s" in result

    @patch("aevum.adapters.langgraph.AevumClient")
    def test_invoke_extracts_result_fields(self, mock_client_cls):
        """Runner should extract what_worked/what_failed/tools from result."""
        mock_client = Mock()
        mock_client.search.return_value = []
        mock_client.create_experience.return_value = {"id": "new"}

        mock_graph = Mock()
        mock_graph.invoke.return_value = {
            "success": True,
            "what_worked": ["docker build"],
            "what_failed": ["missing -d flag"],
            "why": "needed background mode",
            "tools": ["docker"],
            "steps": [{"action": "build"}],
            "confidence": 0.85,
        }

        runner = AevumRunner(mock_graph, mock_client, domain="devops")
        runner.invoke({"task": "deploy"})

        # Check create_experience was called with extracted fields
        call_kwargs = mock_client.create_experience.call_args[1]
        assert call_kwargs["outcome"]["success"] is True
        assert call_kwargs["reflection"]["what_worked"] == ["docker build"]
        assert call_kwargs["reflection"]["what_failed"] == ["missing -d flag"]
        assert call_kwargs["confidence_score"] == 0.85
        assert call_kwargs["execution"]["tools"] == ["docker"]


class TestWithExperienceContext:
    """Test the node-level decorator."""

    def test_decorator_injects_experiences(self):
        """Decorator should inject experiences into state."""
        mock_client = Mock()
        mock_client.search.return_value = [_make_search_result()]

        @with_experience_context(mock_client, domain="devops")
        def my_node(state):
            return {"result": state.get("aevum_experiences", [])}

        state = {"task": "deploy app"}
        result = my_node(state)

        assert len(result["result"]) == 1
        mock_client.search.assert_called_once()

    def test_decorator_skips_if_already_present(self):
        """Decorator should not search if experiences already in state."""
        mock_client = Mock()

        @with_experience_context(mock_client, domain="devops")
        def my_node(state):
            return {"result": "ok"}

        state = {"task": "deploy", "aevum_experiences": ["existing"]}
        my_node(state)

        # Should not search again
        mock_client.search.assert_not_called()

    def test_decorator_handles_search_failure(self):
        """Decorator should handle search failure gracefully."""
        mock_client = Mock()
        mock_client.search.side_effect = Exception("Network error")

        @with_experience_context(mock_client, domain="devops")
        def my_node(state):
            return {"result": state.get("aevum_experiences", [])}

        state = {"task": "deploy"}
        result = my_node(state)

        assert result["result"] == []

    def test_decorator_no_task_no_search(self):
        """Decorator should not search if no task in state."""
        mock_client = Mock()

        @with_experience_context(mock_client, domain="devops")
        def my_node(state):
            return {"result": "ok"}

        my_node({})
        mock_client.search.assert_not_called()
