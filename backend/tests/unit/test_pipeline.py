"""Unit tests for ExperiencePipeline - 8 步经验流水线."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.execution.pipeline import (
    ExperiencePipeline,
    PipelineResult,
    PipelineStepResult,
)


class TestPipelineStepResult:
    """Test PipelineStepResult model."""

    def test_defaults(self) -> None:
        result = PipelineStepResult(step=1, name="test_step")
        assert result.status == "pending"
        assert result.started_at == ""
        assert result.completed_at == ""
        assert result.duration_ms == 0.0
        assert result.output is None
        assert result.error is None

    def test_completed(self) -> None:
        result = PipelineStepResult(
            step=2, name="execute", status="completed",
            started_at="2024-01-01T00:00:00",
            completed_at="2024-01-01T00:00:01",
            duration_ms=1000.0,
            output={"key": "value"},
        )
        assert result.status == "completed"
        assert result.duration_ms == 1000.0
        assert result.output == {"key": "value"}

    def test_failed(self) -> None:
        result = PipelineStepResult(
            step=3, name="deploy", status="failed",
            error="Connection refused",
        )
        assert result.status == "failed"
        assert result.error == "Connection refused"


class TestPipelineResult:
    """Test PipelineResult model."""

    def test_defaults(self) -> None:
        result = PipelineResult(task_id="task-001")
        assert result.status == "running"
        assert result.steps == []
        assert result.experience_id is None
        assert result.total_duration_ms == 0.0
        assert result.error is None

    def test_is_valid_completed_with_experience(self) -> None:
        result = PipelineResult(
            task_id="task-001",
            status="completed",
            experience_id="exp-001",
        )
        assert result.is_valid() is True

    def test_is_valid_no_experience(self) -> None:
        result = PipelineResult(task_id="task-001", status="completed")
        assert result.is_valid() is False

    def test_is_valid_not_completed(self) -> None:
        result = PipelineResult(
            task_id="task-001", status="failed", experience_id="exp-001"
        )
        assert result.is_valid() is False

    def test_is_valid_invalid_status(self) -> None:
        result = PipelineResult(
            task_id="task-001", status="invalid", experience_id="exp-001"
        )
        assert result.is_valid() is False


class TestRuleBasedEvaluate:
    """Test _rule_based_evaluate static method."""

    def test_base_score(self) -> None:
        score = ExperiencePipeline._rule_based_evaluate({})
        assert score == 0.5

    def test_success_bonus(self) -> None:
        score = ExperiencePipeline._rule_based_evaluate({"outcome": {"success": True}})
        assert abs(score - 0.7) < 0.01  # 0.5 + 0.2

    def test_what_worked_bonus(self) -> None:
        score = ExperiencePipeline._rule_based_evaluate({
            "reflection": {"what_worked": ["x"]}
        })
        assert abs(score - 0.6) < 0.01  # 0.5 + 0.1

    def test_what_failed_bonus(self) -> None:
        score = ExperiencePipeline._rule_based_evaluate({
            "reflection": {"what_failed": ["y"]}
        })
        assert abs(score - 0.55) < 0.01  # 0.5 + 0.05

    def test_reusable_patterns_bonus(self) -> None:
        score = ExperiencePipeline._rule_based_evaluate({
            "reusable_patterns": [{"pattern": "x"}]
        })
        assert abs(score - 0.6) < 0.01  # 0.5 + 0.1

    def test_provenance_bonus(self) -> None:
        score = ExperiencePipeline._rule_based_evaluate({
            "provenance": {"agent_signals": [{"contribution": "x"}]}
        })
        assert abs(score - 0.55) < 0.01  # 0.5 + 0.05

    def test_max_score_capped(self) -> None:
        score = ExperiencePipeline._rule_based_evaluate({
            "outcome": {"success": True},
            "reflection": {"what_worked": ["x"], "what_failed": ["y"]},
            "reusable_patterns": [{"pattern": "x"}],
            "provenance": {"agent_signals": [{"contribution": "x"}]},
        })
        # 0.5 + 0.2 + 0.1 + 0.05 + 0.1 + 0.05 = 1.0
        assert score == 1.0

    def test_all_bonuses(self) -> None:
        score = ExperiencePipeline._rule_based_evaluate({
            "outcome": {"success": True},
            "reflection": {"what_worked": ["x"], "what_failed": ["y"]},
            "reusable_patterns": [{"pattern": "x"}],
            "provenance": {"agent_signals": [{"contribution": "x"}]},
        })
        assert score <= 1.0


class TestPipelineRun:
    """Test ExperiencePipeline.run - 完整流水线."""

    @pytest.mark.asyncio
    async def test_run_success(self) -> None:
        """Test successful pipeline run that generates an Experience."""
        session = AsyncMock()

        pipeline = ExperiencePipeline(session)

        # Mock the engine's execute_task
        from app.services.execution.engine import TaskOutput
        mock_output = TaskOutput(
            task_id="test-task",
            success=True,
            result={"intent": "test"},
            steps=[{"step_name": "build", "status": "completed"}],
            tools=["docker"],
            duration=1.5,
        )
        pipeline.engine.execute_task = AsyncMock(return_value=mock_output)

        # Mock repo.create
        mock_experience = MagicMock()
        mock_experience.id = uuid.uuid4()
        pipeline.repo.create = AsyncMock(return_value=mock_experience)
        session.commit = AsyncMock()

        result = await pipeline.run(
            intent="Deploy app",
            context={"domain": "devops", "task_type": "deployment"},
            constraints={"env": "prod"},
        )

        assert result.status == "completed"
        assert result.experience_id is not None
        assert result.is_valid() is True
        assert len(result.steps) == 8
        assert all(s.status == "completed" for s in result.steps)
        assert result.total_duration_ms > 0

    @pytest.mark.asyncio
    async def test_run_with_workflow(self) -> None:
        """Test pipeline with a custom workflow."""
        session = AsyncMock()
        pipeline = ExperiencePipeline(session)

        from app.services.execution.engine import TaskOutput
        mock_output = TaskOutput(
            task_id="test-task",
            success=True,
            steps=[{"step_name": "step1", "status": "completed"}],
            tools=["tool1"],
            duration=2.0,
        )
        pipeline.engine.execute_task = AsyncMock(return_value=mock_output)

        mock_experience = MagicMock()
        mock_experience.id = uuid.uuid4()
        pipeline.repo.create = AsyncMock(return_value=mock_experience)
        session.commit = AsyncMock()

        result = await pipeline.run(
            intent="Custom task",
            workflow=[{"name": "step1", "action": "execute"}],
        )

        assert result.status == "completed"
        assert len(result.steps) == 8

    @pytest.mark.asyncio
    async def test_run_engine_failure(self) -> None:
        """Test pipeline when engine.execute_task raises an exception."""
        session = AsyncMock()
        pipeline = ExperiencePipeline(session)

        pipeline.engine.execute_task = AsyncMock(side_effect=Exception("Engine error"))

        result = await pipeline.run(intent="Failing task")

        assert result.status == "invalid"
        assert result.experience_id is None
        assert result.error is not None
        assert "Engine error" in result.error

    @pytest.mark.asyncio
    async def test_run_repo_create_failure(self) -> None:
        """Test pipeline when repo.create raises an exception."""
        session = AsyncMock()
        pipeline = ExperiencePipeline(session)

        from app.services.execution.engine import TaskOutput
        mock_output = TaskOutput(
            task_id="test-task",
            success=True,
            steps=[{"step_name": "build", "status": "completed"}],
            tools=["docker"],
            duration=1.0,
        )
        pipeline.engine.execute_task = AsyncMock(return_value=mock_output)
        pipeline.repo.create = AsyncMock(side_effect=Exception("DB error"))

        result = await pipeline.run(intent="Test task")

        assert result.status == "invalid"
        assert result.experience_id is None
        assert "DB error" in result.error

    @pytest.mark.asyncio
    async def test_run_failed_task_still_creates_experience(self) -> None:
        """Test that a failed task still generates an Experience (with lower confidence)."""
        session = AsyncMock()
        pipeline = ExperiencePipeline(session)

        from app.services.execution.engine import TaskOutput
        mock_output = TaskOutput(
            task_id="test-task",
            success=False,
            error="Build failed",
            steps=[{"step_name": "build", "status": "failed"}],
            tools=[],
            duration=1.0,
        )
        pipeline.engine.execute_task = AsyncMock(return_value=mock_output)

        mock_experience = MagicMock()
        mock_experience.id = uuid.uuid4()
        pipeline.repo.create = AsyncMock(return_value=mock_experience)
        session.commit = AsyncMock()

        result = await pipeline.run(intent="Failing task")

        assert result.status == "completed"
        assert result.experience_id is not None
        assert result.is_valid() is True

    @pytest.mark.asyncio
    async def test_run_step_names(self) -> None:
        """Test that all 8 step names are present."""
        assert len(ExperiencePipeline.STEP_NAMES) == 8
        assert ExperiencePipeline.STEP_NAMES[0] == "retrieve_similar_experiences"
        assert ExperiencePipeline.STEP_NAMES[1] == "select_best_workflows"
        assert ExperiencePipeline.STEP_NAMES[2] == "execute_task"
        assert ExperiencePipeline.STEP_NAMES[3] == "record_full_trace"
        assert ExperiencePipeline.STEP_NAMES[4] == "generate_experience_object"
        assert ExperiencePipeline.STEP_NAMES[5] == "evaluate_experience"
        assert ExperiencePipeline.STEP_NAMES[6] == "store_into_graph"
        assert ExperiencePipeline.STEP_NAMES[7] == "update_reuse_index"

    @pytest.mark.asyncio
    async def test_execute_step_completed(self) -> None:
        """Test _execute_step returns completed result."""
        session = AsyncMock()
        pipeline = ExperiencePipeline(session)

        step_result = await pipeline._execute_step(1, "test_step", {"key": "value"})

        assert step_result.step == 1
        assert step_result.name == "test_step"
        assert step_result.status == "completed"
        assert step_result.started_at != ""
        assert step_result.completed_at != ""
        assert step_result.duration_ms >= 0
        assert step_result.error is None

    @pytest.mark.asyncio
    async def test_run_no_context(self) -> None:
        """Test pipeline with no context or constraints."""
        session = AsyncMock()
        pipeline = ExperiencePipeline(session)

        from app.services.execution.engine import TaskOutput
        mock_output = TaskOutput(
            task_id="test-task",
            success=True,
            steps=[{"step_name": "execute", "status": "completed"}],
            tools=[],
            duration=0.5,
        )
        pipeline.engine.execute_task = AsyncMock(return_value=mock_output)

        mock_experience = MagicMock()
        mock_experience.id = uuid.uuid4()
        pipeline.repo.create = AsyncMock(return_value=mock_experience)
        session.commit = AsyncMock()

        result = await pipeline.run(intent="Simple task")

        assert result.status == "completed"
        assert result.experience_id is not None
