"""Execution tracer - 执行追踪记录器.

对应 8 步流水线中的 Step 4: record_full_trace
记录每步操作、工具调用、中间结果，生成结构化 trace 对象。
"""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class TraceStep(BaseModel):
    """追踪中的单步记录."""

    step_index: int
    step_name: str
    action: str = ""
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    duration_ms: float | None = None
    inputs: dict = Field(default_factory=dict)
    outputs: Any = None
    error: str | None = None
    status: str = "pending"  # pending | running | completed | failed

    def to_dict(self) -> dict:
        return {
            "step_index": self.step_index,
            "step_name": self.step_name,
            "action": self.action,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "error": self.error,
            "status": self.status,
        }


class TraceRecord(BaseModel):
    """完整执行追踪记录."""

    task_id: str
    intent: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    total_duration_ms: float | None = None
    steps: list[TraceStep] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    tool_calls: list[dict] = Field(default_factory=list)
    final_status: str = "running"  # running | completed | failed | invalid
    error: str | None = None

    def add_step(self, step_name: str, action: str = "", inputs: dict | None = None) -> TraceStep:
        """添加一个追踪步骤."""
        step = TraceStep(
            step_index=len(self.steps),
            step_name=step_name,
            action=action,
            inputs=inputs or {},
            status="running",
        )
        self.steps.append(step)
        return step

    def complete_step(self, step_index: int, outputs: Any = None, error: str | None = None) -> None:
        """完成一个追踪步骤."""
        if step_index < len(self.steps):
            step = self.steps[step_index]
            step.completed_at = datetime.now(timezone.utc)
            if step.started_at:
                step.duration_ms = (step.completed_at - step.started_at).total_seconds() * 1000
            step.outputs = outputs
            step.error = error
            step.status = "failed" if error else "completed"

    def record_tool_call(self, tool_name: str, params: dict, result: dict) -> None:
        """记录工具调用."""
        if tool_name not in self.tools_used:
            self.tools_used.append(tool_name)
        self.tool_calls.append({
            "tool": tool_name,
            "params": params,
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def finalize(self, status: str = "completed", error: str | None = None) -> None:
        """完成追踪记录."""
        self.completed_at = datetime.now(timezone.utc)
        if self.started_at:
            self.total_duration_ms = (self.completed_at - self.started_at).total_seconds() * 1000
        self.final_status = status
        self.error = error

    def to_dict(self) -> dict:
        """转为字典（用于存储到 JSONB 列）."""
        return {
            "task_id": self.task_id,
            "intent": self.intent,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_duration_ms": self.total_duration_ms,
            "steps": [s.to_dict() for s in self.steps],
            "tools_used": self.tools_used,
            "tool_calls": self.tool_calls,
            "final_status": self.final_status,
            "error": self.error,
        }


class ExecutionTracer:
    """执行追踪器 - 管理一次任务执行的完整追踪."""

    def __init__(self, task_id: str, intent: str) -> None:
        self.record = TraceRecord(task_id=task_id, intent=intent)
        self._current_step: TraceStep | None = None

    def start_step(self, step_name: str, action: str = "", inputs: dict | None = None) -> int:
        """开始一个新步骤，返回步骤索引."""
        step = self.record.add_step(step_name, action, inputs)
        self._current_step = step
        return step.step_index

    def complete_current_step(self, outputs: Any = None, error: str | None = None) -> None:
        """完成当前步骤."""
        if self._current_step is not None:
            self.record.complete_step(self._current_step.step_index, outputs, error)
            self._current_step = None

    def record_tool(self, tool_name: str, params: dict, result: dict) -> None:
        """记录工具调用."""
        self.record.record_tool_call(tool_name, params, result)

    def finalize(self, status: str = "completed", error: str | None = None) -> TraceRecord:
        """完成追踪."""
        self.record.finalize(status, error)
        return self.record

    def get_trace_dict(self) -> dict:
        """获取追踪字典."""
        return self.record.to_dict()
