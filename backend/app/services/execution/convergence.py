"""Convergence controller - 收敛控制系统.

防止无限循环和资源浪费。系统内置严格的收敛控制：

| 控制规则 | 内容 |
|----------|------|
| 最大迭代限制 | Experience: 3次 / Workflow: 2次 / Evaluation: 2次 / Retrieval: 2次 |
| 改进阈值 | 每次迭代必须满足 Δ performance ≥ ε |
| 停滞检测 | 连续2次迭代无改进 -> 冻结模块 -> 回滚到最佳版本 |
| 终止保证 | 所有循环均可终止 |
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ModuleType(str, Enum):
    """模块类型 - 每种模块有不同的最大迭代限制."""

    EXPERIENCE = "experience"
    WORKFLOW = "workflow"
    EVALUATION = "evaluation"
    RETRIEVAL = "retrieval"


class ConvergenceStatus(str, Enum):
    """收敛状态."""

    CONTINUE = "continue"       # 继续迭代
    CONVERGED = "converged"     # 已收敛（改进低于阈值）
    STAGNATED = "stagnated"     # 停滞（连续无改进）
    MAX_ITERATIONS = "max_iterations"  # 达到最大迭代次数


# ── 默认配置 ──

DEFAULT_MAX_ITERATIONS: dict[ModuleType, int] = {
    ModuleType.EXPERIENCE: 3,
    ModuleType.WORKFLOW: 2,
    ModuleType.EVALUATION: 2,
    ModuleType.RETRIEVAL: 2,
}

DEFAULT_IMPROVEMENT_THRESHOLD = 0.01  # ε = 1%
DEFAULT_STAGNATION_LIMIT = 2  # 连续2次无改进 -> 冻结


@dataclass
class IterationRecord:
    """单次迭代记录."""

    iteration: int
    performance: float
    improvement: float = 0.0  # Δ performance
    timestamp: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class ConvergenceState:
    """收敛控制状态."""

    module_type: ModuleType
    max_iterations: int = 0
    improvement_threshold: float = DEFAULT_IMPROVEMENT_THRESHOLD
    stagnation_limit: int = DEFAULT_STAGNATION_LIMIT

    iterations: list[IterationRecord] = field(default_factory=list)
    best_performance: float = 0.0
    best_iteration: int = 0
    stagnation_count: int = 0
    is_frozen: bool = False
    frozen_reason: str | None = None

    def __post_init__(self) -> None:
        if self.max_iterations == 0:
            self.max_iterations = DEFAULT_MAX_ITERATIONS.get(self.module_type, 2)


class ConvergenceController:
    """收敛控制器 - 确保系统优化过程不会失控.

    使用方式:
        controller = ConvergenceController(ModuleType.EXPERIENCE)
        for i in range(10):
            performance = run_iteration()
            status = controller.check(performance)
            if status != ConvergenceStatus.CONTINUE:
                break
    """

    def __init__(
        self,
        module_type: ModuleType,
        improvement_threshold: float = DEFAULT_IMPROVEMENT_THRESHOLD,
        stagnation_limit: int = DEFAULT_STAGNATION_LIMIT,
        max_iterations: int | None = None,
    ) -> None:
        self.state = ConvergenceState(
            module_type=module_type,
            max_iterations=max_iterations or DEFAULT_MAX_ITERATIONS.get(module_type, 2),
            improvement_threshold=improvement_threshold,
            stagnation_limit=stagnation_limit,
        )

    def check(self, performance: float, metadata: dict | None = None) -> ConvergenceStatus:
        """检查是否应该继续迭代.

        Args:
            performance: 当前迭代的性能值
            metadata: 可选的元数据

        Returns:
            ConvergenceStatus: 收敛状态
        """
        if self.state.is_frozen:
            return ConvergenceStatus.STAGNATED

        iteration = len(self.state.iterations)
        improvement = 0.0

        if self.state.iterations:
            prev_performance = self.state.iterations[-1].performance
            improvement = performance - prev_performance

        # ── 记录迭代 ──
        from datetime import datetime, timezone

        record = IterationRecord(
            iteration=iteration,
            performance=performance,
            improvement=improvement,
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata=metadata or {},
        )
        self.state.iterations.append(record)

        # ── 更新最佳记录 ──
        if performance > self.state.best_performance:
            self.state.best_performance = performance
            self.state.best_iteration = iteration

        # ── 检查最大迭代限制 ──
        if iteration + 1 >= self.state.max_iterations:
            self._freeze("max_iterations_reached")
            return ConvergenceStatus.MAX_ITERATIONS

        # ── 检查改进阈值 ──
        if iteration > 0 and improvement < self.state.improvement_threshold:
            self.state.stagnation_count += 1
            if self.state.stagnation_count >= self.state.stagnation_limit:
                self._freeze("stagnation_detected")
                return ConvergenceStatus.STAGNATED
        else:
            self.state.stagnation_count = 0

        # ── 检查收敛（改进非常小）──
        if iteration > 0 and improvement < self.state.improvement_threshold * 0.1:
            return ConvergenceStatus.CONVERGED

        return ConvergenceStatus.CONTINUE

    def _freeze(self, reason: str) -> None:
        """冻结模块."""
        self.state.is_frozen = True
        self.state.frozen_reason = reason

    def rollback_to_best(self) -> int:
        """回滚到最佳版本.

        Returns:
            最佳迭代的索引
        """
        return self.state.best_iteration

    def get_summary(self) -> dict:
        """获取收敛控制摘要."""
        return {
            "module_type": self.state.module_type.value,
            "total_iterations": len(self.state.iterations),
            "max_iterations": self.state.max_iterations,
            "best_performance": self.state.best_performance,
            "best_iteration": self.state.best_iteration,
            "is_frozen": self.state.is_frozen,
            "frozen_reason": self.state.frozen_reason,
            "stagnation_count": self.state.stagnation_count,
            "iterations": [
                {
                    "iteration": r.iteration,
                    "performance": r.performance,
                    "improvement": r.improvement,
                }
                for r in self.state.iterations
            ],
        }
