"""管理员 API 路由."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db_session
from app.models.agent import Agent
from app.models.experience import Experience
from app.models.user import User

router = APIRouter()


# ── 请求模型 ──


class UserUpdateRequest(BaseModel):
    """管理员更新用户请求."""

    is_active: bool | None = Field(None, description="是否激活")
    is_admin: bool | None = Field(None, description="是否管理员")


class ExperienceStatusUpdate(BaseModel):
    """经验状态更新请求."""

    evaluation_status: str = Field(
        ...,
        pattern="^(pending|evaluated|skipped|approved|rejected)$",
        description="审核状态",
    )


# ── 用户管理 ──


@router.get("/users", summary="列出所有用户（分页）")
async def list_users(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
):
    result = await session.execute(
        select(User)
        .order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    users = result.scalars().all()
    total_result = await session.execute(select(func.count(User.id)))
    total = total_result.scalar() or 0
    return {
        "items": [
            {
                "id": str(u.id),
                "email": u.email,
                "username": u.username,
                "is_active": u.is_active,
                "is_admin": u.is_admin,
                "bio": u.bio,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "updated_at": u.updated_at.isoformat() if u.updated_at else None,
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/users/{user_id}", summary="获取用户详情")
async def get_user(
    user_id: UUID,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "用户不存在")
    return {
        "id": str(user.id),
        "email": user.email,
        "username": user.username,
        "is_active": user.is_active,
        "is_admin": user.is_admin,
        "bio": user.bio,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }


@router.put("/users/{user_id}", summary="更新用户（激活/禁用/设为管理员）")
async def update_user(
    user_id: UUID,
    data: UserUpdateRequest,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "用户不存在")

    if data.is_active is not None:
        user.is_active = data.is_active
    if data.is_admin is not None:
        user.is_admin = data.is_admin

    await session.flush()
    return {
        "id": str(user.id),
        "email": user.email,
        "username": user.username,
        "is_active": user.is_active,
        "is_admin": user.is_admin,
    }


@router.delete("/users/{user_id}", summary="删除用户", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "用户不存在")
    # 防止管理员删除自己
    if user.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "不能删除当前登录的管理员账户")
    await session.delete(user)
    await session.flush()


# ── 经验审核 ──


@router.get("/experiences", summary="列出所有经验（含用户信息，分页）")
async def list_experiences(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
):
    # 查询经验及其关联用户（左连接，因为 user_id 可为空）
    query = (
        select(Experience, User)
        .outerjoin(User, Experience.user_id == User.id)
        .order_by(Experience.created_at.desc())
    )
    offset = (page - 1) * page_size
    result = await session.execute(query.offset(offset).limit(page_size))
    rows = result.all()

    total_result = await session.execute(select(func.count(Experience.id)))
    total = total_result.scalar() or 0

    items = []
    for exp, user in rows:
        item = exp.to_dict()
        item["user"] = (
            {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
            }
            if user
            else None
        )
        items.append(item)

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.delete(
    "/experiences/{experience_id}",
    summary="删除经验（管理员审核不通过）",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_experience(
    experience_id: UUID,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
):
    experience = await session.get(Experience, experience_id)
    if not experience:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "经验不存在")
    await session.delete(experience)
    await session.flush()


@router.put("/experiences/{experience_id}/status", summary="更新经验状态")
async def update_experience_status(
    experience_id: UUID,
    data: ExperienceStatusUpdate,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
):
    experience = await session.get(Experience, experience_id)
    if not experience:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "经验不存在")
    experience.evaluation_status = data.evaluation_status
    await session.flush()
    return {
        "id": str(experience.id),
        "evaluation_status": experience.evaluation_status,
    }


# ── Agent 管理 ──


@router.get("/agents", summary="列出所有 Agent")
async def list_agents(
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
):
    result = await session.execute(select(Agent).order_by(Agent.created_at.desc()))
    agents = result.scalars().all()
    return {
        "items": [
            {
                "id": str(a.id),
                "name": a.name,
                "api_key": a.api_key[:8] + "...",
                "is_active": a.is_active,
                "user_id": str(a.user_id),
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "last_active_at": a.last_active_at.isoformat() if a.last_active_at else None,
            }
            for a in agents
        ]
    }


# ── 系统统计 ──


@router.get("/stats", summary="系统统计")
async def system_stats(
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
):
    # 用户统计
    total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0
    active_users = (
        await session.execute(
            select(func.count(User.id)).where(User.is_active.is_(True))
        )
    ).scalar() or 0
    admin_users = (
        await session.execute(
            select(func.count(User.id)).where(User.is_admin.is_(True))
        )
    ).scalar() or 0

    # Agent 统计
    total_agents = (await session.execute(select(func.count(Agent.id)))).scalar() or 0
    active_agents = (
        await session.execute(
            select(func.count(Agent.id)).where(Agent.is_active.is_(True))
        )
    ).scalar() or 0

    # 经验统计
    total_experiences = (
        await session.execute(select(func.count(Experience.id)))
    ).scalar() or 0
    evaluated_experiences = (
        await session.execute(
            select(func.count(Experience.id)).where(
                Experience.evaluation_status == "evaluated"
            )
        )
    ).scalar() or 0
    pending_experiences = (
        await session.execute(
            select(func.count(Experience.id)).where(
                Experience.evaluation_status == "pending"
            )
        )
    ).scalar() or 0

    # 活跃度：最近 7 天数据
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent_experiences = (
        await session.execute(
            select(func.count(Experience.id)).where(
                Experience.created_at >= seven_days_ago
            )
        )
    ).scalar() or 0
    recent_users = (
        await session.execute(
            select(func.count(User.id)).where(User.created_at >= seven_days_ago)
        )
    ).scalar() or 0

    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "admins": admin_users,
            "recent_7d": recent_users,
        },
        "agents": {
            "total": total_agents,
            "active": active_agents,
        },
        "experiences": {
            "total": total_experiences,
            "evaluated": evaluated_experiences,
            "pending": pending_experiences,
            "recent_7d": recent_experiences,
        },
    }
