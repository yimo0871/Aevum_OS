"""Pydantic schemas for User - API contracts."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """注册请求."""

    email: str = Field(..., description="邮箱地址")
    username: str = Field(..., min_length=2, max_length=100, description="用户名")
    password: str = Field(..., min_length=8, max_length=128, description="密码")


class UserLogin(BaseModel):
    """登录请求 - 支持用户名或邮箱."""

    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")


class UserUpdate(BaseModel):
    """更新个人信息请求."""

    username: str | None = Field(None, min_length=2, max_length=100, description="用户名")
    bio: str | None = Field(None, max_length=2000, description="个人简介")


class UserResponse(BaseModel):
    """用户响应（不含密码）."""

    id: UUID
    email: str
    username: str
    is_active: bool
    is_admin: bool
    bio: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    """JWT Token 响应."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    """Token 解析后的数据."""

    user_id: str | None = None
    username: str | None = None
