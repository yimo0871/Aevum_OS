"""治理层 API 路由 - 经验版本控制与信任评分."""
from __future__ import annotations

import logging
from types import SimpleNamespace
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_current_user, get_db_session
from app.models.community import user_community
from app.models.experience import Experience, ExperienceRelation
from app.models.user import User
from app.services.governance.audit import AuditLogger
from app.services.governance.compression import CompressionManager
from app.services.governance.trust import TrustScorer
from app.services.governance.versioning import VersionManager

logger = logging.getLogger(__name__)
router = APIRouter()


async def _assert_experience_accessible(
    experience: Experience, current_user: User, session: AsyncSession
) -> None:
    """校验当前用户是否有权访问该经验（fork/improve/cite 前的权限检查）.

    规则:
    - 自己的经验: 始终可访问
    - public 经验: 任何人可访问
    - community 经验: 同社区成员可访问
    - private 经验: 仅创建者可访问
    """
    if experience.user_id == current_user.id:
        return
    if experience.visibility == "public":
        return
    if experience.visibility == "community" and experience.community_id is not None:
        result = await session.execute(
            select(user_community.c.community_id).where(
                user_community.c.user_id == current_user.id,
                user_community.c.community_id == experience.community_id,
            )
        )
        if result.fetchone() is not None:
            return
        raise HTTPException(status.HTTP_403_FORBIDDEN, "无权访问此社区经验")
    raise HTTPException(status.HTTP_403_FORBIDDEN, "无权访问此私有经验")


class ImproveRequest(BaseModel):
    """改进经验请求."""

    improvements: dict = Field(default_factory=dict, description="改进内容（可含 context/outcome/reflection/intent/confidence_score）")


class CiteRequest(BaseModel):
    """引用经验请求."""

    citing_experience_id: UUID = Field(..., description="引用方经验 ID")


class ForgetRequest(BaseModel):
    """遗忘经验请求."""

    reason: str = Field(..., description="遗忘原因 (expired/low_quality/redundant/zero_reuse)")


class CleanupRequest(BaseModel):
    """自动清理请求."""

    threshold_days: int = Field(default=90, description="年龄阈值（天）")
    min_trust: float = Field(default=0.1, description="信任评分上限")
    min_reuse: int = Field(default=0, description="复用次数上限")


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
    logger.info(
        "[API:FORK] 收到请求: experience_id=%s, user=%s",
        experience_id, current_user.username,
    )

    source = await session.get(Experience, experience_id)
    if source is None:
        logger.warning("[API:FORK] 源经验不存在: experience_id=%s", experience_id)
        raise HTTPException(status.HTTP_404_NOT_FOUND, "源经验不存在")

    await _assert_experience_accessible(source, current_user, session)

    manager = VersionManager()
    new_experience = await manager.fork(experience_id, current_user.id, session)
    if new_experience is None:
        logger.error("[API:FORK] VersionManager.fork 返回 None: experience_id=%s", experience_id)
        raise HTTPException(status.HTTP_404_NOT_FOUND, "源经验不存在")

    logger.info(
        "[API:FORK] 分叉成功: source=%s -> forked=%s, user=%s",
        source.id, new_experience.id, current_user.username,
    )

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
    logger.info(
        "[API:IMPROVE] 收到请求: experience_id=%s, user=%s, improvements_keys=%s",
        experience_id, current_user.username,
        list(data.improvements.keys()) if data.improvements else [],
    )

    source = await session.get(Experience, experience_id)
    if source is None:
        logger.warning("[API:IMPROVE] 源经验不存在: experience_id=%s", experience_id)
        raise HTTPException(status.HTTP_404_NOT_FOUND, "源经验不存在")

    await _assert_experience_accessible(source, current_user, session)

    manager = VersionManager()
    new_experience = await manager.improve(
        experience_id, data.improvements, current_user.id, session
    )
    if new_experience is None:
        logger.error("[API:IMPROVE] VersionManager.improve 返回 None: experience_id=%s", experience_id)
        raise HTTPException(status.HTTP_404_NOT_FOUND, "源经验不存在")

    logger.info(
        "[API:IMPROVE] 改进成功: source=%s -> improved=%s, user=%s",
        source.id, new_experience.id, current_user.username,
    )

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
    logger.info(
        "[API:CITE] 收到请求: target_experience_id=%s (被引用), citing_experience_id=%s (引用方), user=%s",
        experience_id, data.citing_experience_id, current_user.username,
    )

    # 验证被引用的经验存在
    target = await session.get(Experience, experience_id)
    if target is None:
        logger.warning("[API:CITE] 被引用的经验不存在: experience_id=%s", experience_id)
        raise HTTPException(status.HTTP_404_NOT_FOUND, "被引用的经验不存在")

    # 验证引用方经验存在
    citing = await session.get(Experience, data.citing_experience_id)
    if citing is None:
        logger.warning("[API:CITE] 引用方经验不存在: citing_experience_id=%s", data.citing_experience_id)
        raise HTTPException(status.HTTP_404_NOT_FOUND, "引用方经验不存在")

    # 权限校验：被引用经验必须对当前用户可见，引用方经验必须属于当前用户
    await _assert_experience_accessible(target, current_user, session)
    await _assert_experience_accessible(citing, current_user, session)

    logger.info(
        "[API:CITE] 双方经验已验证: target='%s', citing='%s'",
        target.intent[:60], citing.intent[:60],
    )

    manager = VersionManager()
    relation = await manager.cite(experience_id, data.citing_experience_id, session)

    logger.info(
        "[API:CITE] 引用成功: relation_id=%s, source=%s -> target=%s, user=%s",
        relation.id, data.citing_experience_id, experience_id, current_user.username,
    )

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


