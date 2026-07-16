"""Community API routes - 社区管理."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session
from app.models.community import Community, user_community
from app.models.user import User
from app.schemas.community import (
    CommunityCreate,
    CommunityListResponse,
    CommunityMemberResponse,
    CommunityResponse,
    CommunityUpdate,
)

router = APIRouter()


@router.post(
    "",
    response_model=CommunityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建社区",
)
async def create_community(
    data: CommunityCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CommunityResponse:
    """创建新社区，创建者自动成为 admin 成员."""
    community = Community(
        name=data.name,
        description=data.description,
        visibility=data.visibility,
        owner_id=current_user.id,
    )
    session.add(community)
    await session.flush()

    # 创建者自动加入为 admin
    await session.execute(
        user_community.insert().values(
            user_id=current_user.id,
            community_id=community.id,
            role="admin",
        )
    )
    await session.flush()
    await session.refresh(community)

    return CommunityResponse(
        id=community.id,
        name=community.name,
        description=community.description or "",
        owner_id=community.owner_id,
        visibility=community.visibility,
        member_count=1,
        created_at=community.created_at,
        updated_at=community.updated_at,
    )


@router.get(
    "",
    response_model=CommunityListResponse,
    summary="列出社区",
)
async def list_communities(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CommunityListResponse:
    """列出当前用户可见的社区（自己创建或已加入的）."""
    query = select(Community).where(
        (Community.owner_id == current_user.id)
        | (
            Community.id.in_(
                select(user_community.c.community_id).where(
                    user_community.c.user_id == current_user.id
                )
            )
        )
        | (Community.visibility == "open")
    )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    offset = (page - 1) * page_size
    query = query.order_by(Community.created_at.desc()).offset(offset).limit(page_size)
    result = await session.execute(query)
    communities = result.scalars().all()

    items = []
    for c in communities:
        member_count_q = select(func.count()).select_from(
            user_community.select().where(user_community.c.community_id == c.id).subquery()
        )
        mc = (await session.execute(member_count_q)).scalar() or 0
        items.append(
            CommunityResponse(
                id=c.id,
                name=c.name,
                description=c.description or "",
                owner_id=c.owner_id,
                visibility=c.visibility,
                member_count=mc,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
        )

    return CommunityListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get(
    "/{community_id}",
    response_model=CommunityResponse,
    summary="获取社区详情",
)
async def get_community(
    community_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CommunityResponse:
    result = await session.execute(
        select(Community).where(Community.id == community_id)
    )
    community = result.scalar_one_or_none()
    if community is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="社区不存在")

    member_count_q = select(func.count()).select_from(
        user_community.select().where(user_community.c.community_id == community.id).subquery()
    )
    mc = (await session.execute(member_count_q)).scalar() or 0

    return CommunityResponse(
        id=community.id,
        name=community.name,
        description=community.description or "",
        owner_id=community.owner_id,
        visibility=community.visibility,
        member_count=mc,
        created_at=community.created_at,
        updated_at=community.updated_at,
    )


@router.post(
    "/{community_id}/join",
    response_model=CommunityMemberResponse,
    summary="加入社区",
)
async def join_community(
    community_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CommunityMemberResponse:
    """加入社区（open 类型可直接加入，invite 类型需要邀请）."""
    result = await session.execute(
        select(Community).where(Community.id == community_id)
    )
    community = result.scalar_one_or_none()
    if community is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="社区不存在")

    if community.visibility == "invite":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该社区仅限邀请加入",
        )

    # 检查是否已加入
    existing = await session.execute(
        user_community.select().where(
            user_community.c.user_id == current_user.id,
            user_community.c.community_id == community_id,
        )
    )
    if existing.first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="已加入该社区",
        )

    from datetime import datetime, timezone

    await session.execute(
        user_community.insert().values(
            user_id=current_user.id,
            community_id=community_id,
            role="member",
            joined_at=datetime.now(timezone.utc),
        )
    )
    await session.flush()

    return CommunityMemberResponse(
        user_id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role="member",
        joined_at=datetime.now(timezone.utc),
    )


@router.post(
    "/{community_id}/leave",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="离开社区",
)
async def leave_community(
    community_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """离开社区。社区所有者不能离开。."""
    result = await session.execute(
        select(Community).where(Community.id == community_id)
    )
    community = result.scalar_one_or_none()
    if community is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="社区不存在")

    if community.owner_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="社区所有者不能离开，请先转移所有权",
        )

    delete_result = await session.execute(
        user_community.delete().where(
            user_community.c.user_id == current_user.id,
            user_community.c.community_id == community_id,
        )
    )
    if delete_result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未加入该社区",
        )


@router.get(
    "/{community_id}/members",
    response_model=list[CommunityMemberResponse],
    summary="列出社区成员",
)
async def list_members(
    community_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[CommunityMemberResponse]:
    """列出社区的所有成员."""
    result = await session.execute(
        user_community.select().where(user_community.c.community_id == community_id)
    )
    rows = result.fetchall()

    members = []
    for row in rows:
        user_result = await session.execute(
            select(User).where(User.id == row.user_id)
        )
        user = user_result.scalar_one_or_none()
        if user:
            members.append(
                CommunityMemberResponse(
                    user_id=user.id,
                    username=user.username,
                    email=user.email,
                    role=row.role,
                    joined_at=row.joined_at,
                )
            )

    return members
