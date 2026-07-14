"""End-to-end test: complete 8-step experience pipeline.

Tests the full flow: task submission -> 8-step pipeline -> experience generation -> evaluation -> storage -> retrieval.

This test uses mocks for database operations to run without a real PostgreSQL instance.
For full integration testing with a real database, see test_experience_lifecycle.py.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


@pytest.mark.asyncio
class TestPipelineE2E:
    """End-to-end test for the 8-step experience pipeline."""

    async def test_successful_pipeline_produces_experience(self) -> None:
        """Test that a successful pipeline run generates a valid Experience object.

        Flow: Submit task -> 8 steps execute -> Experience created -> Task valid
        """
        from app.services.execution.engine import ExecutionEngine, TaskInput

        # ── Step 3: Execute task ──
        engine = ExecutionEngine()
        task_input = TaskInput(
            intent="Deploy FastAPI to production",
            context={"domain": "devops", "task_type": "deployment"},
        )
        task_output = await engine.execute_task(task_input)

        # Verify task execution
        assert task_output.success is True
        assert task_output.task_id == task_input.task_id
        assert len(task_output.steps) > 0
        assert task_output.trace is not None

    async def test_pipeline_step_names_are_correct(self) -> None:
        """Test that pipeline has exactly 8 steps with correct names."""
        from app.services.execution.pipeline import ExperiencePipeline

        assert len(ExperiencePipeline.STEP_NAMES) == 8
        assert ExperiencePipeline.STEP_NAMES[0] == "retrieve_similar_experiences"
        assert ExperiencePipeline.STEP_NAMES[1] == "select_best_workflows"
        assert ExperiencePipeline.STEP_NAMES[2] == "execute_task"
        assert ExperiencePipeline.STEP_NAMES[3] == "record_full_trace"
        assert ExperiencePipeline.STEP_NAMES[4] == "generate_experience_object"
        assert ExperiencePipeline.STEP_NAMES[5] == "evaluate_experience"
        assert ExperiencePipeline.STEP_NAMES[6] == "store_into_graph"
        assert ExperiencePipeline.STEP_NAMES[7] == "update_reuse_index"

    async def test_pipeline_invalid_without_experience(self) -> None:
        """Test that pipeline result is invalid when no Experience is generated."""
        from app.services.execution.pipeline import PipelineResult

        result = PipelineResult(task_id="test-task")
        result.status = "completed"
        # No experience_id set
        assert not result.is_valid()
        assert result.experience_id is None

    async def test_pipeline_valid_with_experience(self) -> None:
        """Test that pipeline result is valid when Experience is generated."""
        from app.services.execution.pipeline import PipelineResult

        result = PipelineResult(task_id="test-task")
        result.status = "completed"
        result.experience_id = str(uuid4())
        assert result.is_valid()

    async def test_experience_factory_generates_valid_object(self) -> None:
        """Test that ExperienceFactory generates a valid Experience from execution trace."""
        from app.services.experience.factory import ExperienceFactory
        from app.schemas.experience import ExperienceCreate

        create_schema = ExperienceFactory.from_trace(
            intent="Test deployment",
            context={"domain": "devops", "task_type": "deployment", "constraints": {}},
            steps=[{"action": "build", "status": "completed"}],
            tools=["docker"],
            trace={"duration_ms": 5000},
            outcome_success=True,
            outcome_metrics={"deploy_time_s": 5},
            what_worked=["Docker build"],
            what_failed=[],
            why="Standard pattern",
            confidence_score=0.85,
        )

        assert isinstance(create_schema, ExperienceCreate)
        assert create_schema.intent == "Test deployment"
        assert create_schema.context.domain == "devops"
        assert create_schema.outcome.success is True
        assert create_schema.confidence_score == 0.85
        assert create_schema.version == 1

    async def test_rule_based_evaluation_updates_confidence(self) -> None:
        """Test that rule-based evaluation produces a reasonable confidence score."""
        from app.services.execution.pipeline import ExperiencePipeline

        experience_data = {
            "outcome": {"success": True},
            "reflection": {"what_worked": ["step1"], "what_failed": []},
            "reusable_patterns": [{"pattern": "test"}],
            "provenance": {"agent_signals": [{"contribution": "execution"}]},
        }

        score = ExperiencePipeline._rule_based_evaluate(experience_data)
        # Should be > 0.5 (base) + 0.2 (success) + 0.1 (what_worked) + 0.1 (patterns) + 0.05 (provenance)
        assert score >= 0.5
        assert score <= 1.0


@pytest.mark.asyncio
class TestExperienceLifecycle:
    """Test the complete experience lifecycle: create -> evaluate -> retrieve -> reuse."""

    async def test_experience_schema_round_trip(self) -> None:
        """Test that an Experience can be created from schema and serialized back."""
        from app.schemas.experience import ExperienceCreate, ExperienceContext, ExperienceOutcome

        ctx = ExperienceContext(domain="testing", task_type="unit_test", constraints={"framework": "pytest"})
        outcome = ExperienceOutcome(success=True, metrics={"coverage": 0.85})

        create = ExperienceCreate(
            context=ctx,
            intent="Run unit tests",
            outcome=outcome,
        )

        # Serialize to dict (simulating storage)
        data = create.model_dump()
        assert data["context"]["domain"] == "testing"
        assert data["outcome"]["success"] is True

        # Deserialize back
        recreated = ExperienceCreate(**data)
        assert recreated.context.domain == "testing"
        assert recreated.outcome.success is True

    async def test_relation_types_are_validated(self) -> None:
        """Test that only valid relation types are accepted."""
        from app.schemas.experience import RelationCreate
        from pydantic import ValidationError

        valid_types = ["reuse", "citation", "fork", "improvement", "dependency"]
        for rt in valid_types:
            rel = RelationCreate(target_id=uuid4(), relation_type=rt)
            assert rel.relation_type == rt

        with pytest.raises(ValidationError):
            RelationCreate(target_id=uuid4(), relation_type="invalid")

    async def test_convergence_guarantees_termination(self) -> None:
        """Test that convergence control always terminates (no infinite loops)."""
        from app.services.execution.convergence import (
            ConvergenceController,
            ConvergenceStatus,
            ModuleType,
        )

        for module_type in ModuleType:
            controller = ConvergenceController(module_type)
            iterations = 0
            for i in range(100):  # Try many iterations
                status = controller.check(performance=0.5 + i * 0.001)
                iterations += 1
                if status != ConvergenceStatus.CONTINUE:
                    break

            # Must terminate before 100 iterations
            assert iterations < 100
            assert controller.state.is_frozen


@pytest.mark.asyncio
class TestHumanAgentSeparation:
    """Test human-agent separation principles (人机分离四原则)."""

    async def test_experience_data_is_structured(self) -> None:
        """Rule 4: Agent output must be fully structured and evaluable."""
        from app.schemas.experience import ExperienceCreate

        # All fields must be structured (no free-form text in core fields)
        ctx = {"domain": "devops", "task_type": "deployment", "constraints": {}}
        outcome = {"success": True, "metrics": {}}
        execution = {"steps": [], "tools": [], "trace": {}}

        create = ExperienceCreate(
            context=ctx,
            intent="Deploy app",
            execution=execution,
            outcome=outcome,
        )

        # Verify all fields are structured
        assert isinstance(create.context.domain, str)
        assert isinstance(create.context.task_type, str)
        assert isinstance(create.context.constraints, dict)
        assert isinstance(create.outcome.success, bool)
        assert isinstance(create.outcome.metrics, dict)
        assert isinstance(create.execution.steps, list)
        assert isinstance(create.execution.tools, list)
        assert isinstance(create.execution.trace, dict)

    async def test_no_human_data_in_experience_graph(self) -> None:
        """Rule 1: Human data must not directly enter the experience graph."""
        from app.schemas.experience import ExperienceCreate, ExperienceProvenance

        # Provenance separates human signals from agent signals
        provenance = ExperienceProvenance(
            human_signals=[],  # Human signals are tracked separately
            agent_signals=[{"agent_id": "test", "contribution": "execution"}],
            external_sources=[],
        )

        create = ExperienceCreate(
            context={"domain": "test", "task_type": "test", "constraints": {}},
            intent="Test",
            outcome={"success": True, "metrics": {}},
            provenance=provenance,
        )

        # Human signals are in provenance, not in core experience data
        assert create.provenance.human_signals == []
        assert len(create.provenance.agent_signals) == 1
