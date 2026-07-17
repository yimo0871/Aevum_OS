"""Federation service - 联邦网络，跨节点经验共享.

支持多个 Aevum 节点之间互相注册、同步经验、联邦搜索。
单个节点故障不会影响整体联邦搜索。
"""

from __future__ import annotations

import logging
from uuid import UUID

import httpx

logger = logging.getLogger(__name__)


class FederationService:
    """联邦网络服务.

    职责:
    - 管理对等节点（注册/列表）
    - 向所有对等节点推送经验
    - 从单个对等节点拉取经验
    - 联邦搜索（本地 + 所有对等节点）
    """

    def __init__(self, node_url: str, node_id: str) -> None:
        """初始化联邦节点.

        Args:
            node_url: 本节点 URL（如 http://localhost:8000）
            node_id: 本节点唯一标识
        """
        self.node_url = node_url.rstrip("/")
        self.node_id = node_id
        # 已注册的对等节点: {peer_id: {"url": peer_url, "id": peer_id}}
        self._peers: dict[str, dict] = {}

    def register_peer(self, peer_url: str, peer_id: str) -> dict:
        """注册一个远程 Aevum 节点.

        Args:
            peer_url: 对等节点 URL
            peer_id: 对等节点唯一标识

        Returns:
            注册的对等节点信息
        """
        peer_url = peer_url.rstrip("/")
        peer_info = {"url": peer_url, "id": peer_id}
        self._peers[peer_id] = peer_info

        logger.info(
            "[FEDERATION] 对等节点已注册: peer_id=%s, url=%s (本节点=%s)",
            peer_id, peer_url, self.node_id,
        )
        return peer_info

    def list_peers(self) -> list[dict]:
        """列出所有已注册的对等节点.

        Returns:
            对等节点信息列表
        """
        return list(self._peers.values())

    def unregister_peer(self, peer_id: str) -> bool:
        """注销对等节点.

        Args:
            peer_id: 对等节点唯一标识

        Returns:
            是否成功注销
        """
        if peer_id in self._peers:
            del self._peers[peer_id]
            logger.info("[FEDERATION] 对等节点已注销: peer_id=%s", peer_id)
            return True
        return False

    async def sync_experience(
        self, experience_id: UUID, experience_data: dict | None = None
    ) -> dict:
        """将经验推送到所有对等节点.

        Args:
            experience_id: 经验 ID
            experience_data: 经验数据（如为 None，仅推送 ID，由对等节点拉取）

        Returns:
            同步结果: {peer_id: success/failure}
        """
        results: dict[str, bool] = {}

        for peer_id, peer_info in self._peers.items():
            peer_url = peer_info["url"]
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    payload = experience_data or {"experience_id": str(experience_id)}
                    resp = await client.post(
                        f"{peer_url}/api/v1/experiences",
                        json=payload,
                    )
                    results[peer_id] = resp.status_code in (200, 201)
            except Exception as e:
                logger.warning(
                    "[FEDERATION] 同步经验到对等节点失败: peer_id=%s, error=%s",
                    peer_id, e,
                )
                results[peer_id] = False

        logger.info(
            "[FEDERATION] 经验同步完成: experience_id=%s, results=%s",
            experience_id, results,
        )
        return results

    async def _fetch_from_peer_raw(
        self,
        peer_id: str,
        query: str,
        domain: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """从单个对等节点查询经验（不捕获异常，供内部调用）.

        Raises:
            ValueError: 对等节点未注册
            Exception: 网络或 HTTP 错误
        """
        if peer_id not in self._peers:
            raise ValueError(f"对等节点未注册: {peer_id}")

        peer_url = self._peers[peer_id]["url"]

        async with httpx.AsyncClient(timeout=10.0) as client:
            payload: dict = {"query": query, "limit": limit}
            if domain:
                payload["domain"] = domain
            resp = await client.post(
                f"{peer_url}/api/v1/retrieval/search",
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    async def fetch_from_peer(
        self,
        peer_id: str,
        query: str,
        domain: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """从单个对等节点查询经验（捕获异常，返回空列表）.

        Args:
            peer_id: 对等节点唯一标识
            query: 搜索查询
            domain: 领域过滤
            limit: 返回数量上限

        Returns:
            搜索结果列表（失败时返回空列表）

        Raises:
            ValueError: 对等节点未注册
        """
        try:
            return await self._fetch_from_peer_raw(peer_id, query, domain, limit)
        except ValueError:
            raise
        except Exception as e:
            logger.warning(
                "[FEDERATION] 从对等节点拉取失败: peer_id=%s, error=%s",
                peer_id, e,
            )
            return []

    async def federated_search(
        self,
        query: str,
        domain: str | None = None,
        limit: int = 10,
        local_search: list[dict] | None = None,
    ) -> dict:
        """联邦搜索 - 跨所有对等节点 + 本地搜索.

        单个对等节点故障不会影响整体搜索。

        Args:
            query: 搜索查询
            domain: 领域过滤
            limit: 每个节点返回数量上限
            local_search: 本地搜索结果（由调用方提供，避免循环依赖）

        Returns:
            {
                "query": query,
                "local_results": [...],
                "peer_results": {peer_id: [...]},
                "errors": [peer_id, ...],
            }
        """
        local_results = local_search or []
        peer_results: dict[str, list] = {}
        errors: list[str] = []

        for peer_id in self._peers:
            try:
                results = await self._fetch_from_peer_raw(peer_id, query, domain, limit)
                peer_results[peer_id] = results
            except Exception as e:
                logger.warning(
                    "[FEDERATION] 联邦搜索中对等节点失败: peer_id=%s, error=%s",
                    peer_id, e,
                )
                errors.append(peer_id)

        logger.info(
            "[FEDERATION] 联邦搜索完成: query='%s', local=%d, peers=%d, errors=%d",
            query, len(local_results), len(peer_results), len(errors),
        )

        return {
            "query": query,
            "local_results": local_results,
            "peer_results": peer_results,
            "errors": errors,
        }
