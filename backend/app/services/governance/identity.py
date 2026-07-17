"""Agent 身份与经验所有权管理 - DID 生成与所有权验证."""

from __future__ import annotations

import logging
import uuid
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.experience import Experience

logger = logging.getLogger(__name__)


class IdentityManager:
    """Agent 身份与经验所有权管理器.

    职责:
    - 为 Agent 生成去中心化身份标识 (DID)
    - 分配经验所有权（将经验归属到 Agent）
    - 查询经验的所有者
    - 验证 Agent 对经验的所有权
    """

    DID_PREFIX = "did:aevum"

    async def generate_did(
        self, agent_id: UUID, session: AsyncSession
    ) -> str:
        """为 Agent 生成 DID（去中心化身份标识）.

        DID 格式: did:aevum:{uuid}

        如果 Agent 已有 DID，则返回现有 DID。

        Args:
            agent_id: Agent ID
            session: 异步数据库会话

        Returns:
            生成的 DID 字符串

        Raises:
            ValueError: Agent 不存在
        """
        agent = await session.get(Agent, agent_id)
        if agent is None:
            raise ValueError(f"Agent 不存在: {agent_id}")

        # ── 若已有 DID，直接返回（幂等）──
        if agent.did:
            logger.info("[IDENTITY] Agent 已有 DID: agent_id=%s, did=%s", agent_id, agent.did)
            return agent.did

        did = f"{self.DID_PREFIX}:{uuid.uuid4()}"
        agent.did = did
        await session.flush()

        logger.info("[IDENTITY] 已生成 DID: agent_id=%s, did=%s", agent_id, did)
        return did

    async def assign_ownership(
        self,
        experience_id: UUID,
        agent_id: UUID,
        session: AsyncSession,
    ) -> Experience | None:
        """将经验的所有权分配给指定 Agent.

        Args:
            experience_id: 经验 ID
            agent_id: Agent ID
            session: 异步数据库会话

        Returns:
            更新后的 Experience，若经验或 Agent 不存在返回 None

        Raises:
            ValueError: Agent 不存在
        """
        logger.info(
            "[IDENTITY] 分配所有权: experience_id=%s -> agent_id=%s",
            experience_id, agent_id,
        )

        # ── 验证 Agent 存在 ──
        agent = await session.get(Agent, agent_id)
        if agent is None:
            raise ValueError(f"Agent 不存在: {agent_id}")

        # ── 获取经验 ──
        experience = await session.get(Experience, experience_id)
        if experience is None:
            logger.warning("[IDENTITY] 经验不存在: experience_id=%s", experience_id)
            return None

        experience.owner_agent_id = agent_id
        await session.flush()

        logger.info(
            "[IDENTITY] 所有权已分配: experience_id=%s -> agent_id=%s (%s)",
            experience_id, agent_id, agent.name,
        )
        return experience

    async def get_owner(
        self, experience_id: UUID, session: AsyncSession
    ) -> Agent | None:
        """获取经验的所有者 Agent.

        Args:
            experience_id: 经验 ID
            session: 异步数据库会话

        Returns:
            所有者 Agent，若无所有者或经验不存在返回 None
        """
        experience = await session.get(Experience, experience_id)
        if experience is None:
            return None
        if experience.owner_agent_id is None:
            return None
        return await session.get(Agent, experience.owner_agent_id)

    async def verify_ownership(
        self,
        experience_id: UUID,
        agent_id: UUID,
        session: AsyncSession,
    ) -> bool:
        """验证 Agent 是否拥有指定经验的所有权.

        Args:
            experience_id: 经验 ID
            agent_id: Agent ID
            session: 异步数据库会话

        Returns:
            True 表示 Agent 拥有该经验
        """
        experience = await session.get(Experience, experience_id)
        if experience is None:
            return False
        return experience.owner_agent_id == agent_id