# ── 经验压缩与遗忘（M3-S1）──


@router.post(
    "/experiences/{experience_id}/compress",
    summary="压缩经验",
    description="压缩低质/冗余经验：设置 compressed 标记、存储摘要、降低信任权重。",
)
async def compress_experience(
    experience_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """压缩一条经验."""
    manager = CompressionManager()
    experience = await manager.compress_experience(experience_id, session)

    if experience is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "经验不存在")

    # ── 记录审计日志 ──
    audit_logger = AuditLogger()
    await audit_logger.log(
        action="compress",
        entity_type="experience",
        entity_id=experience_id,
        session=session,
        actor_id=current_user.id,
        actor_type="user",
        details={"compression_summary": experience.compression_summary},
    )

    return {
        "experience_id": str(experience.id),
        "compressed": experience.compressed,
        "compression_summary": experience.compression_summary,
        "confidence_score": experience.confidence_score,
    }


@router.post(
    "/experiences/{experience_id}/forget",
    summary="遗忘经验",
    description="软删除经验：设置 status=forgotten 并记录原因。",
)
async def forget_experience(
    experience_id: UUID,
    data: ForgetRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """遗忘一条经验."""
    manager = CompressionManager()
    try:
        experience = await manager.forget_experience(experience_id, data.reason, session)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

    if experience is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "经验不存在")

    # ── 记录审计日志 ──
    audit_logger = AuditLogger()
    await audit_logger.log(
        action="forget",
        entity_type="experience",
        entity_id=experience_id,
        session=session,
        actor_id=current_user.id,
        actor_type="user",
        details={"reason": data.reason},
    )

    return {
        "experience_id": str(experience.id),
        "status": experience.status,
        "reason": data.reason,
    }


@router.post(
    "/cleanup",
    summary="自动清理经验",
    description="管理员触发自动清理：遗忘过期的低信任、低复用经验。",
)
async def auto_cleanup(
    data: CleanupRequest | None = None,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """自动清理过期经验."""
    params = data or CleanupRequest()
    manager = CompressionManager()
    forgotten = await manager.auto_cleanup(
        session,
        threshold_days=params.threshold_days,
        min_trust=params.min_trust,
        min_reuse=params.min_reuse,
    )

    # ── 批量记录审计日志 ──
    audit_logger = AuditLogger()
    for exp in forgotten:
        await audit_logger.log(
            action="forget",
            entity_type="experience",
            entity_id=exp.id,
            session=session,
            actor_id=current_user.id,
            actor_type="user",
            details={"reason": "auto_cleanup"},
        )

    return {
        "forgotten_count": len(forgotten),
        "forgotten_ids": [str(exp.id) for exp in forgotten],
    }


# ── 审计日志检索（M3-S2）──


@router.get(
    "/audit/{entity_type}/{entity_id}",
    summary="获取审计轨迹",
    description="检索指定实体的审计日志轨迹。",
)
async def get_audit_trail(
    entity_type: str,
    entity_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """获取实体的审计轨迹."""
    audit_logger = AuditLogger()
    logs = await audit_logger.get_logs(entity_type, entity_id, session)

    return {
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "logs": [log.to_dict() for log in logs],
        "total": len(logs),
    }
