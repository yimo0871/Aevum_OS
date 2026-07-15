"""认证 API 路由 - 注册、登录、个人信息管理."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import (
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)

router = APIRouter()


@router.post(
    "/register",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    summary="用户注册",
    description="创建新用户并返回 JWT token。",
)
async def register(
    data: UserCreate,
    session: AsyncSession = Depends(get_db_session),
) -> Token:
    # 检查邮箱或用户名是否已被注册
    existing = await session.execute(
        select(User).where(
            or_(User.email == data.email, User.username == data.username)
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="邮箱或用户名已被注册",
        )

    user = User(
        email=data.email,
        username=data.username,
        hashed_password=get_password_hash(data.password),
    )
    session.add(user)
    await session.flush()

    access_token = create_access_token(
        {"sub": str(user.id), "username": user.username}
    )
    return Token(access_token=access_token, user=UserResponse.model_validate(user))


@router.post(
    "/login",
    response_model=Token,
    summary="用户登录",
    description="验证凭据并返回 JWT token。",
)
async def login(
    data: UserLogin,
    session: AsyncSession = Depends(get_db_session),
) -> Token:
    result = await session.execute(
        select(User).where(or_(User.email == data.username, User.username == data.username))
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )

    access_token = create_access_token(
        {"sub": str(user.id), "username": user.username}
    )
    return Token(access_token=access_token, user=UserResponse.model_validate(user))


@router.get(
    "/me",
    response_model=UserResponse,
    summary="获取当前用户信息",
    description="返回当前登录用户的详细信息。",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.put(
    "/me",
    response_model=UserResponse,
    summary="更新个人信息",
    description="更新当前登录用户的用户名或个人简介。",
)
async def update_me(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    if data.username is not None and data.username != current_user.username:
        # 检查用户名唯一性
        existing = await session.execute(
            select(User).where(
                User.username == data.username, User.id != current_user.id
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="用户名已被占用",
            )
        current_user.username = data.username

    if data.bio is not None:
        current_user.bio = data.bio

    await session.flush()
    return UserResponse.model_validate(current_user)
