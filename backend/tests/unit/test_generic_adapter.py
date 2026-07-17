"""Unit tests for Generic adapter (AevumHook / AevumContext)."""

from unittest.mock import Mock

import pytest

from aevum.adapters.generic import AevumContext, AevumHook
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


class TestAevumHookBeforeExecution:
    """Test AevumHook.before_execution."""

    def test_before_execution_searches_and_returns_summaries(self) -> None:
        """before_execution should search and return experience summary strings."""
        mock_client = Mock()
        mock_client.search.return_value = [_make_search_result(0.9, "deploy")]

        hook = AevumHook(mock_client, domain="devops")
        summaries = hook.before_execution("deploy app")

        mock_client.search.assert_called_once_with("deploy app", domain="devops", limit=5)
        assert len(summaries) == 1
        assert isinstance(summaries[0], str)
        assert "90% match" in summaries[0]
        assert "deploy" in summaries[0]

    def test_before_execution_uses_override_domain(self) -> None:
        """before_execution should use the domain argument over the default."""
        mock_client = Mock()
        mock_client.search.return_value = []

        hook = AevumHook(mock_client, domain="devops")
        hook.before_execution("task", domain="frontend")

        mock_client.search.assert_called_once_with("task", domain="frontend", limit=5)

    def test_before_execution_search_failure_returns_empty(self) -> None:
        """Search failure should degrade to an empty list."""
        mock_client = Mock()
        mock_client.search.side_effect = Exception("Network error")

        hook = AevumHook(mock_client, domain="devops")
        summaries = hook.before_execution("task")

        assert summaries == []

    def test_before_execution_no_experiences_found(self) -> None:
        """No experiences found should return an empty list."""
        mock_client = Mock()
        mock_client.search.return_value = []

        hook = AevumHook(mock_client, domain="devops")
        summaries = hook.before_execution("unknown task")

        assert summaries == []


class TestAevumHookAfterExecution:
    """Test AevumHook.after_execution."""

    def test_after_execution_stores_experience(self) -> None:
        """after_execution should store an experience via the client."""
        mock_client = Mock()
        mock_client.create_experience.return_value = {"id": "new-1"}

        hook = AevumHook(mock_client, domain="devops", task_type="deploy", visibility="public")
        exp = hook.after_execution(
            "deploy app",
            result="done",
            success=True,
            what_worked=["docker"],
            what_failed=["missing flag"],
            why="background mode needed",
            tools=["docker", "kubectl"],
            confidence=0.9,
        )

        mock_client.create_experience.assert_called_once()
        call_kwargs = mock_client.create_experience.call_args[1]
        assert call_kwargs["intent"] == "deploy app"
        assert call_kwargs["context"]["domain"] == "devops"
        assert call_kwargs["context"]["task_type"] == "deploy"
        assert call_kwargs["outcome"]["success"] is True
        assert call_kwargs["reflection"]["what_worked"] == ["docker"]
        assert call_kwargs["reflection"]["what_failed"] == ["missing flag"]
        assert call_kwargs["confidence_score"] == 0.9
        assert call_kwargs["visibility"] == "public"
        assert exp == {"id": "new-1"}

    def test_after_execution_result_stringified_in_trace(self) -> None:
        """The result should be stringified and stored in execution.trace."""
        mock_client = Mock()
        mock_client.create_experience.return_value = {"id": "new"}

        hook = AevumHook(mock_client, domain="devops")
        hook.after_execution("task", result={"arbitrary": "output"})

        call_kwargs = mock_client.create_experience.call_args[1]
        assert "result" in call_kwargs["execution"]["trace"]
        assert "arbitrary" in call_kwargs["execution"]["trace"]["result"]

    def test_after_execution_includes_duration_metric(self) -> None:
        """duration_s should be recorded in outcome metrics when provided."""
        mock_client = Mock()
        mock_client.create_experience.return_value = {"id": "new"}

        hook = AevumHook(mock_client, domain="devops")
        hook.after_execution("task", duration_s=12.345)

        call_kwargs = mock_client.create_experience.call_args[1]
        assert call_kwargs["outcome"]["metrics"]["duration_s"] == 12.35

    def test_after_execution_store_failure_returns_none(self) -> None:
        """Store failure should return None and not raise."""
        mock_client = Mock()
        mock_client.create_experience.side_effect = Exception("Store failed")

        hook = AevumHook(mock_client, domain="devops")
        exp = hook.after_execution("task", success=True)

        assert exp is None


