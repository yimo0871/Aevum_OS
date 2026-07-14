"""Unit tests for convergence controller."""

import pytest


class TestConvergenceController:
    """Test ConvergenceController - 收敛控制系统."""

    def test_max_iterations_experience(self) -> None:
        from app.services.execution.convergence import (
            ConvergenceController,
            ConvergenceStatus,
            ModuleType,
        )

        controller = ConvergenceController(ModuleType.EXPERIENCE)
        # Experience: max 3 iterations
        statuses = []
        for i in range(5):
            status = controller.check(performance=0.5 + i * 0.1)
            statuses.append(status)
            if status != ConvergenceStatus.CONTINUE:
                break

        # Should stop after 3 iterations
        assert ConvergenceStatus.MAX_ITERATIONS in statuses
        assert len(controller.state.iterations) == 3

    def test_max_iterations_workflow(self) -> None:
        from app.services.execution.convergence import (
            ConvergenceController,
            ConvergenceStatus,
            ModuleType,
        )

        controller = ConvergenceController(ModuleType.WORKFLOW)
        # Workflow: max 2 iterations
        for i in range(2):
            status = controller.check(performance=0.5 + i * 0.1)

        assert controller.state.is_frozen
        assert controller.state.frozen_reason == "max_iterations_reached"

    def test_stagnation_detection(self) -> None:
        from app.services.execution.convergence import (
            ConvergenceController,
            ConvergenceStatus,
            ModuleType,
        )

        controller = ConvergenceController(
            ModuleType.EXPERIENCE,
            improvement_threshold=0.05,
            stagnation_limit=2,
        )

        # Iteration 0: initial
        status0 = controller.check(performance=0.5)
        assert status0 == ConvergenceStatus.CONTINUE

        # Iteration 1: no improvement (stagnation count = 1)
        status1 = controller.check(performance=0.5)
        assert status1 == ConvergenceStatus.CONTINUE
        assert controller.state.stagnation_count == 1

        # Iteration 2: still no improvement (stagnation count = 2 -> freeze)
        status2 = controller.check(performance=0.5)
        assert status2 == ConvergenceStatus.STAGNATED
        assert controller.state.is_frozen

    def test_improvement_resets_stagnation(self) -> None:
        from app.services.execution.convergence import (
            ConvergenceController,
            ConvergenceStatus,
            ModuleType,
        )

        controller = ConvergenceController(
            ModuleType.EXPERIENCE,
            improvement_threshold=0.05,
            stagnation_limit=2,
        )

        # Iteration 0
        controller.check(performance=0.5)
        # Iteration 1: no improvement
        controller.check(performance=0.5)
        assert controller.state.stagnation_count == 1
        # Iteration 2: improvement -> reset stagnation
        status = controller.check(performance=0.7)
        assert controller.state.stagnation_count == 0

    def test_rollback_to_best(self) -> None:
        from app.services.execution.convergence import ConvergenceController, ModuleType

        controller = ConvergenceController(ModuleType.EXPERIENCE)

        controller.check(performance=0.5)  # iter 0
        controller.check(performance=0.8)  # iter 1 - best
        controller.check(performance=0.6)  # iter 2

        assert controller.state.best_performance == 0.8
        assert controller.state.best_iteration == 1
        assert controller.rollback_to_best() == 1

    def test_frozen_controller_returns_stagnated(self) -> None:
        from app.services.execution.convergence import (
            ConvergenceController,
            ConvergenceStatus,
            ModuleType,
        )

        controller = ConvergenceController(ModuleType.WORKFLOW)
        controller.check(performance=0.5)
        controller.check(performance=0.6)
        assert controller.state.is_frozen

        # Further checks return STAGNATED
        status = controller.check(performance=0.9)
        assert status == ConvergenceStatus.STAGNATED

    def test_get_summary(self) -> None:
        from app.services.execution.convergence import ConvergenceController, ModuleType

        controller = ConvergenceController(ModuleType.EXPERIENCE)
        controller.check(performance=0.5)
        controller.check(performance=0.7)

        summary = controller.get_summary()
        assert summary["module_type"] == "experience"
        assert summary["total_iterations"] == 2
        assert summary["best_performance"] == 0.7
        assert summary["is_frozen"] is False
