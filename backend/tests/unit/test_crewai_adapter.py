"""Unit tests for CrewAI adapter."""

from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from aevum.adapters.crewai import AevumCrewWrapper
from aevum.models import SearchResult


def _make_search_result(similarity: float = 0.8, intent: str = "test", rid: str = "exp-1") -> SearchResult:
    return SearchResult(
        id=rid,
        intent=intent,
        similarity=similarity,
        confidence_score=0.8,
        domain="dev",
        task_type="test",
        success=True,
        what_worked=["a"],
        what_failed=[],
        why="reason",
        reusable_patterns=[],
        tools=["t"],
    )


class TestAevumCrewWrapper:
    """Test AevumCrewWrapper wrapper."""

    def test_kickoff_searches_before_execution(self) -> None:
        """kickoff should search Aevum before executing the crew."""
        mock_client = Mock()
        mock_client.search.return_value = [_make_search_result()]
        mock_client.create_experience.return_value = {"id": "new-exp"}

        mock_crew = Mock()
        mock_crew.kickoff.return_value = {"success": True, "what_worked": ["x"]}

        wrapper = AevumCrewWrapper(mock_crew, mock_client, domain="devops")
        result = wrapper.kickoff(inputs={"task": "deploy app"})

        # Search was called with the task before crew execution
        mock_client.search.assert_called_once_with("deploy app", domain="devops", limit=5)
        # Crew was executed
        mock_crew.kickoff.assert_called_once()
        # Result contains Aevum metadata
        assert result["aevum_experiences_found"] == 1
        assert result["aevum_stored_experience_id"] == "new-exp"
        assert "aevum_duration_s" in result

    def test_kickoff_injects_experiences_into_inputs(self) -> None:
        """kickoff should inject experience summaries into crew inputs."""
        mock_client = Mock()
        exp = _make_search_result(similarity=0.9, intent="deploy", rid="exp-1")
        mock_client.search.return_value = [exp]
        mock_client.create_experience.return_value = {"id": "new"}

        mock_crew = Mock()
        mock_crew.kickoff.return_value = {"success": True}

        wrapper = AevumCrewWrapper(mock_crew, mock_client, domain="devops")
        wrapper.kickoff(inputs={"topic": "deploy"})

        # crew.kickoff called with inputs containing experiences
        call_inputs = mock_crew.kickoff.call_args[1]["inputs"]
        assert "aevum_experiences" in call_inputs
        assert len(call_inputs["aevum_experiences"]) == 1
        assert call_inputs["aevum_experience_ids"] == ["exp-1"]

    def test_kickoff_stores_experience_after_execution(self) -> None:
        """kickoff should store execution as a new experience after running."""
        mock_client = Mock()
        mock_client.search.return_value = []
        mock_client.create_experience.return_value = {"id": "stored-1"}

        mock_crew = Mock()
        mock_crew.kickoff.return_value = {"success": True, "what_worked": ["docker"]}

        wrapper = AevumCrewWrapper(mock_crew, mock_client, domain="devops", task_type="deploy")
        result = wrapper.kickoff(inputs={"task": "deploy"})

        mock_client.create_experience.assert_called_once()
        call_kwargs = mock_client.create_experience.call_args[1]
        assert call_kwargs["intent"] == "deploy"
        assert call_kwargs["context"]["domain"] == "devops"
        assert call_kwargs["context"]["task_type"] == "deploy"
        assert call_kwargs["outcome"]["success"] is True
        assert call_kwargs["reflection"]["what_worked"] == ["docker"]
        assert result["aevum_stored_experience_id"] == "stored-1"

    def test_kickoff_search_failure_no_crash(self) -> None:
        """Search failure should not crash execution."""
        mock_client = Mock()
        mock_client.search.side_effect = Exception("Network error")
        mock_client.create_experience.return_value = {"id": "new"}

        mock_crew = Mock()
        mock_crew.kickoff.return_value = {"success": True}

        wrapper = AevumCrewWrapper(mock_crew, mock_client, domain="devops")
        result = wrapper.kickoff(inputs={"task": "task"})

        # Crew still executed
        mock_crew.kickoff.assert_called_once()
        assert result["aevum_experiences_found"] == 0
        # Empty experiences injected
        call_inputs = mock_crew.kickoff.call_args[1]["inputs"]
        assert call_inputs["aevum_experiences"] == []

    def test_kickoff_store_failure_no_crash(self) -> None:
        """Store failure should not crash the result."""
        mock_client = Mock()
        mock_client.search.return_value = []
        mock_client.create_experience.side_effect = Exception("Store failed")

        mock_crew = Mock()
        mock_crew.kickoff.return_value = {"success": True}

        wrapper = AevumCrewWrapper(mock_crew, mock_client, domain="devops")
        result = wrapper.kickoff(inputs={"task": "task"})

        assert result["aevum_stored_experience_id"] is None
        # Duration still recorded
        assert "aevum_duration_s" in result

    def test_kickoff_no_experiences_found(self) -> None:
        """kickoff should handle no experiences found gracefully."""
        mock_client = Mock()
        mock_client.search.return_value = []
        mock_client.create_experience.return_value = {"id": "new"}

        mock_crew = Mock()
        mock_crew.kickoff.return_value = {"success": True}

        wrapper = AevumCrewWrapper(mock_crew, mock_client, domain="devops")
        result = wrapper.kickoff(inputs={"task": "new task"})

        assert result["aevum_experiences_found"] == 0
        call_inputs = mock_crew.kickoff.call_args[1]["inputs"]
        assert call_inputs["aevum_experiences"] == []
        assert call_inputs["aevum_experience_ids"] == []

    def test_kickoff_result_metadata(self) -> None:
        """Result should contain full Aevum metadata."""
        mock_client = Mock()
        mock_client.search.return_value = [
            _make_search_result(0.9, "deploy", "exp-1"),
            _make_search_result(0.7, "other", "exp-2"),
        ]
        mock_client.create_experience.return_value = {"id": "new"}

        mock_crew = Mock()
        mock_crew.kickoff.return_value = {"success": True}

        wrapper = AevumCrewWrapper(mock_crew, mock_client, domain="devops")
        result = wrapper.kickoff(inputs={"task": "deploy"})

        assert result["aevum_experiences_found"] == 2
        assert result["aevum_stored_experience_id"] == "new"
        assert "aevum_duration_s" in result
        assert len(result["aevum_experiences"]) == 2
        assert result["aevum_experience_ids"] == ["exp-1", "exp-2"]

    def test_kickoff_extracts_result_fields(self) -> None:
        """kickoff should extract what_worked/what_failed/tools from result dict."""
        mock_client = Mock()
        mock_client.search.return_value = []
        mock_client.create_experience.return_value = {"id": "new"}

        mock_crew = Mock()
        mock_crew.kickoff.return_value = {
            "success": True,
            "what_worked": ["docker build"],
            "what_failed": ["missing -d flag"],
            "why": "needed background mode",
            "tools": ["docker"],
            "steps": [{"action": "build"}],
            "confidence": 0.85,
        }

        wrapper = AevumCrewWrapper(mock_crew, mock_client, domain="devops")
        wrapper.kickoff(inputs={"task": "deploy"})

        call_kwargs = mock_client.create_experience.call_args[1]
        assert call_kwargs["outcome"]["success"] is True
        assert call_kwargs["reflection"]["what_worked"] == ["docker build"]
        assert call_kwargs["reflection"]["what_failed"] == ["missing -d flag"]
        assert call_kwargs["reflection"]["why"] == "needed background mode"
        assert call_kwargs["confidence_score"] == 0.85
        assert call_kwargs["execution"]["tools"] == ["docker"]
        assert call_kwargs["execution"]["steps"] == [{"action": "build"}]

    def test_kickoff_no_inputs(self) -> None:
        """kickoff should work with inputs=None."""
        mock_client = Mock()
        mock_client.search.return_value = []
        mock_client.create_experience.return_value = {"id": "new"}

        mock_crew = Mock()
        mock_crew.kickoff.return_value = {"success": True}

        wrapper = AevumCrewWrapper(mock_crew, mock_client, domain="devops")
        result = wrapper.kickoff()

        mock_crew.kickoff.assert_called_once()
        # search called with empty task string
        mock_client.search.assert_called_once_with("", domain="devops", limit=5)
        assert result["aevum_experiences_found"] == 0

    def test_kickoff_attaches_metadata_to_object_result(self) -> None:
        """When result is an object (not dict), metadata is attached as attributes."""
        mock_client = Mock()
        mock_client.search.return_value = []
        mock_client.create_experience.return_value = {"id": "obj-1"}

        mock_result = MagicMock()
        mock_result.json_dict = None  # 模拟 CrewOutput.json_dict 为 None
        mock_crew = Mock()
        mock_crew.kickoff.return_value = mock_result

        wrapper = AevumCrewWrapper(mock_crew, mock_client, domain="devops")
        result = wrapper.kickoff(inputs={"task": "deploy"})

        # 元数据作为属性挂载到对象结果上
        assert result.aevum_stored_experience_id == "obj-1"
        assert result.aevum_experiences_found == 0
        # 兜底：self 上也能取到
        assert wrapper.aevum_stored_experience_id == "obj-1"

    def test_kickoff_passes_extra_kwargs(self) -> None:
        """Extra kwargs should be forwarded to crew.kickoff."""
        mock_client = Mock()
        mock_client.search.return_value = []
        mock_client.create_experience.return_value = {"id": "new"}

        mock_crew = Mock()
        mock_crew.kickoff.return_value = {"success": True}

        wrapper = AevumCrewWrapper(mock_crew, mock_client, domain="devops")
        wrapper.kickoff(inputs={"task": "deploy"}, config={"key": "val"})

        call_kwargs = mock_crew.kickoff.call_args[1]
        assert call_kwargs["config"] == {"key": "val"}

    async def test_kickoff_async_support(self) -> None:
        """kickoff_async should await crew.kickoff_async and store experience."""
        mock_client = Mock()
        mock_client.search.return_value = []
        mock_client.create_experience.return_value = {"id": "async-1"}

        mock_crew = Mock()
        mock_crew.kickoff_async = AsyncMock(return_value={"success": True})

        wrapper = AevumCrewWrapper(mock_crew, mock_client, domain="devops")
        result = await wrapper.kickoff_async(inputs={"task": "deploy"})

        mock_crew.kickoff_async.assert_awaited_once()
        mock_client.create_experience.assert_called_once()
        assert result["aevum_stored_experience_id"] == "async-1"
        assert "aevum_duration_s" in result

    def test_kickoff_constraints_forwarded(self) -> None:
        """constraints in inputs should be forwarded to stored experience context."""
        mock_client = Mock()
        mock_client.search.return_value = []
        mock_client.create_experience.return_value = {"id": "new"}

        mock_crew = Mock()
        mock_crew.kickoff.return_value = {"success": True}

        wrapper = AevumCrewWrapper(mock_crew, mock_client, domain="devops")
        wrapper.kickoff(inputs={"task": "deploy", "constraints": {"env": "prod"}})

        call_kwargs = mock_client.create_experience.call_args[1]
        assert call_kwargs["context"]["constraints"] == {"env": "prod"}


class TestAevumCrewWrapperImport:
    """Test that the adapter imports cleanly without crewai installed."""

    def test_module_imports_without_crewai(self) -> None:
        """Importing the module should not require crewai."""
        import aevum.adapters.crewai as crewai_mod

        assert hasattr(crewai_mod, "AevumCrewWrapper")
        assert crewai_mod.AevumCrewWrapper is AevumCrewWrapper
