"""Pydantic schemas for HumanExpression - 人类表达层 API 契约."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class HumanExpressionCreate(BaseModel):
    """创建人类表达请求（仅人类 JWT）."""

    type: str = Field(..., pattern="^(text|image|video|audio|link|note)$", description="表达类型")
    content: dict = Field(..., description="原始内容（自由 JSONB）")
    metadata: dict = Field(default_factory=dict, description="可选元数据")


class HumanExpressionUpdate(BaseModel):
    """更新人类表达请求（仅作者）."""

    content: dict | None = None
    metadata: dict | None = None


class HumanExpressionResponse(BaseModel):
    """人类表达响应."""

    id: UUID
    user_id: UUID
    type: str
    content: dict
    metadata: dict = Field(default_factory=dict, alias="metadata_")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class HumanExpressionListResponse(BaseModel):
    """人类表达列表响应."""

    items: list[HumanExpressionResponse]
    total: int
    page: int
    page_size: int


class ObserveRequest(BaseModel):
    """语义搜索请求（Agent 可调用，只读）."""

    query: str = Field(..., min_length=1, description="搜索查询")
    limit: int = Field(5, ge=1, le=50, description="返回数量")
