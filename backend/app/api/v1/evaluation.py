"""Evaluation API routes - 评估接口."""

import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.models.experience import Experience
from app.services.evaluation.experience_evaluator import ExperienceEvaluator
from app.services.evaluation.human_review import HumanReviewService
from app.services.evaluation.metrics import SystemMetricsCalculator
from app.services.evaluation.task_evaluator import TaskEvaluator
from app.services.experience.repository import ExperienceRepository

router = APIRouter()

# 简单内存缓存（5秒TTL）
_cache: dict[str, tuple[float, any]] = {}
_CACHE_TTL = 5.0


def _get_cache(key: str):
    if key in _cache:
        ts, val = _cache[key]
        if time.time() - ts < _CACHE_TTL:
            return val
    return None


def _set_cache(key: str, val):
    _cache[key] = (time.time(), val)


@router.post(
    "/experiences/{experience_id}",
    summary="评估经验",
    description="对指定经验进行评估，更新其置信度和评估状态。",
)
async def evaluate_experience(
    experience_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """评估经验对象."""
    repo = ExperienceRepository(session)
    experience = await repo.get_by_id(experience_id)

    if experience is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experience {experience_id} not found",
        )

    # ── 评估经验 ──
    evaluator = ExperienceEvaluator()
    result = evaluator.evaluate(experience)

    # ── 更新经验置信度和评估状态 ──
    from app.schemas.experience import ExperienceUpdate

    await repo.update(experience_id, ExperienceUpdate(
        confidence_score=result.confidence_score,
        evaluation_status="evaluated",
    ))
    await session.commit()

    # ── 保存评估记录 ──
    evaluation_model = evaluator.to_evaluation_model(result)
    session.add(evaluation_model)
    await session.commit()

    return result.to_dict()


@router.get(
    "/metrics",
    summary="获取系统指标",
    description="获取七个系统级追踪指标的当前值。",
)
async def get_system_metrics(
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """获取系统级指标."""
    cached = _get_cache("metrics")
    if cached is not None:
        return cached

    calculator = SystemMetricsCalculator(session)
    metrics = await calculator.compute_all()
    result = {
        "metrics": metrics,
        "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }
    _set_cache("metrics", result)
    return result


@router.get(
    "/metrics/{metric_name}/history",
    summary="获取指标历史",
    description="获取指定指标的历史数据。",
)
async def get_metric_history(
    metric_name: str,
    hours: int = 24,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """获取指标历史数据."""
    calculator = SystemMetricsCalculator(session)
    history = await calculator.get_history(metric_name, hours=hours)
    return {
        "metric_name": metric_name,
        "hours": hours,
        "data_points": len(history),
        "history": history,
    }


@router.get(
    "/dashboard",
    summary="Dashboard 聚合数据",
    description="获取 Dashboard 页面所需的聚合数据：系统指标 + 经验统计。",
)
async def get_dashboard_data(
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """获取 Dashboard 聚合数据."""
    cached = _get_cache("dashboard")
    if cached is not None:
        return cached

    from sqlalchemy import func

    calculator = SystemMetricsCalculator(session)
    metrics = await calculator.compute_all()

    # ── 经验统计 ──
    total_result = await session.execute(select(func.count(Experience.id)))
    total_experiences = total_result.scalar() or 0

    evaluated_result = await session.execute(
        select(func.count(Experience.id))
        .where(Experience.evaluation_status == "evaluated")
    )
    evaluated_count = evaluated_result.scalar() or 0

    pending_result = await session.execute(
        select(func.count(Experience.id))
        .where(Experience.evaluation_status == "pending")
    )
    pending_count = pending_result.scalar() or 0

    avg_confidence_result = await session.execute(
        select(func.avg(Experience.confidence_score))
    )
    avg_confidence = avg_confidence_result.scalar() or 0.0

    result = {
        "system_metrics": metrics,
        "experience_stats": {
            "total": total_experiences,
            "evaluated": evaluated_count,
            "pending": pending_count,
            "avg_confidence": round(float(avg_confidence), 4),
        },
    }
    _set_cache("dashboard", result)
    return result


# ── 人机协同评估（M3-S4）──


class HumanReviewRequest(BaseModel):
    """人类专家评审请求."""

    reviewer_id: UUID = Field(..., description="评审者 ID")
    rating: int = Field(..., ge=1, le=5, description="评分 (1-5)")
    notes: str | None = Field(default=None, description="评审备注")
    recommend_archive: bool = Field(default=False, description="是否建议归档")


@router.post(
    "/experiences/{experience_id}/human-review",
    summary="人类专家评审",
    description="提交人类专家对经验的评审，并据此调整信任评分。",
)
async def create_human_review(
    experience_id: UUID,
    data: HumanReviewRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """创建人类专家评审."""
    service = HumanReviewService()
    try:
        review = await service.create_review(
            experience_id=experience_id,
            reviewer_id=data.reviewer_id,
            rating=data.rating,
            session=session,
            notes=data.notes,
            recommend_archive=data.recommend_archive,
        )
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

    return review.to_dict()


@router.get(
    "/experiences/{experience_id}/reviews",
    summary="获取人类评审列表",
    description="获取指定经验的所有人类专家评审记录。",
)
async def get_human_reviews(
    experience_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """获取经验的人类评审记录."""
    service = HumanReviewService()
    reviews = await service.get_reviews(experience_id, session)

    return {
        "experience_id": str(experience_id),
        "reviews": [review.to_dict() for review in reviews],
        "total": len(reviews),
    }


@router.get(
    "/pending-reviews",
    summary="获取待评审经验",
    description="获取高使用量但低置信度、尚未有人类评审的经验列表。",
)
async def get_pending_reviews(
    min_usage: int = 5,
    max_confidence: float = 0.5,
    limit: int = 50,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """获取待评审经验列表."""
    service = HumanReviewService()
    experiences = await service.get_pending_reviews(
        session,
        min_usage=min_usage,
        max_confidence=max_confidence,
        limit=limit,
    )

    return {
        "pending": [exp.to_dict() for exp in experiences],
        "total": len(experiences),
    }
