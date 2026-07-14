"""Unit tests for ExperienceFactory."""

import pytest


class TestExperienceFactory:
    """Test ExperienceFactory - 从执行记录生成 Experience 对象."""

    def test_from_trace_creates_valid_schema(self) -> None:
        from app.schemas.experience import ExperienceCreate
        from app.services.experience.factory import ExperienceFactory

        create_schema = ExperienceFactory.from_trace(
            intent="Deploy FastAPI to production",
            context={"domain": "devops", "task_type": "deployment", "constraints": {"env": "prod"}},
            steps=[{"action": "build", "status": "success"}],
            tools=["docker", "kubectl"],
            trace={"duration_ms": 45000},
            outcome_success=True,
            outcome_metrics={"deploy_time_s": 45},
            what_worked=["Docker multi-stage build"],
            what_failed=[],
            why="Standard deployment pattern",
            confidence_score=0.92,
        )

        assert isinstance(create_schema, ExperienceCreate)
        assert create_schema.intent == "Deploy FastAPI to production"
        assert create_schema.context.domain == "devops"
        assert create_schema.context.task_type == "deployment"
        assert create_schema.outcome.success is True
        assert create_schema.confidence_score == 0.92
        assert create_schema.version == 1

    def test_from_trace_defaults(self) -> None:
        from app.services.experience.factory import ExperienceFactory

        create_schema = ExperienceFactory.from_trace(
            intent="Test task",
            context={},
            steps=[],
            tools=[],
            trace={},
            outcome_success=True,
            outcome_metrics={},
        )

        # Defaults should be applied
        assert create_schema.context.domain == "general"
        assert create_schema.context.task_type == "unknown"
        assert create_schema.reflection.what_worked == []
        assert create_schema.reflection.what_failed == []
        assert create_schema.confidence_score == 0.5
        assert len(create_schema.provenance.agent_signals) == 1

    def test_from_trace_to_model(self) -> None:
        from app.models.experience import Experience
        from app.services.experience.factory import ExperienceFactory

        model = ExperienceFactory.from_trace_to_model(
            intent="Test task",
            context={"domain": "testing", "task_type": "unit_test"},
            steps=[{"action": "run", "status": "success"}],
            tools=["pytest"],
            trace={"tests_run": 10, "tests_passed": 10},
            outcome_success=True,
            outcome_metrics={"coverage": 0.85},
            what_worked=["All tests passed"],
            what_failed=[],
            why="Good test coverage",
            confidence_score=0.88,
        )

        assert isinstance(model, Experience)
        assert model.intent == "Test task"
        assert model.confidence_score == 0.88
        assert model.timestamp is not None
        assert model.version == 1
        assert model.evaluation_status == "pending"

    def test_from_trace_with_failure(self) -> None:
        from app.services.experience.factory import ExperienceFactory

        create_schema = ExperienceFactory.from_trace(
            intent="Failed deployment",
            context={"domain": "devops", "task_type": "deployment"},
            steps=[{"action": "build", "status": "success"}, {"action": "deploy", "status": "failed"}],
            tools=["docker"],
            trace={"error": "port already in use"},
            outcome_success=False,
            outcome_metrics={"deploy_time_s": 5, "error_count": 1},
            what_worked=["Build succeeded"],
            what_failed=["Port conflict during deploy"],
            why="Port 8080 was already in use",
            confidence_score=0.3,
        )

        assert create_schema.outcome.success is False
        assert create_schema.reflection.what_failed == ["Port conflict during deploy"]
        assert create_schema.confidence_score == 0.3
