"""Pydantic schemas for Co-creation - API contracts."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CoCreationSessionCreate(BaseModel):
    """创建协同创作会话请求."""

    task_description: str = Field(..., min_length=1, description="任务描述")
    domain: str = Field(default="general", max_length=100, description="领域")
    human_constraints: dict = Field(default_factory=dict, description="人类约束条件")


class CoCreationJudgeRequest(BaseModel):
    """用户评审请求."""

    accepted: bool = Field(..., description="是否接受 Agent 方案")
    feedback: str = Field(default="", description="反馈")
    rating: int = Field(default=3, ge=1, le=5, description="评分 1-5")


class CoCreationSessionResponse(BaseModel):
    """协同创作会话响应."""

    id: UUID
    user_id: UUID
    task_description: str
    domain: str
    human_constraints: dict
    agent_proposals: dict | list | None = None
    human_feedback: str | None = None
    human_rating: int | None = None
    status: str
    experience_id: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CoCreationSessionListResponse(BaseModel):
    """会话列表响应（分页）."""

    items: list[CoCreationSessionResponse]
    total: int
    page: int
    page_size: int


class CoCreationExploreResponse(BaseModel):
    """探索结果响应."""

    session: CoCreationSessionResponse
    proposals: list[dict] = Field(default_factory=list, description="Agent 提出的方案")
    matched_experience_count: int = Field(default=0, description="匹配到的经验数量")


class CoCreationJudgeResponse(BaseModel):
    """评审结果响应."""

    session: CoCreationSessionResponse
    experience_id: UUID | None = Field(None, description="若接受则创建的经验 ID")
