"""Retrieval API routes - 经验检索接口."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session, get_optional_user
from app.models.community import user_community
from app.models.user import User
from app.schemas.experience import (
    ExperienceResponse,
    ExperienceSearchRequest,
    ExperienceSearchResult,
)
from app.services.retrieval.priority_chain import PriorityChain

router = APIRouter()


async def _get_user_community_ids(session: AsyncSession, user_id: str) -> list[str]:
    """查询用户所属的社区 ID 列表."""
    result = await session.execute(
        select(user_community.c.community_id).where(
            user_community.c.user_id == user_id
        )
    )
    return [str(row[0]) for row in result.fetchall()]


@router.post(
    "/search",
    response_model=list[ExperienceSearchResult],
    summary="搜索经验",
    description="通过四级优先级链检索相似经验：用户经验 -> 社区经验 -> 全球经验 -> 外部网络。",
)
async def search_experiences(
    request: ExperienceSearchRequest,
    current_user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[ExperienceSearchResult]:
    """搜索经验 - 四级优先级链检索."""
    user_id = str(current_user.id) if current_user else None
    community_ids = await _get_user_community_ids(session, user_id) if user_id else None
    chain = PriorityChain(session, min_results=request.limit, max_results=request.limit * 2)

    chain_results = await chain.search(
        query=request.query,
        domain=request.domain,
        task_type=request.task_type,
        user_id=user_id,
        community_ids=community_ids,
    )

    best_results = chain.get_best_results(chain_results, limit=request.limit)

    # 过滤最低置信度
    best_results = [r for r in best_results if r.experience.confidence_score >= request.min_confidence]

    return [
        ExperienceSearchResult(
            experience=ExperienceResponse.model_validate(r.experience),
            score=r.total_score,
            matched_factors=r.factors.to_dict(),
        )
        for r in best_results
    ]


@router.get(
    "/recommend",
    response_model=list[ExperienceSearchResult],
    summary="推荐经验",
    description="基于上下文自动推荐相关经验。",
)
async def recommend_experiences(
    query: str = Query(..., min_length=1, description="推荐查询"),
    domain: str | None = Query(None, description="领域"),
    task_type: str | None = Query(None, description="任务类型"),
    limit: int = Query(5, ge=1, le=20, description="推荐数量"),
    current_user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[ExperienceSearchResult]:
    """推荐经验."""
    user_id = str(current_user.id) if current_user else None
    community_ids = await _get_user_community_ids(session, user_id) if user_id else None
    chain = PriorityChain(session, min_results=limit, max_results=limit * 2)

    chain_results = await chain.search(
        query=query,
        domain=domain,
        task_type=task_type,
        user_id=user_id,
        community_ids=community_ids,
    )

    best_results = chain.get_best_results(chain_results, limit=limit)

    return [
        ExperienceSearchResult(
            experience=ExperienceResponse.model_validate(r.experience),
            score=r.total_score,
            matched_factors=r.factors.to_dict(),
        )
        for r in best_results
    ]


@router.get(
    "/priority-chain",
    summary="查看优先级链执行详情",
    description="返回四级优先级链的完整执行结果，用于调试和分析。",
)
async def search_with_priority_chain(
    query: str = Query(..., min_length=1, description="搜索查询"),
    domain: str | None = Query(None, description="领域"),
    task_type: str | None = Query(None, description="任务类型"),
    limit: int = Query(10, ge=1, le=50, description="每级最大返回数量"),
    current_user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """查看优先级链执行详情."""
    user_id = str(current_user.id) if current_user else None
    community_ids = await _get_user_community_ids(session, user_id) if user_id else None
    chain = PriorityChain(session, min_results=limit, max_results=limit)

    chain_results = await chain.search(
        query=query,
        domain=domain,
        task_type=task_type,
        user_id=user_id,
        community_ids=community_ids,
    )

    return {
        "query": query,
        "domain": domain,
        "task_type": task_type,
        "chain_results": [r.to_dict() for r in chain_results],
        "best_results": [r.to_dict() for r in chain.get_best_results(chain_results, limit=limit)],
    }
