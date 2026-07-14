"""Retrieval API routes - 经验检索接口."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.schemas.experience import (
    ExperienceResponse,
    ExperienceSearchRequest,
    ExperienceSearchResult,
)
from app.services.retrieval.priority_chain import PriorityChain

router = APIRouter()


@router.post(
    "/search",
    response_model=list[ExperienceSearchResult],
    summary="搜索经验",
    description="通过四级优先级链检索相似经验：用户经验 -> 社区经验 -> 全球经验 -> 外部网络。",
)
async def search_experiences(
    request: ExperienceSearchRequest,
    session: AsyncSession = Depends(get_db_session),
) -> list[ExperienceSearchResult]:
    """搜索经验 - 四级优先级链检索."""
    chain = PriorityChain(session, min_results=request.limit, max_results=request.limit * 2)

    chain_results = await chain.search(
        query=request.query,
        domain=request.domain,
        task_type=request.task_type,
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
    session: AsyncSession = Depends(get_db_session),
) -> list[ExperienceSearchResult]:
    """推荐经验."""
    chain = PriorityChain(session, min_results=limit, max_results=limit * 2)

    chain_results = await chain.search(
        query=query,
        domain=domain,
        task_type=task_type,
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
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """查看优先级链执行详情."""
    chain = PriorityChain(session, min_results=limit, max_results=limit)

    chain_results = await chain.search(
        query=query,
        domain=domain,
        task_type=task_type,
    )

    return {
        "query": query,
        "domain": domain,
        "task_type": task_type,
        "chain_results": [r.to_dict() for r in chain_results],
        "best_results": [r.to_dict() for r in chain.get_best_results(chain_results, limit=limit)],
    }
