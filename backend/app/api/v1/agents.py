"""Agent 管理 API 路由 - 注册、列表、删除、重新生成 API Key."""

from __future__ import annotations

import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session
from app.models.agent import Agent
from app.models.user import User
from app.schemas.agent import AgentCreate, AgentResponse, AgentWithKey

router = APIRouter()


def _generate_api_key() -> str:
    """生成安全的随机 API Key."""
    return secrets.token_urlsafe(32)


@router.post(
    "",
    response_model=AgentWithKey,
    status_code=status.HTTP_201_CREATED,
    summary="注册新 Agent",
    description="创建一个新的 Agent 并返回 API Key（仅在创建时返回）。",
)
async def create_agent(
    data: AgentCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> AgentWithKey:
    agent = Agent(
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        api_key=_generate_api_key(),
        capabilities=data.capabilities,
    )
    session.add(agent)
    await session.flush()
    return AgentWithKey.model_validate(agent)


@router.get(
    "",
    response_model=list[AgentResponse],
    summary="列出我的 Agent",
    description="返回当前用户注册的所有 Agent。",
)
async def list_agents(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[AgentResponse]:
    result = await session.execute(
        select(Agent)
        .where(Agent.user_id == current_user.id)
        .order_by(Agent.created_at.desc())
    )
    agents = result.scalars().all()
    return [AgentResponse.model_validate(a) for a in agents]


@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除 Agent",
    description="删除指定的 Agent（仅限所有者）。",
)
async def delete_agent(
    agent_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    result = await session.execute(
        select(Agent).where(
            Agent.id == agent_id, Agent.user_id == current_user.id
        )
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent 不存在",
        )
    await session.delete(agent)


@router.post(
    "/{agent_id}/regenerate-key",
    response_model=AgentWithKey,
    summary="重新生成 API Key",
    description="为指定 Agent 重新生成 API Key（旧 Key 失效）。",
)
async def regenerate_key(
    agent_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> AgentWithKey:
    result = await session.execute(
        select(Agent).where(
            Agent.id == agent_id, Agent.user_id == current_user.id
        )
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent 不存在",
        )
    agent.api_key = _generate_api_key()
    await session.flush()
    return AgentWithKey.model_validate(agent)