class TestAevumContext:
    """Test AevumContext context manager (full lifecycle)."""

    def test_context_manager_full_lifecycle(self) -> None:
        """Context manager should search on enter and store on exit."""
        mock_client = Mock()
        mock_client.search.return_value = [_make_search_result(0.85, "deploy")]
        mock_client.create_experience.return_value = {"id": "ctx-1"}

        with AevumContext(mock_client, task="deploy app", domain="devops") as ctx:
            # Experiences available inside the block
            assert len(ctx.experiences) == 1
            assert "deploy" in ctx.experiences[0]
            ctx.record(
                success=True,
                what_worked=["docker"],
                what_failed=[],
                why="standard pattern",
                tools=["docker"],
                confidence=0.9,
            )

        # search happened on enter
        mock_client.search.assert_called_once_with("deploy app", domain="devops", limit=5)
        # create happened on exit
        mock_client.create_experience.assert_called_once()
        assert ctx.stored_experience == {"id": "ctx-1"}

    def test_context_manager_exit_stores_experience_fields(self) -> None:
        """Exit should store the experience with recorded fields."""
        mock_client = Mock()
        mock_client.search.return_value = []
        mock_client.create_experience.return_value = {"id": "ctx-2"}

        with AevumContext(mock_client, task="task", domain="devops", task_type="deploy") as ctx:
            ctx.record(
                success=False,
                what_worked=[],
                what_failed=["bad flag"],
                why="wrong flag",
                tools=["kubectl"],
                steps=[{"action": "apply"}],
                metrics={"retries": 2},
                confidence=0.3,
            )

        call_kwargs = mock_client.create_experience.call_args[1]
        assert call_kwargs["outcome"]["success"] is False
        assert call_kwargs["reflection"]["what_failed"] == ["bad flag"]
        assert call_kwargs["execution"]["tools"] == ["kubectl"]
        assert call_kwargs["execution"]["steps"] == [{"action": "apply"}]
        assert call_kwargs["outcome"]["metrics"]["retries"] == 2
        assert "duration_s" in call_kwargs["outcome"]["metrics"]

    def test_context_manager_search_failure_graceful(self) -> None:
        """Search failure on enter should not block execution."""
        mock_client = Mock()
        mock_client.search.side_effect = Exception("Network error")
        mock_client.create_experience.return_value = {"id": "new"}

        with AevumContext(mock_client, task="task", domain="devops") as ctx:
            assert ctx.experiences == []
            ctx.record(success=True)

        # Store still happened on exit
        mock_client.create_experience.assert_called_once()

    def test_context_manager_store_failure_graceful(self) -> None:
        """Store failure on exit should not raise."""
        mock_client = Mock()
        mock_client.search.return_value = []
        mock_client.create_experience.side_effect = Exception("Store failed")

        # Should not raise
        with AevumContext(mock_client, task="task", domain="devops") as ctx:
            ctx.record(success=True)

        assert ctx.stored_experience is None

    def test_context_manager_record_outcome_alias(self) -> None:
        """record_outcome should behave like record (MemoryContext compatibility)."""
        mock_client = Mock()
        mock_client.search.return_value = []
        mock_client.create_experience.return_value = {"id": "new"}

        with AevumContext(mock_client, task="task", domain="devops") as ctx:
            ctx.record_outcome(success=True, what_worked=["a"], tools=["t"])

        call_kwargs = mock_client.create_experience.call_args[1]
        assert call_kwargs["outcome"]["success"] is True
        assert call_kwargs["reflection"]["what_worked"] == ["a"]
        assert call_kwargs["execution"]["tools"] == ["t"]

    def test_context_manager_records_duration(self) -> None:
        """Context manager should measure and store a non-negative duration."""
        mock_client = Mock()
        mock_client.search.return_value = []
        mock_client.create_experience.return_value = {"id": "new"}

        with AevumContext(mock_client, task="task", domain="devops") as ctx:
            ctx.record(success=True)

        call_kwargs = mock_client.create_experience.call_args[1]
        duration = call_kwargs["outcome"]["metrics"]["duration_s"]
        assert isinstance(duration, float)
        assert duration >= 0.0

    def test_context_manager_default_success_false(self) -> None:
        """Without calling record(), success defaults to False on exit."""
        mock_client = Mock()
        mock_client.search.return_value = []
        mock_client.create_experience.return_value = {"id": "new"}

        with AevumContext(mock_client, task="task", domain="devops"):
            pass  # no record() call

        call_kwargs = mock_client.create_experience.call_args[1]
        assert call_kwargs["outcome"]["success"] is False
