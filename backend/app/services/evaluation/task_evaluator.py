"""Task evaluator - 任务执行质量评估.

评估单次任务执行的质量，维度包括：
- 完成度 (completeness): 任务是否完整执行
- 正确性 (correctness): 执行结果是否正确
- 效率 (efficiency): 执行效率（时间、资源）
- 资源消耗 (resource_usage): 资源使用情况
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.models.evaluation import Evaluation


@dataclass
class TaskEvaluationResult:
    """任务评估结果."""

    target_id: str
    scores: dict = field(default_factory=dict)
    overall_score: float = 0.0
    summary: str = ""
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "target_id": self.target_id,
            "scores": self.scores,
            "overall_score": round(self.overall_score, 4),
            "summary": self.summary,
            "details": self.details,
        }


class TaskEvaluator:
    """任务评估器 - 评估单次任务执行质量.

    核心原则：无评估 = 无效输出
    """

    # 评估维度权重
    WEIGHTS = {
        "completeness": 0.35,  # 完成度
        "correctness": 0.30,   # 正确性
        "efficiency": 0.20,    # 效率
        "resource_usage": 0.15,  # 资源消耗
    }

    def evaluate(
        self,
        task_id: str,
        success: bool,
        steps: list[dict] | None = None,
        duration: float = 0.0,
        error: str | None = None,
        tools_used: list[str] | None = None,
    ) -> TaskEvaluationResult:
        """评估任务执行质量.

        Args:
            task_id: 任务 ID
            success: 是否成功
            steps: 执行步骤列表
            duration: 执行时长（秒）
            error: 错误信息
            tools_used: 使用的工具列表

        Returns:
            TaskEvaluationResult: 评估结果
        """
        steps = steps or []
        tools_used = tools_used or []

        # ── 完成度评估 ──
        completed_steps = sum(1 for s in steps if s.get("status") == "completed")
        total_steps = len(steps)
        completeness = completed_steps / total_steps if total_steps > 0 else (1.0 if success else 0.0)

        # ── 正确性评估 ──
        correctness = 1.0 if success and not error else 0.0

        # ── 效率评估 ──
        # 基于执行时长：越短越好（参考基线 60s）
        baseline_duration = 60.0
        if duration > 0:
            efficiency = max(0.0, min(1.0, baseline_duration / duration))
        else:
            efficiency = 0.5  # 未知时长

        # ── 资源消耗评估 ──
        # 基于工具调用次数：越少越好（参考基线 10 次）
        tool_count = len(tools_used)
        baseline_tools = 10
        resource_usage = max(0.0, min(1.0, 1.0 - (tool_count / baseline_tools))) if tool_count > 0 else 0.8

        # ── 计算总分 ──
        scores = {
            "completeness": round(completeness, 4),
            "correctness": round(correctness, 4),
            "efficiency": round(efficiency, 4),
            "resource_usage": round(resource_usage, 4),
        }

        overall_score = sum(
            self.WEIGHTS[dim] * scores[dim] for dim in self.WEIGHTS
        )

        # ── 生成摘要 ──
        if success:
            summary = f"Task completed successfully. Completeness: {completeness:.0%}, Duration: {duration:.1f}s"
        else:
            summary = f"Task failed. Error: {error or 'Unknown'}. Completed {completed_steps}/{total_steps} steps."

        return TaskEvaluationResult(
            target_id=task_id,
            scores=scores,
            overall_score=overall_score,
            summary=summary,
            details={
                "total_steps": total_steps,
                "completed_steps": completed_steps,
                "duration_s": duration,
                "tools_count": tool_count,
                "error": error,
                "evaluated_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    def to_evaluation_model(self, result: TaskEvaluationResult) -> Evaluation:
        """将评估结果转为 ORM 模型."""
        return Evaluation(
            target_type="task",
            target_id=result.target_id,
            evaluator="rule_based",
            scores=result.scores,
            overall_score=result.overall_score,
            summary=result.summary,
            details=result.details,
        )
