"""Unit tests for SystemMetricsCalculator - 系统指标计算."""

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.evaluation import SystemMetric
from app.services.evaluation.metrics import SystemMetricsCalculator


def _make_scalar_result(value):
    """Create a mock result that returns a scalar value."""
    mock = MagicMock()
    mock.scalar.return_value = value
    return mock


class TestComputeAll:
    """Test compute_all."""

    @pytest.mark.asyncio
    async def test_compute_all(self) -> None:
        session = AsyncMock()
        # compute_all calls 7 individual metrics, each with multiple session.execute calls
        # We need to set up enough return values for all of them

        # _compute_reuse_rate: total=10, reused=3
        # _compute_workflow_success_rate: total=10, success=8
        # _compute_cross_agent_transfer_rate: total=10, transferred=2
        # _compute_external_dependency_ratio: total=10 -> returns 0.0
        # _compute_learning_velocity: count=7 -> 7/7=1.0
        # _compute_convergence_speed: total=10, evaluated=5
        # _compute_human_intervention_rate: total=10 -> returns 0.0

        # Each metric that uses total calls session.execute for total count first
        # Order of metrics in compute_all:
        # 1. reuse_rate: execute(total=10), execute(reused=3)
        # 2. workflow_success_rate: execute(total=10), execute(success=8)
        # 3. cross_agent_transfer_rate: execute(total=10), execute(transferred=2)
        # 4. external_dependency_ratio: execute(total=10)
        # 5. learning_velocity: execute(count=7)
        # 6. convergence_speed: execute(total=10), execute(evaluated=5)
        # 7. human_intervention_rate: execute(total=10)

        session.execute.side_effect = [
            _make_scalar_result(10), _make_scalar_result(3),   # reuse_rate
            _make_scalar_result(10), _make_scalar_result(8),   # workflow_success_rate
            _make_scalar_result(10), _make_scalar_result(2),   # cross_agent_transfer_rate
            _make_scalar_result(10),                           # external_dependency_ratio
            _make_scalar_result(7),                            # learning_velocity
            _make_scalar_result(10), _make_scalar_result(5),   # convergence_speed
            _make_scalar_result(10),                           # human_intervention_rate
        ]

        calc = SystemMetricsCalculator(session)
        metrics = await calc.compute_all()

        assert "experience_reuse_rate" in metrics
        assert "workflow_success_rate" in metrics
        assert "cross_agent_transfer_rate" in metrics
        assert "external_dependency_ratio" in metrics
        assert "learning_velocity" in metrics
        assert "convergence_speed" in metrics
        assert "human_intervention_rate" in metrics

        assert abs(metrics["experience_reuse_rate"] - 0.3) < 0.01
        assert abs(metrics["workflow_success_rate"] - 0.8) < 0.01
        assert abs(metrics["cross_agent_transfer_rate"] - 0.2) < 0.01
        assert metrics["external_dependency_ratio"] == 0.0
        assert abs(metrics["learning_velocity"] - 1.0) < 0.01
        assert abs(metrics["convergence_speed"] - 0.5) < 0.01
        assert metrics["human_intervention_rate"] == 0.0


class TestReuseRate:
    """Test _compute_reuse_rate."""

    @pytest.mark.asyncio
    async def test_reuse_rate(self) -> None:
        session = AsyncMock()
        session.execute.side_effect = [_make_scalar_result(100), _make_scalar_result(30)]

        calc = SystemMetricsCalculator(session)
        rate = await calc._compute_reuse_rate()

        assert abs(rate - 0.3) < 0.01

    @pytest.mark.asyncio
    async def test_reuse_rate_zero_total(self) -> None:
        session = AsyncMock()
        session.execute.side_effect = [_make_scalar_result(0)]

        calc = SystemMetricsCalculator(session)
        rate = await calc._compute_reuse_rate()

        assert rate == 0.0

    @pytest.mark.asyncio
    async def test_reuse_rate_capped_at_1(self) -> None:
        session = AsyncMock()
        session.execute.side_effect = [_make_scalar_result(5), _make_scalar_result(10)]

        calc = SystemMetricsCalculator(session)
        rate = await calc._compute_reuse_rate()

        assert rate == 1.0  # min(1.0, 10/5)

    @pytest.mark.asyncio
    async def test_reuse_rate_none_total(self) -> None:
        session = AsyncMock()
        session.execute.side_effect = [_make_scalar_result(None)]

        calc = SystemMetricsCalculator(session)
        rate = await calc._compute_reuse_rate()

        assert rate == 0.0


