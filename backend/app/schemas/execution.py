"""Pydantic schemas for Execution objects."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TaskSubmitRequest(BaseModel):
    """提交任务请求."""

    intent: str = Field(..., min_length=1, max_length=2000, description="任务意图")
    context: dict = Field(default_factory=dict, description="任务上下文")
    constraints: dict = Field(default_factory=dict, description="约束条件")


class PipelineStateStep(BaseModel):
    """8 步流水线中单步状态."""

    name: str
    status: str = Field(pattern="^(pending|running|completed|failed|skipped)$")
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: dict | None = None


class ExecutionTraceResponse(BaseModel):
    """执行追踪响应."""

    id: UUID
    experience_id: UUID | None = None
    intent: str
    context: dict
    status: str
    steps: list[dict] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    trace: dict = Field(default_factory=dict)
    duration: float | None = None
    error: str | None = None
    pipeline_state: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskStatusResponse(BaseModel):
    """任务状态响应."""

    id: UUID
    status: str
    intent: str
    experience_id: UUID | None = None
    pipeline_state: dict = Field(default_factory=dict)
    duration: float | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
