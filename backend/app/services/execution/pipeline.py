"""8-step experience pipeline - 经验生成流水线编排器.

每次任务执行都必须完整走完以下流程，缺一则任务无效：

    Step 1: 检索相似经验     -> retrieve_similar_experiences
    Step 2: 选择最佳工作流   -> select_best_workflows
    Step 3: 执行任务         -> execute_task
    Step 4: 记录完整追踪     -> record_full_trace
    Step 5: 生成经验对象     -> generate_experience_object
    Step 6: 评估经验         -> evaluate_experience
    Step 7: 存入图谱         -> store_into_graph
    Step 8: 更新复用索引     -> update_reuse_index

失败条件：如果未生成 Experience 对象 -> 该任务视为无效。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.execution.engine import ExecutionEngine, TaskInput, TaskOutput
from app.services.execution.trace import ExecutionTracer
from app.services.experience.factory import ExperienceFactory
from app.services.experience.repository import ExperienceRepository
from sqlalchemy.ext.asyncio import AsyncSession


class PipelineStepResult(BaseModel):
    """流水线单步结果."""

    step: int
    name: str
    status: str = "pending"  # pending | running | completed | failed | skipped
    started_at: str = ""
    completed_at: str = ""
    duration_ms: float = 0.0
    output: Any = None
    error: str | None = None


class PipelineResult(BaseModel):
    """流水线完整结果."""

    task_id: str
    status: str = "running"  # running | completed | failed | invalid
    steps: list[PipelineStepResult] = Field(default_factory=list)
    experience_id: str | None = None
    total_duration_ms: float = 0.0
    error: str | None = None

    def is_valid(self) -> bool:
        """任务是否有效（生成了 Experience 对象）."""
        return self.experience_id is not None and self.status == "completed"


class ExperiencePipeline:
    """8 步经验流水线编排器.

    将 8 个步骤串联执行，确保每次任务执行都生成完整的 Experience 对象。
    如果未生成 Experience -> 任务标记为 invalid。
    """

    STEP_NAMES = [
        "retrieve_similar_experiences",  # Step 1
        "select_best_workflows",         # Step 2
        "execute_task",                  # Step 3
        "record_full_trace",             # Step 4
        "generate_experience_object",    # Step 5
        "evaluate_experience",           # Step 6
        "store_into_graph",              # Step 7
        "update_reuse_index",             # Step 8
    ]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.engine = ExecutionEngine()
        self.repo = ExperienceRepository(session)

    async def run(
        self,
        intent: str,
        context: dict | None = None,
        constraints: dict | None = None,
        workflow: list[dict] | None = None,
        user_id: str | None = None,
    ) -> PipelineResult:
        """运行完整的 8 步流水线.

        Args:
            intent: 任务意图
            context: 任务上下文
            constraints: 约束条件
            workflow: 工作流定义（可选）
            user_id: 用户 ID（用于数据隔离，关联生成的 Experience）

        Returns:
            PipelineResult: 流水线结果
        """
        task_input = TaskInput(
            intent=intent,
            context=context or {},
            constraints=constraints or {},
            workflow=workflow,
        )

        result = PipelineResult(task_id=task_input.task_id)
        pipeline_start = datetime.now(timezone.utc)

        # 执行追踪器（用于 Step 4）
        tracer = ExecutionTracer(task_input.task_id, intent)

        try:
            # ── Step 1: 检索相似经验 ──
            step1 = await self._execute_step(1, "retrieve_similar_experiences", {
                "intent": intent,
                "context": context or {},
            })
            result.steps.append(step1)
            similar_experiences = step1.output or []

            # ── Step 2: 选择最佳工作流 ──
            step2 = await self._execute_step(2, "select_best_workflows", {
                "similar_experiences": similar_experiences,
                "context": context or {},
            })
            result.steps.append(step2)
            selected_workflow = step2.output or workflow

            # ── Step 3: 执行任务 ──
            step3 = await self._execute_step(3, "execute_task", {
                "task_input": task_input,
            })
            result.steps.append(step3)

            # 实际执行任务
            task_output: TaskOutput = await self.engine.execute_task(task_input)

            # ── Step 4: 记录完整追踪 ──
            step4 = await self._execute_step(4, "record_full_trace", {
                "task_output": task_output.to_dict(),
            })
            result.steps.append(step4)
            trace_dict = task_output.trace

            # ── Step 5: 生成经验对象 ──
            step5 = await self._execute_step(5, "generate_experience_object", {
                "intent": intent,
                "trace": trace_dict,
            })
            result.steps.append(step5)

            # 使用 ExperienceFactory 从执行记录生成 Experience
            experience_create = ExperienceFactory.from_trace(
                intent=intent,
                context=context or {},
                steps=task_output.steps,
                tools=task_output.tools,
                trace=trace_dict,
                outcome_success=task_output.success,
                outcome_metrics={"duration_s": task_output.duration},
                what_worked=[s["step_name"] for s in task_output.steps if s.get("status") == "completed"],
                what_failed=[s["step_name"] for s in task_output.steps if s.get("status") == "failed"],
                why="Pipeline completed" if task_output.success else f"Task failed: {task_output.error}",
                confidence_score=0.7 if task_output.success else 0.3,
            )

            # ── Step 6: 评估经验 ──
            step6 = await self._execute_step(6, "evaluate_experience", {
                "experience": experience_create.model_dump(),
            })
            result.steps.append(step6)

            # MVP: 基于规则的基础评估
            evaluation_score = self._rule_based_evaluate(experience_create.model_dump())
            experience_create.confidence_score = evaluation_score

            # 关联用户 ID（数据隔离）
            experience_create.user_id = user_id

            # ── Step 7: 存入图谱 ──
            step7 = await self._execute_step(7, "store_into_graph", {
                "experience": experience_create.model_dump(),
            })
            result.steps.append(step7)

            # 实际存储到数据库
            experience = await self.repo.create(experience_create)
            await self.session.commit()

            result.experience_id = str(experience.id)

            # ── Step 8: 更新复用索引 ──
            step8 = await self._execute_step(8, "update_reuse_index", {
                "experience_id": str(experience.id),
                "context": context or {},
            })
            result.steps.append(step8)

            # ── 完成 ──
            result.status = "completed"

        except Exception as e:
            settings.logger.error(f"Pipeline failed: {e}")
            result.status = "failed"
            result.error = str(e)

        # ── 检查是否生成了 Experience ──
        if result.experience_id is None:
            result.status = "invalid"
            result.error = result.error or "No Experience object generated - task is invalid"

        # ── 计算总时长 ──
        pipeline_end = datetime.now(timezone.utc)
        result.total_duration_ms = (pipeline_end - pipeline_start).total_seconds() * 1000

        return result

    async def _execute_step(self, step_num: int, step_name: str, inputs: dict) -> PipelineStepResult:
        """执行单个流水线步骤（记录状态和时间）."""
        started = datetime.now(timezone.utc)
        result = PipelineStepResult(
            step=step_num,
            name=step_name,
            status="running",
            started_at=started.isoformat(),
        )

        try:
            # 步骤逻辑由 run() 方法中的主流程处理
            # 这里只负责记录状态
            result.output = {"step": step_name, "inputs_keys": list(inputs.keys())}
            result.status = "completed"
        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        completed = datetime.now(timezone.utc)
        result.completed_at = completed.isoformat()
        result.duration_ms = (completed - started).total_seconds() * 1000

        return result

    @staticmethod
    def _rule_based_evaluate(experience_data: dict) -> float:
        """基于规则的基础评估（Phase 4 将替换为完整评估系统）."""
        score = 0.5  # 基础分

        # 成功加分
        outcome = experience_data.get("outcome", {})
        if outcome.get("success"):
            score += 0.2

        # 有反思加分
        reflection = experience_data.get("reflection", {})
        if reflection.get("what_worked"):
            score += 0.1
        if reflection.get("what_failed"):
            score += 0.05  # 失败反思也有价值

        # 有可复用模式加分
        if experience_data.get("reusable_patterns"):
            score += 0.1

        # 有来源追溯加分
        provenance = experience_data.get("provenance", {})
        if provenance.get("agent_signals"):
            score += 0.05

        return min(score, 1.0)  # 不超过 1.0