class TestWorkflowSuccessRate:
    """Test _compute_workflow_success_rate."""

    @pytest.mark.asyncio
    async def test_success_rate(self) -> None:
        session = AsyncMock()
        session.execute.side_effect = [_make_scalar_result(20), _make_scalar_result(15)]

        calc = SystemMetricsCalculator(session)
        rate = await calc._compute_workflow_success_rate()

        assert abs(rate - 0.75) < 0.01

    @pytest.mark.asyncio
    async def test_success_rate_zero_total(self) -> None:
        session = AsyncMock()
        session.execute.side_effect = [_make_scalar_result(0)]

        calc = SystemMetricsCalculator(session)
        rate = await calc._compute_workflow_success_rate()

        assert rate == 0.0


class TestCrossAgentTransferRate:
    """Test _compute_cross_agent_transfer_rate."""

    @pytest.mark.asyncio
    async def test_transfer_rate(self) -> None:
        session = AsyncMock()
        session.execute.side_effect = [_make_scalar_result(50), _make_scalar_result(10)]

        calc = SystemMetricsCalculator(session)
        rate = await calc._compute_cross_agent_transfer_rate()

        assert abs(rate - 0.2) < 0.01

    @pytest.mark.asyncio
    async def test_transfer_rate_zero_total(self) -> None:
        session = AsyncMock()
        session.execute.side_effect = [_make_scalar_result(0)]

        calc = SystemMetricsCalculator(session)
        rate = await calc._compute_cross_agent_transfer_rate()

        assert rate == 0.0


class TestExternalDependencyRatio:
    """Test _compute_external_dependency_ratio."""

    @pytest.mark.asyncio
    async def test_returns_zero(self) -> None:
        session = AsyncMock()
        session.execute.side_effect = [_make_scalar_result(100)]

        calc = SystemMetricsCalculator(session)
        ratio = await calc._compute_external_dependency_ratio()

        assert ratio == 0.0

    @pytest.mark.asyncio
    async def test_zero_total(self) -> None:
        session = AsyncMock()
        session.execute.side_effect = [_make_scalar_result(0)]

        calc = SystemMetricsCalculator(session)
        ratio = await calc._compute_external_dependency_ratio()

        assert ratio == 0.0


class TestLearningVelocity:
    """Test _compute_learning_velocity."""

    @pytest.mark.asyncio
    async def test_velocity(self) -> None:
        session = AsyncMock()
        session.execute.side_effect = [_make_scalar_result(14)]

        calc = SystemMetricsCalculator(session)
        velocity = await calc._compute_learning_velocity()

        assert abs(velocity - 2.0) < 0.01  # 14 / 7

    @pytest.mark.asyncio
    async def test_velocity_zero(self) -> None:
        session = AsyncMock()
        session.execute.side_effect = [_make_scalar_result(0)]

        calc = SystemMetricsCalculator(session)
        velocity = await calc._compute_learning_velocity()

        assert velocity == 0.0

    @pytest.mark.asyncio
    async def test_velocity_none(self) -> None:
        session = AsyncMock()
        session.execute.side_effect = [_make_scalar_result(None)]

        calc = SystemMetricsCalculator(session)
        velocity = await calc._compute_learning_velocity()

        assert velocity == 0.0


class TestConvergenceSpeed:
    """Test _compute_convergence_speed."""

    @pytest.mark.asyncio
    async def test_convergence(self) -> None:
        session = AsyncMock()
        session.execute.side_effect = [_make_scalar_result(10), _make_scalar_result(7)]

        calc = SystemMetricsCalculator(session)
        speed = await calc._compute_convergence_speed()

        assert abs(speed - 0.7) < 0.01

    @pytest.mark.asyncio
    async def test_convergence_zero_total(self) -> None:
        session = AsyncMock()
        session.execute.side_effect = [_make_scalar_result(0)]

        calc = SystemMetricsCalculator(session)
        speed = await calc._compute_convergence_speed()

        assert speed == 0.0


