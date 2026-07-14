"""Execution engine - 任务执行核心引擎.

Agent 执行层的核心，负责：
- 接收任务并执行
- 调用工具（通过 ToolRegistry）
- 执行工作流
- 生成执行追踪记录
"""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.core.config import settings
from app.services.execution.tools import ToolRegistry, ToolResult, default_registry
from app.services.execution.trace import ExecutionTracer


class TaskInput:
    """任务输入."""

    def __init__(
        self,
        intent: str,
        context: dict | None = None,
        constraints: dict | None = None,
        workflow: list[dict] | None = None,
    ) -> None:
        self.intent = intent
        self.context = context or {}
        self.constraints = constraints or {}
        self.workflow = workflow or []
        self.task_id = str(uuid4())


class TaskOutput:
    """任务输出."""

    def __init__(
        self,
        task_id: str,
        success: bool,
        result: Any = None,
        error: str | None = None,
        trace: dict | None = None,
        steps: list[dict] | None = None,
        tools: list[str] | None = None,
        duration: float = 0.0,
    ) -> None:
        self.task_id = task_id
        self.success = success
        self.result = result
        self.error = error
        self.trace = trace or {}
        self.steps = steps or []
        self.tools = tools or []
        self.duration = duration

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "trace": self.trace,
            "steps": self.steps,
            "tools": self.tools,
            "duration": self.duration,
        }


class ExecutionEngine:
    """执行引擎 - 任务执行的核心.

    职责:
        - execute_task(task_input): 执行单个任务
        - call_tool(tool_name, params): 调用注册的工具
        - run_workflow(workflow_def): 执行工作流（多步骤）
    """

    def __init__(self, tool_registry: ToolRegistry | None = None) -> None:
        self.registry = tool_registry or default_registry

    async def execute_task(self, task_input: TaskInput) -> TaskOutput:
        """执行单个任务.

        Args:
            task_input: 任务输入（意图、上下文、约束）

        Returns:
            TaskOutput: 执行结果（含追踪记录）
        """
        tracer = ExecutionTracer(task_input.task_id, task_input.intent)
        start_time = datetime.now(timezone.utc)

        try:
            # ── 如果有工作流定义，按工作流执行 ──
            if task_input.workflow:
                return await self._run_workflow_steps(task_input, tracer, start_time)

            # ── 否则执行单步任务 ──
            step_idx = tracer.start_step(
                step_name="execute",
                action="single_task",
                inputs={"intent": task_input.intent, "context": task_input.context},
            )

            # 模拟任务执行（实际执行由具体 Agent 框架接入）
            result = {
                "intent": task_input.intent,
                "context": task_input.context,
                "executed_at": datetime.now(timezone.utc).isoformat(),
            }

            tracer.complete_current_step(outputs=result)
            tracer.finalize(status="completed")

            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()

            return TaskOutput(
                task_id=task_input.task_id,
                success=True,
                result=result,
                trace=tracer.get_trace_dict(),
                steps=[s.to_dict() for s in tracer.record.steps],
                tools=tracer.record.tools_used,
                duration=duration,
            )

        except Exception as e:
            settings.logger.error(f"Task execution failed: {e}")
            tracer.complete_current_step(error=str(e))
            tracer.finalize(status="failed", error=str(e))

            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()

            return TaskOutput(
                task_id=task_input.task_id,
                success=False,
                error=str(e),
                trace=tracer.get_trace_dict(),
                duration=duration,
            )

    async def call_tool(self, tool_name: str, **params: Any) -> ToolResult:
        """调用注册的工具.

        Args:
            tool_name: 工具名称
            **params: 工具参数

        Returns:
            ToolResult: 工具执行结果

        Raises:
            ValueError: 工具未注册
        """
        tool = self.registry.get(tool_name)
        if tool is None:
            raise ValueError(f"Tool '{tool_name}' not registered")

        result = await tool.execute(**params)
        return result

    async def run_workflow(self, workflow_def: list[dict], task_input: TaskInput) -> TaskOutput:
        """执行工作流.

        Args:
            workflow_def: 工作流定义（步骤列表）
            task_input: 任务输入

        Returns:
            TaskOutput: 执行结果
        """
        task_input.workflow = workflow_def
        return await self.execute_task(task_input)

    async def _run_workflow_steps(
        self, task_input: TaskInput, tracer: ExecutionTracer, start_time: datetime
    ) -> TaskOutput:
        """执行工作流步骤."""
        results: list[dict] = []

        for i, step_def in enumerate(task_input.workflow):
            step_name = step_def.get("name", f"step_{i}")
            action = step_def.get("action", "execute")
            tool_name = step_def.get("tool")
            params = step_def.get("params", {})

            step_idx = tracer.start_step(
                step_name=step_name,
                action=action,
                inputs=params,
            )

            # ── 如果指定了工具，调用工具 ──
            if tool_name and self.registry.has(tool_name):
                tool_result = await self.call_tool(tool_name, **params)
                tracer.record_tool(tool_name, params, tool_result.to_dict())

                if not tool_result.success:
                    tracer.complete_current_step(
                        outputs=tool_result.to_dict(),
                        error=tool_result.error,
                    )
                    tracer.finalize(status="failed", error=f"Step '{step_name}' failed: {tool_result.error}")
                    end_time = datetime.now(timezone.utc)
                    duration = (end_time - start_time).total_seconds()
                    return TaskOutput(
                        task_id=task_input.task_id,
                        success=False,
                        error=f"Step '{step_name}' failed: {tool_result.error}",
                        trace=tracer.get_trace_dict(),
                        steps=[s.to_dict() for s in tracer.record.steps],
                        tools=tracer.record.tools_used,
                        duration=duration,
                    )

                results.append({
                    "step": step_name,
                    "tool": tool_name,
                    "result": tool_result.to_dict(),
                })
                tracer.complete_current_step(outputs=tool_result.to_dict())
            else:
                # ── 无工具的步骤（模拟执行）──
                step_result = {"step": step_name, "action": action, "status": "completed"}
                results.append(step_result)
                tracer.complete_current_step(outputs=step_result)

        tracer.finalize(status="completed")
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()

        return TaskOutput(
            task_id=task_input.task_id,
            success=True,
            result={"steps": results},
            trace=tracer.get_trace_dict(),
            steps=[s.to_dict() for s in tracer.record.steps],
            tools=tracer.record.tools_used,
            duration=duration,
        )
