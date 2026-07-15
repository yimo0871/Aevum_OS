"""治理层 API 路由 - 经验版本控制与信任评分."""
from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session
from app.models.experience import Experience, ExperienceRelation
from app.models.user import User
from app.services.governance.trust import TrustScorer
from app.services.governance.versioning import VersionManager

router = APIRouter()


class ImproveRequest(BaseModel):
    """改进经验请求."""

    improvements: dict = Field(default_factory=dict, description="改进内容（可含 context/outcome/reflection/intent/confidence_score）")


class CiteRequest(BaseModel):
    """引用经验请求."""

    citing_experience_id: UUID = Field(..., description="引用方经验 ID")


@router.post(
    "/experiences/{experience_id}/fork",
    summary="分叉经验",
    description="基于源经验创建一个副本，并在 experience_relations 表中建立 fork 关系。",
)
async def fork_experience(
    experience_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    source = await session.get(Experience, experience_id)
    if source is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "源经验不存在")

    manager = VersionManager()
    new_experience = await manager.fork(experience_id, current_user.id, session)
    if new_experience is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "源经验不存在")

    return {
        "forked_experience": new_experience.to_dict(),
        "source_id": str(source.id),
    }


@router.post(
    "/experiences/{experience_id}/improve",
    summary="改进经验",
    description="基于源经验创建改进版本，合并改进内容并建立 improvement 关系。",
)
async def improve_experience(
    experience_id: UUID,
    data: ImproveRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    source = await session.get(Experience, experience_id)
    if source is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "源经验不存在")

    manager = VersionManager()
    new_experience = await manager.improve(
        experience_id, data.improvements, current_user.id, session
    )
    if new_experience is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "源经验不存在")

    return {
        "improved_experience": new_experience.to_dict(),
        "source_id": str(source.id),
    }


@router.post(
    "/experiences/{experience_id}/cite",
    summary="引用经验",
    description="在当前经验和指定经验之间建立 citation 引用关系。",
)
async def cite_experience(
    experience_id: UUID,
    data: CiteRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    # 验证被引用的经验存在
    target = await session.get(Experience, experience_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "被引用的经验不存在")

    # 验证引用方经验存在
    citing = await session.get(Experience, data.citing_experience_id)
    if citing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "引用方经验不存在")

    manager = VersionManager()
    relation = await manager.cite(experience_id, data.citing_experience_id, session)

    return {
        "id": str(relation.id),
        "source_id": str(relation.source_id),
        "target_id": str(relation.target_id),
        "relation_type": relation.relation_type,
        "weight": relation.weight,
        "created_at": relation.created_at.isoformat() if relation.created_at else None,
    }


@router.get(
    "/experiences/{experience_id}/trust",
    summary="获取信任评分",
    description="基于使用次数、成功率、引用数、复用率、稳定性计算经验信任评分。",
)
async def get_trust_score(
    experience_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    experience = await session.get(Experience, experience_id)
    if experience is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "经验不存在")

    # 从 DB 查询实际的引用数和复用数
    citation_count_result = await session.execute(
        select(func.count(ExperienceRelation.id)).where(
            ExperienceRelation.target_id == experience_id,
            ExperienceRelation.relation_type == "citation",
        )
    )
    citation_count = citation_count_result.scalar() or 0

    reuse_count_result = await session.execute(
        select(func.count(ExperienceRelation.id)).where(
            ExperienceRelation.target_id == experience_id,
            ExperienceRelation.relation_type == "reuse",
        )
    )
    reuse_count = reuse_count_result.scalar() or 0

    # 构建代理对象，将实际计数注入 provenance（不修改数据库中的经验对象）
    provenance = dict(experience.provenance) if experience.provenance else {}
    provenance["citation_count"] = citation_count
    provenance["reuse_count"] = reuse_count

    exp_proxy = SimpleNamespace(
        provenance=provenance,
        outcome=experience.outcome,
        confidence_score=experience.confidence_score,
    )

    scorer = TrustScorer()
    trust_score = scorer.compute(exp_proxy)

    # 收集指标用于响应
    usage_count = provenance.get("usage_count", 0)
    outcome = experience.outcome if experience.outcome else {}
    success_rate = 1.0 if outcome.get("success") else 0.0

    return {
        "experience_id": str(experience_id),
        "trust_score": trust_score,
        "metrics": {
            "usage_count": usage_count,
            "success_rate": success_rate,
            "citation_count": citation_count,
            "reuse_count": reuse_count,
            "stability": experience.confidence_score or 0.0,
        },
    }


@router.get(
    "/experiences/{experience_id}/lineage",
    summary="获取经验谱系",
    description="获取经验的 fork/improvement 谱系链，包括祖先（来源）和后代（分叉/改进）。",
)
async def get_experience_lineage(
    experience_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    experience = await session.get(Experience, experience_id)
    if experience is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "经验不存在")

    # 祖先：当前经验作为 target 的 fork/improvement 关系（从哪些经验分叉/改进而来）
    ancestors_result = await session.execute(
        select(ExperienceRelation).where(
            ExperienceRelation.target_id == experience_id,
            ExperienceRelation.relation_type.in_(["fork", "improvement"]),
        )
    )
    ancestors = ancestors_result.scalars().all()

    # 后代：当前经验作为 source 的 fork/improvement 关系（哪些经验从当前经验分叉/改进）
    descendants_result = await session.execute(
        select(ExperienceRelation).where(
            ExperienceRelation.source_id == experience_id,
            ExperienceRelation.relation_type.in_(["fork", "improvement"]),
        )
    )
    descendants = descendants_result.scalars().all()

    # 获取关联经验详情
    related_ids = [rel.source_id for rel in ancestors] + [
        rel.target_id for rel in descendants
    ]
    related_experiences: dict[str, dict] = {}
    if related_ids:
        related_result = await session.execute(
            select(Experience).where(Experience.id.in_(related_ids))
        )
        for exp in related_result.scalars().all():
            related_experiences[str(exp.id)] = exp.to_dict()

    return {
        "experience_id": str(experience_id),
        "ancestors": [
            {
                "relation_id": str(rel.id),
                "relation_type": rel.relation_type,
                "source_experience_id": str(rel.source_id),
                "experience": related_experiences.get(str(rel.source_id)),
            }
            for rel in ancestors
        ],
        "descendants": [
            {
                "relation_id": str(rel.id),
                "relation_type": rel.relation_type,
                "target_experience_id": str(rel.target_id),
                "experience": related_experiences.get(str(rel.target_id)),
            }
            for rel in descendants
        ],
    }
