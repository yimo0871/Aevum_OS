"""Evaluation API routes - 评估接口."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.models.experience import Experience
from app.services.evaluation.experience_evaluator import ExperienceEvaluator
from app.services.evaluation.metrics import SystemMetricsCalculator
from app.services.evaluation.task_evaluator import TaskEvaluator
from app.services.experience.repository import ExperienceRepository

router = APIRouter()


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
    calculator = SystemMetricsCalculator(session)
    metrics = await calculator.compute_all()
    return {
        "metrics": metrics,
        "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }


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

    return {
        "system_metrics": metrics,
        "experience_stats": {
            "total": total_experiences,
            "evaluated": evaluated_count,
            "pending": pending_count,
            "avg_confidence": round(float(avg_confidence), 4),
        },
    }
