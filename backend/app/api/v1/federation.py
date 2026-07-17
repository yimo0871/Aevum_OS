"""Federation API routes - 联邦网络管理."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_current_user, get_db_session
from app.models.user import User
from app.services.federation.federation_service import FederationService
from app.services.retrieval.matcher import ExperienceMatcher

logger = logging.getLogger(__name__)
router = APIRouter()


# ── 联邦节点单例（进程内共享）──

_federation_node: FederationService | None = None


def get_federation_service() -> FederationService:
    """获取联邦服务单例."""
    global _federation_node
    if _federation_node is None:
        _federation_node = FederationService(
            node_url="http://localhost:8000",
            node_id="local",
        )
    return _federation_node


# ── 请求模型 ──


class PeerRegisterRequest(BaseModel):
    """注册对等节点请求."""

    peer_url: str = Field(..., description="对等节点 URL")
    peer_id: str = Field(..., description="对等节点唯一标识")


class SyncRequest(BaseModel):
    """同步经验请求."""

    experience_data: dict | None = Field(None, description="经验数据（可选，不传则仅推送 ID）")


# ── 路由 ──


@router.post(
    "/peers",
    status_code=status.HTTP_201_CREATED,
    summary="注册对等节点",
    description="注册一个远程 Aevum 节点为联邦对等节点（管理员权限）。",
)
async def register_peer(
    data: PeerRegisterRequest,
    current_user: User = Depends(get_current_admin),
) -> dict:
    service = get_federation_service()
    peer_info = service.register_peer(data.peer_url, data.peer_id)
    return {"peer": peer_info, "total_peers": len(service.list_peers())}


@router.get(
    "/peers",
    summary="列出对等节点",
    description="列出所有已注册的联邦对等节点。",
)
async def list_peers(
    current_user: User = Depends(get_current_user),
) -> dict:
    service = get_federation_service()
    peers = service.list_peers()
    return {"peers": peers, "total": len(peers)}


@router.post(
    "/sync/{experience_id}",
    summary="推送经验到对等节点",
    description="将指定经验推送到所有已注册的对等节点。",
)
async def sync_experience(
    experience_id: UUID,
    data: SyncRequest | None = None,
    current_user: User = Depends(get_current_user),
) -> dict:
    service = get_federation_service()
    exp_data = data.experience_data if data else None
    results = await service.sync_experience(experience_id, exp_data)
    return {
        "experience_id": str(experience_id),
        "sync_results": results,
        "total_peers": len(service.list_peers()),
    }


@router.get(
    "/search",
    summary="联邦搜索",
    description="跨所有对等节点 + 本地搜索经验。单个节点故障不影响整体搜索。",
)
async def federated_search(
    query: str = Query(..., min_length=1, description="搜索查询"),
    domain: str | None = Query(None, description="领域过滤"),
    limit: int = Query(10, ge=1, le=50, description="每个节点返回数量上限"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    # ── 本地搜索 ──
    matcher = ExperienceMatcher(session)
    local_matches = await matcher.match_by_keywords(
        query=query, limit=limit, domain=domain
    )
    local_results = [
        {
            "experience_id": str(m.experience.id),
            "intent": m.experience.intent,
            "similarity": m.similarity,
            "source": "local",
        }
        for m in local_matches
    ]

    # ── 联邦搜索 ──
    service = get_federation_service()
    result = await service.federated_search(
        query=query, domain=domain, limit=limit, local_search=local_results
    )
    return result
