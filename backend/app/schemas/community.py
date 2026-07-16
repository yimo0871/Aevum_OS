"""Pydantic schemas for Community - API contracts."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CommunityCreate(BaseModel):
    """创建社区请求."""

    name: str = Field(..., min_length=2, max_length=200, description="社区名称")
    description: str = Field("", max_length=2000, description="描述")
    visibility: str = Field("open", pattern="^(open|invite)$", description="open(自由加入) | invite(仅邀请)")


class CommunityUpdate(BaseModel):
    """更新社区请求."""

    name: str | None = Field(None, min_length=2, max_length=200)
    description: str | None = Field(None, max_length=2000)
    visibility: str | None = Field(None, pattern="^(open|invite)$")


class CommunityResponse(BaseModel):
    """社区响应."""

    id: UUID
    name: str
    description: str
    owner_id: UUID
    visibility: str
    member_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CommunityMemberResponse(BaseModel):
    """社区成员响应."""

    user_id: UUID
    username: str
    email: str
    role: str
    joined_at: datetime

    model_config = {"from_attributes": True}


class CommunityListResponse(BaseModel):
    """社区列表响应."""

    items: list[CommunityResponse]
    total: int
    page: int
    page_size: int
