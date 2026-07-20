"""Experience CRUD API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session, get_optional_user
from app.models.user import User
from app.schemas.experience import (
    ExperienceCreate,
    ExperienceListResponse,
    ExperienceResponse,
    ExperienceUpdate,
    RelationCreate,
    RelationResponse,
)
from app.services.experience.graph import ExperienceGraph
from app.services.experience.repository import ExperienceRepository
from app.services.retrieval.embedder import get_embedder

import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Experience CRUD ──


@router.post(
    "",
    response_model=ExperienceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建经验",
    description="创建一个新的 Experience 对象并存入经验图谱。",
)
async def create_experience(
    data: ExperienceCreate,
    current_user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(get_db_session),
) -> ExperienceResponse:
    # 关联当前用户（如果已认证）
    if current_user and not data.user_id:
        data.user_id = current_user.id

    repo = ExperienceRepository(session)
    experience = await repo.create(data)

    # API 创建的经验视为已评估（Agent 已执行并反思）
    experience.evaluation_status = "evaluated"
    await session.commit()

    # 生成 embedding 以支持向量检索
    try:
        embedder = get_embedder()
        embed_text = f"{data.intent} {data.context.domain} {data.context.task_type}"
        embedding = await embedder.embed_async(embed_text)
        await repo.update_embedding(experience.id, embedding)
    except Exception:
        pass  # embedding 失败不阻塞经验创建

    return ExperienceResponse.model_validate(experience)


@router.get(
    "",
    response_model=ExperienceListResponse,
    summary="列出经验",
    description="分页列出经验，支持按领域、任务类型、置信度、可见性过滤。仅返回当前用户有权查看的经验。",
)
async def list_experiences(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    domain: str | None = Query(None, description="领域过滤"),
    task_type: str | None = Query(None, description="任务类型过滤"),
    min_confidence: float | None = Query(None, ge=0.0, le=1.0, description="最低置信度"),
    evaluation_status: str | None = Query(None, description="评估状态过滤"),
    visibility: str | None = Query(None, pattern="^(private|community|public)$", description="可见性过滤"),
    current_user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(get_db_session),
) -> ExperienceListResponse:
    current_user_id = str(current_user.id) if current_user else None
    repo = ExperienceRepository(session)
    experiences, total = await repo.list(
        page=page,
        page_size=page_size,
        domain=domain,
        task_type=task_type,
        min_confidence=min_confidence,
        evaluation_status=evaluation_status,
        visibility=visibility,
        current_user_id=current_user_id,
    )
    return ExperienceListResponse(
        items=[ExperienceResponse.model_validate(exp) for exp in experiences],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{experience_id}",
    response_model=ExperienceResponse,
    summary="获取经验",
    description="根据 ID 获取单个 Experience 对象。仅返回当前用户有权查看的经验。",
)
async def get_experience(
    experience_id: UUID,
    current_user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(get_db_session),
) -> ExperienceResponse:
    current_user_id = str(current_user.id) if current_user else None
    repo = ExperienceRepository(session)
    experience = await repo.get_by_id(experience_id, current_user_id=current_user_id)
    if experience is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experience {experience_id} not found",
        )
    return ExperienceResponse.model_validate(experience)


@router.put(
    "/{experience_id}",
    response_model=ExperienceResponse,
    summary="更新经验",
    description="更新一个 Experience 对象。",
)
async def update_experience(
    experience_id: UUID,
    data: ExperienceUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> ExperienceResponse:
    repo = ExperienceRepository(session)
    experience = await repo.update(experience_id, data)
    if experience is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experience {experience_id} not found",
        )
    return ExperienceResponse.model_validate(experience)


@router.delete(
    "/{experience_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除经验",
    description="删除一个 Experience 对象及其所有关系。",
)
async def delete_experience(
    experience_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    repo = ExperienceRepository(session)
    deleted = await repo.delete(experience_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experience {experience_id} not found",
        )


# ── Experience Relations (Graph) ──


@router.post(
    "/{experience_id}/relations",
    response_model=RelationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="添加经验关系",
    description="在两个经验之间添加图谱关系边（reuse/citation/fork/improvement/dependency）。",
)
async def add_relation(
    experience_id: UUID,
    data: RelationCreate,
    session: AsyncSession = Depends(get_db_session),
) -> RelationResponse:
    logger.info(
        "[API:ADD_RELATION] 收到请求: source=%s, target=%s, type=%s, weight=%.2f",
        experience_id, data.target_id, data.relation_type, data.weight,
    )

    repo = ExperienceRepository(session)
    # 验证源经验存在（使用 unfiltered 以支持所有可见性）
    source = await repo._get_by_id_unfiltered(experience_id)
    if source is None:
        logger.warning("[API:ADD_RELATION] 源经验不存在: experience_id=%s", experience_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source experience {experience_id} not found",
        )

    # 验证目标经验存在
    target = await repo._get_by_id_unfiltered(data.target_id)
    if target is None:
        logger.warning("[API:ADD_RELATION] 目标经验不存在: target_id=%s", data.target_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target experience {data.target_id} not found",
        )

    logger.info(
        "[API:ADD_RELATION] 双方经验已验证: source='%s', target='%s'",
        source.intent[:60], target.intent[:60],
    )

    graph = ExperienceGraph(session)
    relation = await graph.add_relation(experience_id, data)

    logger.info(
        "[API:ADD_RELATION] 关系边已创建: relation_id=%s, source=%s -> target=%s, type=%s",
        relation.id, experience_id, data.target_id, data.relation_type,
    )

    return RelationResponse.model_validate(relation)


@router.get(
    "/{experience_id}/relations",
    response_model=list[RelationResponse],
    summary="查询经验关系",
    description="查询某个经验的所有图谱关系。",
)
async def get_relations(
    experience_id: UUID,
    direction: str = Query("both", pattern="^(outgoing|incoming|both)$"),
    relation_type: str | None = Query(None, pattern="^(reuse|citation|fork|improvement|dependency)$"),
    session: AsyncSession = Depends(get_db_session),
) -> list[RelationResponse]:
    graph = ExperienceGraph(session)
    relations = await graph.get_relations(
        experience_id, direction=direction, relation_type=relation_type
    )
    return [RelationResponse.model_validate(rel) for rel in relations]
