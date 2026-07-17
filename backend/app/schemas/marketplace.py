"""Pydantic schemas for Marketplace - API contracts."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── ExperienceListing schemas ──


class ListingCreate(BaseModel):
    """创建挂单请求."""

    experience_id: UUID = Field(..., description="经验 ID")
    title: str = Field(..., min_length=1, max_length=200, description="标题")
    description: str = Field(default="", description="描述")
    price: float = Field(default=0.0, ge=0.0, description="价格（0.0 = 免费）")
    currency: str = Field(default="USD", max_length=10, description="货币")
    license_type: str = Field(
        default="free",
        pattern="^(free|paid|subscription|exclusive)$",
        description="许可类型",
    )


class ListingUpdate(BaseModel):
    """更新挂单请求（所有字段可选）."""

    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    price: float | None = Field(None, ge=0.0)
    currency: str | None = Field(None, max_length=10)
    license_type: str | None = Field(None, pattern="^(free|paid|subscription|exclusive)$")


class ListingResponse(BaseModel):
    """挂单响应."""

    id: UUID
    experience_id: UUID
    seller_id: UUID
    title: str
    description: str
    price: float
    currency: str
    license_type: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ListingListResponse(BaseModel):
    """挂单列表响应（分页）."""

    items: list[ListingResponse]
    total: int
    page: int
    page_size: int


# ── Transaction schemas ──


class TransactionResponse(BaseModel):
    """交易响应."""

    id: UUID
    listing_id: UUID
    buyer_id: UUID
    seller_id: UUID
    amount: float
    currency: str
    status: str
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class TransactionListResponse(BaseModel):
    """交易列表响应（分页）."""

    items: list[TransactionResponse]
    total: int
    page: int
    page_size: int


class PurchaseResponse(BaseModel):
    """购买响应."""

    transaction: TransactionResponse
    listing_status: str = Field(..., description="挂单交易后的状态")
