"""Pydantic schemas for WorkflowTemplate objects - API contracts."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class WorkflowTemplateBase(BaseModel):
    """WorkflowTemplate 基础字段（创建和更新共用）."""

    name: str = Field(..., min_length=1, max_length=200, description="模板名称")
    description: str | None = Field(None, description="模板描述")
    domain: str = Field(..., min_length=1, max_length=100, description="领域（如 devops, testing, debugging）")
    task_type: str = Field(..., min_length=1, max_length=100, description="任务类型（如 deployment, unit_test）")
    steps: list[dict] = Field(default_factory=list, description="工作流步骤列表")
    tools: list[str] = Field(default_factory=list, description="使用的工具列表")
    expected_outcome: dict = Field(default_factory=dict, description="预期结果")
    visibility: str = Field(
        default="public",
        pattern="^(public|private)$",
        description="可见性: public(所有人) | private(仅创建者)",
    )

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be empty")
        return v.strip()

    @field_validator("domain")
    @classmethod
    def domain_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("domain must not be empty")
        return v.strip()

    @field_validator("task_type")
    @classmethod
    def task_type_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("task_type must not be empty")
        return v.strip()


class WorkflowTemplateCreate(WorkflowTemplateBase):
    """创建 WorkflowTemplate 请求."""

    pass


class WorkflowTemplateUpdate(BaseModel):
    """更新 WorkflowTemplate 请求（所有字段可选）."""

    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    domain: str | None = Field(None, min_length=1, max_length=100)
    task_type: str | None = Field(None, min_length=1, max_length=100)
    steps: list[dict] | None = None
    tools: list[str] | None = None
    expected_outcome: dict | None = None
    visibility: str | None = Field(None, pattern="^(public|private)$")


class WorkflowTemplateResponse(WorkflowTemplateBase):
    """WorkflowTemplate 响应."""

    id: UUID
    success_rate: float
    usage_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkflowTemplateListResponse(BaseModel):
    """工作流模板列表响应（分页）."""

    items: list[WorkflowTemplateResponse]
    total: int
    page: int
    page_size: int
