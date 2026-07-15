"""Pydantic schemas for Agent - API contracts."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    """注册 Agent 请求."""

    name: str = Field(..., min_length=1, max_length=200, description="Agent 名称")
    description: str = Field(default="", max_length=2000, description="Agent 描述")
    capabilities: dict = Field(default_factory=dict, description="Agent 能力描述")


class AgentResponse(BaseModel):
    """Agent 响应（不含 API Key）."""

    id: UUID
    user_id: UUID
    name: str
    description: str
    is_active: bool
    capabilities: dict
    created_at: datetime
    last_active_at: datetime | None = None

    model_config = {"from_attributes": True}


class AgentWithKey(AgentResponse):
    """Agent 响应（含 API Key，仅在创建/重新生成时返回）."""

    api_key: str
