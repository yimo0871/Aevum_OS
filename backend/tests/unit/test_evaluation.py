"""Unit tests for evaluation layer."""

import pytest
from datetime import datetime, timezone, timedelta


class TestTaskEvaluator:
    """Test TaskEvaluator - 任务评估器."""

    def test_successful_task(self) -> None:
        from app.services.evaluation.task_evaluator import TaskEvaluator

        evaluator = TaskEvaluator()
        result = evaluator.evaluate(
            task_id="task-001",
            success=True,
            steps=[
                {"step_name": "build", "status": "completed"},
                {"step_name": "test", "status": "completed"},
                {"step_name": "deploy", "status": "completed"},
            ],
            duration=45.0,
            tools_used=["docker", "kubectl"],
        )

        assert result.overall_score > 0.5
        assert result.scores["completeness"] == 1.0
        assert result.scores["correctness"] == 1.0
        assert "completed successfully" in result.summary

    def test_failed_task(self) -> None:
        from app.services.evaluation.task_evaluator import TaskEvaluator

        evaluator = TaskEvaluator()
        result = evaluator.evaluate(
            task_id="task-002",
            success=False,
            steps=[
                {"step_name": "build", "status": "completed"},
                {"step_name": "test", "status": "failed"},
            ],
            duration=30.0,
            error="Test failure",
        )

        assert result.scores["completeness"] < 1.0
        assert result.scores["correctness"] == 0.0
        assert "failed" in result.summary

    def test_efficiency_short_duration(self) -> None:
        from app.services.evaluation.task_evaluator import TaskEvaluator

        evaluator = TaskEvaluator()
        result = evaluator.evaluate(
            task_id="task-003",
            success=True,
            steps=[{"status": "completed"}],
            duration=10.0,  # 短时长 -> 高效率
        )

        assert result.scores["efficiency"] > 0.8

    def test_efficiency_long_duration(self) -> None:
        from app.services.evaluation.task_evaluator import TaskEvaluator

        evaluator = TaskEvaluator()
        result = evaluator.evaluate(
            task_id="task-004",
            success=True,
            steps=[{"status": "completed"}],
            duration=300.0,  # 长时长 -> 低效率
        )

        assert result.scores["efficiency"] < 0.3

    def test_no_steps_no_duration(self) -> None:
        from app.services.evaluation.task_evaluator import TaskEvaluator

        evaluator = TaskEvaluator()
        result = evaluator.evaluate(
            task_id="task-005",
            success=True,
        )

        assert result.overall_score > 0
        assert result.details["total_steps"] == 0

    def test_to_evaluation_model(self) -> None:
        from app.models.evaluation import Evaluation
        from app.services.evaluation.task_evaluator import TaskEvaluator

        evaluator = TaskEvaluator()
        result = evaluator.evaluate(task_id="task-006", success=True)
        model = evaluator.to_evaluation_model(result)

        assert isinstance(model, Evaluation)
        assert model.target_type == "task"
        assert model.evaluator == "rule_based"


class TestExperienceEvaluator:
    """Test ExperienceEvaluator - 经验评估器."""

    def _make_experience(self, **kwargs) -> "Experience":
        from app.models.experience import Experience

        defaults = {
            "context": {"domain": "devops", "task_type": "deployment"},
            "intent": "Deploy application",
            "execution": {
                "steps": [{"action": "build"}, {"action": "deploy"}],
                "tools": ["docker", "kubectl"],
                "trace": {},
            },
            "outcome": {"success": True, "metrics": {}},
            "reflection": {
                "what_worked": ["Docker build"],
                "what_failed": [],
                "why": "Standard pattern",
            },
            "reusable_patterns": [{"pattern": "docker-build"}],
            "confidence_score": 0.5,
            "provenance": {"agent_signals": [{"contribution": "execution"}]},
            "created_at": datetime.now(timezone.utc) - timedelta(days=5),
        }
        defaults.update(kwargs)
        return Experience(**defaults)

    def test_successful_experience(self) -> None:
        from app.services.evaluation.experience_evaluator import ExperienceEvaluator

        exp = self._make_experience()
        evaluator = ExperienceEvaluator()
        result = evaluator.evaluate(exp, reuse_count=3, citation_count=2)

        assert result.scores["reusability"] > 0
        assert result.scores["reliability"] > 0.5  # success + citations
        assert result.confidence_score > 0.5  # should be updated

    def test_failed_experience(self) -> None:
        from app.services.evaluation.experience_evaluator import ExperienceEvaluator

        exp = self._make_experience(
            outcome={"success": False, "metrics": {}},
            reflection={"what_worked": [], "what_failed": ["Build error"], "why": "Missing dependency"},
        )
        evaluator = ExperienceEvaluator()
        result = evaluator.evaluate(exp)

        assert result.scores["reliability"] < 0.5

    def test_old_experience_low_timeliness(self) -> None:
        from app.services.evaluation.experience_evaluator import ExperienceEvaluator

        exp = self._make_experience(
            created_at=datetime.now(timezone.utc) - timedelta(days=120)
        )
        evaluator = ExperienceEvaluator()
        result = evaluator.evaluate(exp)

        assert result.scores["timeliness"] < 0.2

    def test_recent_experience_high_timeliness(self) -> None:
        from app.services.evaluation.experience_evaluator import ExperienceEvaluator

        exp = self._make_experience(
            created_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        evaluator = ExperienceEvaluator()
        result = evaluator.evaluate(exp)

        assert result.scores["timeliness"] > 0.9

    def test_confidence_update(self) -> None:
        from app.services.evaluation.experience_evaluator import ExperienceEvaluator

        exp = self._make_experience(confidence_score=0.3)
        evaluator = ExperienceEvaluator()
        result = evaluator.evaluate(exp, reuse_count=5, citation_count=3)

        # confidence = original * 0.3 + overall * 0.7
        # Should be higher than original if overall is good
        assert result.confidence_score > 0.3

    def test_to_evaluation_model(self) -> None:
        from app.models.evaluation import Evaluation
        from app.services.evaluation.experience_evaluator import ExperienceEvaluator

        exp = self._make_experience()
        evaluator = ExperienceEvaluator()
        result = evaluator.evaluate(exp)
        model = evaluator.to_evaluation_model(result)

        assert isinstance(model, Evaluation)
        assert model.target_type == "experience"
