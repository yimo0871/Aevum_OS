"""Experience factory - 从执行记录生成 Experience 对象."""

from datetime import datetime, timezone

from app.models.experience import Experience
from app.schemas.experience import (
    ExperienceContext,
    ExperienceCreate,
    ExperienceExecution,
    ExperienceOutcome,
    ExperienceProvenance,
    ExperienceReflection,
)


class ExperienceFactory:
    """经验工厂 - 从执行追踪记录生成结构化 Experience 对象.

    对应 8 步流水线中的 Step 5: generate_experience_object
    """

    @staticmethod
    def from_trace(
        intent: str,
        context: dict,
        steps: list[dict],
        tools: list[str],
        trace: dict,
        outcome_success: bool,
        outcome_metrics: dict,
        what_worked: list[str] | None = None,
        what_failed: list[str] | None = None,
        why: str = "",
        reusable_patterns: list[dict] | None = None,
        confidence_score: float = 0.5,
        agent_signals: list[dict] | None = None,
    ) -> ExperienceCreate:
        """从执行追踪生成 Experience 创建请求.

        这是 8 步流水线 Step 5 的核心实现：
        将非结构化的执行过程转化为结构化的 Experience 对象。
        """
        # ── 构建上下文 ──
        exp_context = ExperienceContext(
            domain=context.get("domain", "general"),
            task_type=context.get("task_type", "unknown"),
            constraints=context.get("constraints", {}),
        )

        # ── 构建执行过程 ──
        exp_execution = ExperienceExecution(
            steps=steps,
            tools=tools,
            trace=trace,
        )

        # ── 构建结果 ──
        exp_outcome = ExperienceOutcome(
            success=outcome_success,
            metrics=outcome_metrics,
        )

        # ── 构建反思 ──
        exp_reflection = ExperienceReflection(
            what_worked=what_worked or [],
            what_failed=what_failed or [],
            why=why,
        )

        # ── 构建来源 ──
        exp_provenance = ExperienceProvenance(
            agent_signals=agent_signals or [{"contribution": "execution"}],
        )

        return ExperienceCreate(
            context=exp_context,
            intent=intent,
            execution=exp_execution,
            outcome=exp_outcome,
            reflection=exp_reflection,
            reusable_patterns=reusable_patterns or [],
            confidence_score=confidence_score,
            provenance=exp_provenance,
            version=1,
        )

    @staticmethod
    def from_trace_to_model(
        intent: str,
        context: dict,
        steps: list[dict],
        tools: list[str],
        trace: dict,
        outcome_success: bool,
        outcome_metrics: dict,
        what_worked: list[str] | None = None,
        what_failed: list[str] | None = None,
        why: str = "",
        reusable_patterns: list[dict] | None = None,
        confidence_score: float = 0.5,
        agent_signals: list[dict] | None = None,
    ) -> Experience:
        """从执行追踪直接生成 Experience ORM 模型."""
        create_schema = ExperienceFactory.from_trace(
            intent=intent,
            context=context,
            steps=steps,
            tools=tools,
            trace=trace,
            outcome_success=outcome_success,
            outcome_metrics=outcome_metrics,
            what_worked=what_worked,
            what_failed=what_failed,
            why=why,
            reusable_patterns=reusable_patterns,
            confidence_score=confidence_score,
            agent_signals=agent_signals,
        )

        return Experience(
            timestamp=datetime.now(timezone.utc),
            context=create_schema.context.model_dump(),
            intent=create_schema.intent,
            execution=create_schema.execution.model_dump(),
            outcome=create_schema.outcome.model_dump(),
            reflection=create_schema.reflection.model_dump(),
            reusable_patterns=create_schema.reusable_patterns,
            confidence_score=create_schema.confidence_score,
            provenance=create_schema.provenance.model_dump(),
            version=create_schema.version,
        )