class TestHumanInterventionRate:
    """Test _compute_human_intervention_rate."""

    @pytest.mark.asyncio
    async def test_returns_zero(self) -> None:
        session = AsyncMock()
        session.execute.side_effect = [_make_scalar_result(100)]

        calc = SystemMetricsCalculator(session)
        rate = await calc._compute_human_intervention_rate()

        assert rate == 0.0

    @pytest.mark.asyncio
    async def test_zero_total(self) -> None:
        session = AsyncMock()
        session.execute.side_effect = [_make_scalar_result(0)]

        calc = SystemMetricsCalculator(session)
        rate = await calc._compute_human_intervention_rate()

        assert rate == 0.0


class TestSaveMetrics:
    """Test save_metrics."""

    @pytest.mark.asyncio
    async def test_save_metrics(self) -> None:
        session = AsyncMock()
        calc = SystemMetricsCalculator(session)

        metrics = {
            "experience_reuse_rate": 0.3,
            "workflow_success_rate": 0.8,
        }

        await calc.save_metrics(metrics)

        assert session.add.call_count == 2
        session.flush.assert_awaited_once()

        # Verify the metrics added are SystemMetric objects
        added = [call.args[0] for call in session.add.call_args_list]
        assert all(isinstance(m, SystemMetric) for m in added)
        assert added[0].metric_name == "experience_reuse_rate"
        assert added[0].value == 0.3
        assert added[1].metric_name == "workflow_success_rate"
        assert added[1].value == 0.8


class TestGetHistory:
    """Test get_history."""

    @pytest.mark.asyncio
    async def test_get_history(self) -> None:
        session = AsyncMock()
        m1 = SystemMetric(metric_name="reuse_rate", value=0.3, timestamp=datetime.now(timezone.utc))
        m2 = SystemMetric(metric_name="reuse_rate", value=0.5, timestamp=datetime.now(timezone.utc) - timedelta(hours=1))

        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [m1, m2]
        result_mock.scalars.return_value = scalars_mock
        session.execute.return_value = result_mock

        calc = SystemMetricsCalculator(session)
        history = await calc.get_history("reuse_rate", hours=24)

        assert len(history) == 2
        assert history[0]["value"] == 0.3
        assert history[1]["value"] == 0.5
        assert "timestamp" in history[0]

    @pytest.mark.asyncio
    async def test_get_history_empty(self) -> None:
        session = AsyncMock()
        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock.scalars.return_value = scalars_mock
        session.execute.return_value = result_mock

        calc = SystemMetricsCalculator(session)
        history = await calc.get_history("nonexistent", hours=12)

        assert history == []

    @pytest.mark.asyncio
    async def test_get_history_null_timestamp(self) -> None:
        session = AsyncMock()
        m = SystemMetric(metric_name="test", value=0.1, timestamp=None)

        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [m]
        result_mock.scalars.return_value = scalars_mock
        session.execute.return_value = result_mock

        calc = SystemMetricsCalculator(session)
        history = await calc.get_history("test")

        assert len(history) == 1
        assert history[0]["timestamp"] is None


class TestMetricNames:
    """Test METRIC_NAMES constant."""

    def test_metric_names(self) -> None:
        assert len(SystemMetricsCalculator.METRIC_NAMES) == 7
        assert "experience_reuse_rate" in SystemMetricsCalculator.METRIC_NAMES
        assert "workflow_success_rate" in SystemMetricsCalculator.METRIC_NAMES
        assert "cross_agent_transfer_rate" in SystemMetricsCalculator.METRIC_NAMES
        assert "external_dependency_ratio" in SystemMetricsCalculator.METRIC_NAMES
        assert "learning_velocity" in SystemMetricsCalculator.METRIC_NAMES
        assert "convergence_speed" in SystemMetricsCalculator.METRIC_NAMES
        assert "human_intervention_rate" in SystemMetricsCalculator.METRIC_NAMES
