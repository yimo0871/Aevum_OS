"""Co-creation API routes - 人机协同创作工作流.

工作流:
1. defined: 用户提交任务描述 -> 创建会话
2. exploring: Agent 搜索相关经验，生成方案
3. completed/rejected: 用户评审 Agent 方案
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session
from app.models.cocreation import CoCreationSession
from app.models.experience import Experience
from app.models.user import User
from app.schemas.cocreation import (
    CoCreationExploreResponse,
    CoCreationJudgeRequest,
    CoCreationJudgeResponse,
    CoCreationSessionCreate,
    CoCreationSessionListResponse,
    CoCreationSessionResponse,
)
from app.services.retrieval.matcher import ExperienceMatcher

logger = logging.getLogger(__name__)
router = APIRouter()


# ── 可测试的核心逻辑函数 ──


async def _create_session(
    user_id: UUID,
    data: CoCreationSessionCreate,
    session: AsyncSession,
) -> CoCreationSession:
    """创建协同创作会话."""
    cocreation = CoCreationSession(
        user_id=user_id,
        task_description=data.task_description,
        domain=data.domain,
        human_constraints=data.human_constraints,
        status="defined",
    )
    session.add(cocreation)
    await session.flush()
    await session.refresh(cocreation)
    return cocreation


async def _get_session(
    session_id: UUID,
    user_id: UUID,
    session: AsyncSession,
) -> CoCreationSession | None:
    """获取会话（仅返回属于该用户的会话）."""
    result = await session.execute(
        select(CoCreationSession).where(
            CoCreationSession.id == session_id,
            CoCreationSession.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def _explore_session(
    cocreation: CoCreationSession,
    session: AsyncSession,
) -> list[dict]:
    """Agent 探索方案 - 搜索相关经验并生成方案."""
    cocreation.status = "exploring"

    # 搜索 Aevum 中与任务相关的经验
    matcher = ExperienceMatcher(session)
    matches = await matcher.match_by_keywords(
        query=cocreation.task_description,
        limit=5,
        domain=cocreation.domain,
    )

    # 构建方案
    proposals: list[dict] = []
    for m in matches:
        proposals.append({
            "experience_id": str(m.experience.id),
            "intent": m.experience.intent,
            "confidence_score": m.experience.confidence_score,
            "similarity": m.similarity,
            "approach": f"复用经验: {m.experience.intent[:100]}",
        })

    cocreation.agent_proposals = proposals
    await session.flush()

    return proposals


async def _judge_session(
    cocreation: CoCreationSession,
    data: CoCreationJudgeRequest,
    session: AsyncSession,
) -> CoCreationSession:
    """用户评审 Agent 方案."""
    cocreation.human_feedback = data.feedback
    cocreation.human_rating = data.rating

    if data.accepted:
        cocreation.status = "completed"
        # 将经验存入 Aevum
        experience = Experience(
            intent=cocreation.task_description,
            context={
                "domain": cocreation.domain or "general",
                "task_type": "cocreation",
                "constraints": cocreation.human_constraints,
            },
            execution={},
            outcome={"success": True, "metrics": {"rating": data.rating}},
            reflection={
                "what_worked": ["人机协同创作"],
                "what_failed": [],
                "why": data.feedback or "用户接受方案",
            },
            reusable_patterns=[],
            confidence_score=min(1.0, data.rating / 5.0),
            provenance={
                "human_signals": [{"type": "cocreation", "rating": data.rating}],
                "agent_signals": [],
                "external_sources": [],
            },
            user_id=cocreation.user_id,
            visibility="private",
        )
        session.add(experience)
        await session.flush()
        await session.refresh(experience)
        cocreation.experience_id = experience.id
    else:
        cocreation.status = "rejected"

    await session.flush()
    return cocreation


# ── API 路由 ──


@router.post(
    "/sessions",
    response_model=CoCreationSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建协同创作会话",
    description="提交任务描述，启动一个人机协同创作会话。",
)
async def create_session(
    data: CoCreationSessionCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CoCreationSessionResponse:
    cocreation = await _create_session(current_user.id, data, session)
    return CoCreationSessionResponse.model_validate(cocreation)


@router.get(
    "/sessions/{session_id}",
    response_model=CoCreationSessionResponse,
    summary="获取会话状态",
    description="获取协同创作会话的当前状态。",
)
async def get_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CoCreationSessionResponse:
    cocreation = await _get_session(session_id, current_user.id, session)
    if cocreation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"会话 {session_id} 不存在")
    return CoCreationSessionResponse.model_validate(cocreation)


@router.post(
    "/sessions/{session_id}/explore",
    response_model=CoCreationExploreResponse,
    summary="Agent 探索方案",
    description="Agent 搜索 Aevum 中的相关经验，生成解决方案。",
)
async def explore_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CoCreationExploreResponse:
    cocreation = await _get_session(session_id, current_user.id, session)
    if cocreation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"会话 {session_id} 不存在")

    proposals = await _explore_session(cocreation, session)
    return CoCreationExploreResponse(
        session=CoCreationSessionResponse.model_validate(cocreation),
        proposals=proposals,
        matched_experience_count=len(proposals),
    )


@router.post(
    "/sessions/{session_id}/judge",
    response_model=CoCreationJudgeResponse,
    summary="用户评审方案",
    description="用户对 Agent 方案进行评审。接受则将经验存入 Aevum。",
)
async def judge_session(
    session_id: UUID,
    data: CoCreationJudgeRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CoCreationJudgeResponse:
    cocreation = await _get_session(session_id, current_user.id, session)
    if cocreation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"会话 {session_id} 不存在")

    cocreation = await _judge_session(cocreation, data, session)
    return CoCreationJudgeResponse(
        session=CoCreationSessionResponse.model_validate(cocreation),
        experience_id=cocreation.experience_id,
    )


@router.get(
    "/sessions",
    response_model=CoCreationSessionListResponse,
    summary="列出我的会话",
    description="列出当前用户的所有协同创作会话。",
)
async def list_sessions(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CoCreationSessionListResponse:
    from sqlalchemy import func

    query = (
        select(CoCreationSession)
        .where(CoCreationSession.user_id == current_user.id)
        .order_by(CoCreationSession.created_at.desc())
    )

    count_query = select(func.count()).select_from(
        select(CoCreationSession).where(
            CoCreationSession.user_id == current_user.id
        ).subquery()
    )
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await session.execute(query)
    sessions = list(result.scalars().all())

    return CoCreationSessionListResponse(
        items=[CoCreationSessionResponse.model_validate(s) for s in sessions],
        total=total,
        page=page,
        page_size=page_size,
    )
