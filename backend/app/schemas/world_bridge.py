"""Pydantic schemas for WorldBridge - 双世界桥接 API 契约."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class BridgeCreate(BaseModel):
    """创建桥接请求."""

    bridge_type: str = Field(
        ...,
        pattern="^(inspiration|observation|recommendation|reflection)$",
        description="桥接类型: inspiration | observation | recommendation | reflection",
    )
    human_expression_id: UUID = Field(..., description="人类表达 ID")
    experience_id: UUID = Field(..., description="Agent 经验 ID")
    metadata: dict = Field(default_factory=dict, description="桥接元信息")


class BridgeResponse(BaseModel):
    """桥接响应."""

    id: UUID
    bridge_type: str
    human_expression_id: UUID
    experience_id: UUID
    metadata: dict = Field(default_factory=dict)
    created_by: str
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class BridgeListResponse(BaseModel):
    """桥接列表响应."""

    items: list[BridgeResponse]
    total: int
