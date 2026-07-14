"""Experience evaluator - 经验对象价值评估.

评估经验对象本身的价值，维度包括：
- 可复用性 (reusability): 经验是否可以被其他任务复用
- 可靠性 (reliability): 经验的可靠性（基于历史使用记录）
- 覆盖度 (coverage): 经验覆盖的场景范围
- 时效性 (timeliness): 经验是否仍然适用

核心原则：无评估 = 无效输出
未评估的经验被标记为 'pending'，不进入检索池。
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from app.models.evaluation import Evaluation
from app.models.experience import Experience


@dataclass
class ExperienceEvaluationResult:
    """经验评估结果."""

    target_id: str
    scores: dict = field(default_factory=dict)
    overall_score: float = 0.0
    confidence_score: float = 0.0  # 更新后的置信度
    summary: str = ""
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "target_id": self.target_id,
            "scores": self.scores,
            "overall_score": round(self.overall_score, 4),
            "confidence_score": round(self.confidence_score, 4),
            "summary": self.summary,
            "details": self.details,
        }


class ExperienceEvaluator:
    """经验评估器 - 评估经验对象本身的价值."""

    # 评估维度权重
    WEIGHTS = {
        "reusability": 0.35,   # 可复用性
        "reliability": 0.25,   # 可靠性
        "coverage": 0.20,      # 覆盖度
        "timeliness": 0.20,    # 时效性
    }

    def evaluate(
        self,
        experience: Experience,
        reuse_count: int = 0,
        citation_count: int = 0,
        avg_task_score: float = 0.5,
    ) -> ExperienceEvaluationResult:
        """评估经验对象.

        Args:
            experience: Experience 对象
            reuse_count: 被复用次数
            citation_count: 被引用次数
            avg_task_score: 基于此经验执行的任务的平均得分

        Returns:
            ExperienceEvaluationResult: 评估结果
        """
        # ── 可复用性评估 ──
        # 基于可复用模式数量和引用次数
        patterns = experience.reusable_patterns or []
        reusability = min(1.0, len(patterns) * 0.2 + min(reuse_count * 0.1, 0.5))

        # ── 可靠性评估 ──
        # 基于历史成功率和引用次数
        outcome = experience.outcome or {}
        success = outcome.get("success", False)
        reliability = 0.4 if success else 0.1
        reliability += min(citation_count * 0.1, 0.4)
        reliability += avg_task_score * 0.2
        reliability = min(1.0, reliability)

        # ── 覆盖度评估 ──
        # 基于执行步骤数量和工具多样性
        execution = experience.execution or {}
        steps = execution.get("steps", [])
        tools = execution.get("tools", [])
        coverage = min(1.0, len(steps) * 0.1 + len(tools) * 0.15)

        # ── 时效性评估 ──
        # 基于创建时间（30天半衰期）
        if experience.created_at:
            age_days = (datetime.now(timezone.utc) - experience.created_at).days
            timeliness = 0.5 ** (age_days / 30) if age_days > 0 else 1.0
        else:
            timeliness = 0.5

        # ── 计算总分 ──
        scores = {
            "reusability": round(reusability, 4),
            "reliability": round(reliability, 4),
            "coverage": round(coverage, 4),
            "timeliness": round(timeliness, 4),
        }

        overall_score = sum(
            self.WEIGHTS[dim] * scores[dim] for dim in self.WEIGHTS
        )

        # ── 更新置信度 ──
        # 置信度 = 原始置信度 * 0.3 + 评估得分 * 0.7
        original_confidence = experience.confidence_score or 0.5
        confidence_score = original_confidence * 0.3 + overall_score * 0.7

        # ── 生成摘要 ──
        reflection = experience.reflection or {}
        what_worked = reflection.get("what_worked", [])
        what_failed = reflection.get("what_failed", [])

        summary_parts = [
            f"Reusability: {reusability:.0%}",
            f"Reliability: {reliability:.0%}",
        ]
        if what_worked:
            summary_parts.append(f"Strengths: {len(what_worked)}")
        if what_failed:
            summary_parts.append(f"Risks: {len(what_failed)}")

        return ExperienceEvaluationResult(
            target_id=str(experience.id) if experience.id else "",
            scores=scores,
            overall_score=overall_score,
            confidence_score=confidence_score,
            summary=" | ".join(summary_parts),
            details={
                "reuse_count": reuse_count,
                "citation_count": citation_count,
                "patterns_count": len(patterns),
                "steps_count": len(steps),
                "tools_count": len(tools),
                "evaluated_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    def to_evaluation_model(self, result: ExperienceEvaluationResult) -> Evaluation:
        """将评估结果转为 ORM 模型."""
        return Evaluation(
            target_type="experience",
            target_id=result.target_id,
            evaluator="rule_based",
            scores=result.scores,
            overall_score=result.overall_score,
            summary=result.summary,
            details={
                **result.details,
                "confidence_score": result.confidence_score,
            },
        )
