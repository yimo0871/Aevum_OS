"""Human Expression API routes - 人类表达层.

人机分离原则:
- 写入（POST/PUT/DELETE）仅限人类 JWT
- 读取（GET/observe）可供 Agent 观察使用（只读）
- embedding 由后端自动生成
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session, get_optional_user
from app.models.experience import Experience
from app.models.human_expression import HumanExpression
from app.models.user import User
from app.models.world_bridge import WorldBridge
from app.schemas.human_expression import (
    HumanExpressionCreate,
    HumanExpressionListResponse,
    HumanExpressionResponse,
    HumanExpressionUpdate,
    ObserveRequest,
)
from app.schemas.world_bridge import BridgeCreate, BridgeListResponse, BridgeResponse
from app.services.retrieval.embedder import get_embedder

router = APIRouter()


def _serialize(exp: HumanExpression) -> dict:
    """序列化 HumanExpression（不返回 embedding）."""
    return {
        "id": str(exp.id),
        "user_id": str(exp.user_id) if exp.user_id else None,
        "type": exp.type,
        "content": exp.content,
        "metadata": exp.metadata_ if exp.metadata_ else {},
        "created_at": exp.created_at.isoformat() if exp.created_at else None,
        "updated_at": exp.updated_at.isoformat() if exp.updated_at else None,
    }


@router.post(
    "/expressions",
    response_model=HumanExpressionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="存储人类表达（仅人类 JWT）",
)
async def create_expression(
    data: HumanExpressionCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> HumanExpressionResponse:
    """存储人类表达。后端自动生成 embedding，不强制结构化内容。"""
    # 生成 embedding（内容序列化为文本）
    content_text = str(data.content)
    try:
        embedder = get_embedder()
        if hasattr(embedder, "embed_async"):
            embedding = await embedder.embed_async(content_text)
        else:
            embedding = await embedder.embed(content_text)
    except Exception:
        embedding = None

    expression = HumanExpression(
        user_id=current_user.id,
        type=data.type,
        content=data.content,
        metadata_=data.metadata,
        embedding=embedding,
    )
    session.add(expression)
    await session.flush()
    await session.refresh(expression)

    return HumanExpressionResponse(
        id=expression.id,
        user_id=expression.user_id,
        type=expression.type,
        content=expression.content,
        metadata=expression.metadata_ or {},
        created_at=expression.created_at,
        updated_at=expression.updated_at,
    )


@router.get(
    "/expressions",
    response_model=HumanExpressionListResponse,
    summary="人类表达时间线（分页，只读）",
)
async def list_expressions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type_filter: str | None = Query(None, alias="type", description="按类型过滤"),
    current_user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(get_db_session),
) -> HumanExpressionListResponse:
    """人类表达时间线，支持按类型过滤。可供 Agent 观察使用。"""
    query = select(HumanExpression)
    if type_filter:
        query = query.where(HumanExpression.type == type_filter)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    offset = (page - 1) * page_size
    query = query.order_by(HumanExpression.created_at.desc()).offset(offset).limit(page_size)
    result = await session.execute(query)
    expressions = result.scalars().all()

    return HumanExpressionListResponse(
        items=[
            HumanExpressionResponse(
                id=e.id,
                user_id=e.user_id,
                type=e.type,
                content=e.content,
                metadata=e.metadata_ or {},
                created_at=e.created_at,
                updated_at=e.updated_at,
            )
            for e in expressions
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/expressions/{expression_id}",
    response_model=HumanExpressionResponse,
    summary="获取人类表达详情",
)
async def get_expression(
    expression_id: UUID,
    current_user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(get_db_session),
) -> HumanExpressionResponse:
    result = await session.execute(
        select(HumanExpression).where(HumanExpression.id == expression_id)
    )
    expression = result.scalar_one_or_none()
    if expression is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="表达不存在")

    return HumanExpressionResponse(
        id=expression.id,
        user_id=expression.user_id,
        type=expression.type,
        content=expression.content,
        metadata=expression.metadata_ or {},
        created_at=expression.created_at,
        updated_at=expression.updated_at,
    )


@router.put(
    "/expressions/{expression_id}",
    response_model=HumanExpressionResponse,
    summary="修改人类表达（仅作者）",
)
async def update_expression(
    expression_id: UUID,
    data: HumanExpressionUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> HumanExpressionResponse:
    result = await session.execute(
        select(HumanExpression).where(HumanExpression.id == expression_id)
    )
    expression = result.scalar_one_or_none()
    if expression is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="表达不存在")

    if expression.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只能修改自己的表达")

    if data.content is not None:
        expression.content = data.content
        # 重新生成 embedding
        try:
            embedder = get_embedder()
            if hasattr(embedder, "embed_async"):
                expression.embedding = await embedder.embed_async(str(data.content))
            else:
                expression.embedding = await embedder.embed(str(data.content))
        except Exception:
            pass

    if data.metadata is not None:
        expression.metadata_ = data.metadata

    await session.flush()
    await session.refresh(expression)

    return HumanExpressionResponse(
        id=expression.id,
        user_id=expression.user_id,
        type=expression.type,
        content=expression.content,
        metadata=expression.metadata_ or {},
        created_at=expression.created_at,
        updated_at=expression.updated_at,
    )


@router.delete(
    "/expressions/{expression_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除人类表达（仅作者）",
)
async def delete_expression(
    expression_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    result = await session.execute(
        select(HumanExpression).where(HumanExpression.id == expression_id)
    )
    expression = result.scalar_one_or_none()
    if expression is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="表达不存在")

    if expression.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只能删除自己的表达")

    await session.delete(expression)
    await session.flush()


@router.post(
    "/observe",
    summary="语义搜索人类表达（Agent 可调用，只读）",
)
async def observe_expressions(
    data: ObserveRequest,
    current_user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    """基于 embedding 的语义搜索。返回匹配的人类表达（不含 embedding）。

    供 Agent 执行任务前观察相关人类表达使用。
    """
    # 生成查询向量
    try:
        embedder = get_embedder()
        if hasattr(embedder, "embed_async"):
            query_vector = await embedder.embed_async(data.query)
        else:
            query_vector = await embedder.embed(data.query)
    except Exception:
        return []

    vector_str = f"[{','.join(str(v) for v in query_vector)}]"

    sql = text("""
        SELECT id, user_id, type, content, metadata, created_at,
               1 - (embedding <=> :vector) as similarity
        FROM human_expressions
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> :vector
        LIMIT :limit
    """)

    result = await session.execute(sql, {"vector": vector_str, "limit": data.limit})
    rows = result.fetchall()

    return [
        {
            "id": str(row[0]),
            "user_id": str(row[1]) if row[1] else None,
            "type": row[2],
            "content": row[3],
            "metadata": row[4] or {},
            "created_at": row[5].isoformat() if row[5] else None,
            "similarity": row[6] if row[6] is not None else 0.0,
        }
        for row in rows
    ]


# ── WorldBridge 桥接管理 ──


@router.post(
    "/bridge",
    response_model=BridgeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建世界桥接",
    description="在 HumanExpression 和 Experience 之间建立语义引用桥接。",
)
async def create_bridge(
    data: BridgeCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> BridgeResponse:
    """创建桥接。验证两端存在性，防止重复桥接。"""
    # 验证人类表达存在
    expr = await session.get(HumanExpression, data.human_expression_id)
    if expr is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="人类表达不存在")

    # 验证 Agent 经验存在
    exp = await session.get(Experience, data.experience_id)
    if exp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent 经验不存在")

    # 检查重复桥接
    existing = await session.execute(
        select(WorldBridge).where(
            WorldBridge.bridge_type == data.bridge_type,
            WorldBridge.human_expression_id == data.human_expression_id,
            WorldBridge.experience_id == data.experience_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该桥接已存在",
        )

    bridge = WorldBridge(
        bridge_type=data.bridge_type,
        human_expression_id=data.human_expression_id,
        experience_id=data.experience_id,
        metadata_=data.metadata,
        created_by=str(current_user.id),
    )
    session.add(bridge)
    await session.flush()
    await session.refresh(bridge)

    return BridgeResponse(
        id=bridge.id,
        bridge_type=bridge.bridge_type,
        human_expression_id=bridge.human_expression_id,
        experience_id=bridge.experience_id,
        metadata=bridge.metadata_ or {},
        created_by=bridge.created_by,
        created_at=bridge.created_at,
    )


@router.get(
    "/bridge",
    response_model=BridgeListResponse,
    summary="查询世界桥接",
    description="按人类表达 ID 或 Agent 经验 ID 过滤查询桥接关系。",
)
async def list_bridges(
    human_expression_id: UUID | None = Query(None, description="按人类表达过滤"),
    experience_id: UUID | None = Query(None, description="按 Agent 经验过滤"),
    bridge_type: str | None = Query(None, pattern="^(inspiration|observation|recommendation|reflection)$", description="按桥接类型过滤"),
    current_user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(get_db_session),
) -> BridgeListResponse:
    """查询桥接关系，支持按表达/经验/类型过滤。"""
    query = select(WorldBridge)

    if human_expression_id:
        query = query.where(WorldBridge.human_expression_id == human_expression_id)
    if experience_id:
        query = query.where(WorldBridge.experience_id == experience_id)
    if bridge_type:
        query = query.where(WorldBridge.bridge_type == bridge_type)

    query = query.order_by(WorldBridge.created_at.desc())
    result = await session.execute(query)
    bridges = result.scalars().all()

    return BridgeListResponse(
        items=[
            BridgeResponse(
                id=b.id,
                bridge_type=b.bridge_type,
                human_expression_id=b.human_expression_id,
                experience_id=b.experience_id,
                metadata=b.metadata_ or {},
                created_by=b.created_by,
                created_at=b.created_at,
            )
            for b in bridges
        ],
        total=len(bridges),
    )
