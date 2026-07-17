"""审计日志服务 - 记录与检索系统操作审计轨迹."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


class AuditLogger:
    """审计日志记录器.

    职责:
    - 记录关键操作（创建/更新/删除/访问/分叉/引用/压缩/遗忘）
    - 检索实体的审计轨迹
    - 检索操作者的操作历史
    """

    VALID_ACTIONS = {
        "create", "update", "delete", "access",
        "fork", "cite", "compress", "forget",
    }
    VALID_ENTITY_TYPES = {"experience", "workflow", "agent"}
    VALID_ACTOR_TYPES = {"user", "agent", "system"}

    async def log(
        self,
        action: str,
        entity_type: str,
        entity_id: UUID,
        session: AsyncSession,
        actor_id: UUID | None = None,
        actor_type: str = "system",
        details: dict | None = None,
    ) -> AuditLog:
        """创建一条审计日志.

        Args:
            action: 操作类型 (create/update/delete/access/fork/cite/compress/forget)
            entity_type: 实体类型 (experience/workflow/agent)
            entity_id: 实体 ID
            session: 异步数据库会话
            actor_id: 操作者 ID（可为空，表示系统操作）
            actor_type: 操作者类型 (user/agent/system)
            details: 额外上下文信息

        Returns:
            创建的 AuditLog 记录
        """
        if action not in self.VALID_ACTIONS:
            raise ValueError(f"无效的操作类型: {action}，有效值: {self.VALID_ACTIONS}")
        if entity_type not in self.VALID_ENTITY_TYPES:
            raise ValueError(f"无效的实体类型: {entity_type}，有效值: {self.VALID_ENTITY_TYPES}")
        if actor_type not in self.VALID_ACTOR_TYPES:
            raise ValueError(f"无效的操作者类型: {actor_type}，有效值: {self.VALID_ACTOR_TYPES}")

        entry = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            actor_type=actor_type,
            details=details if details is not None else {},
        )
        session.add(entry)
        await session.flush()
        await session.refresh(entry)

        logger.info(
            "[AUDIT] 记录日志: action=%s, entity=%s:%s, actor=%s:%s",
            action, entity_type, entity_id, actor_type, actor_id,
        )
        return entry

    async def get_logs(
        self,
        entity_type: str,
        entity_id: UUID,
        session: AsyncSession,
        limit: int = 100,
    ) -> list[AuditLog]:
        """检索某实体的审计轨迹.

        Args:
            entity_type: 实体类型
            entity_id: 实体 ID
            session: 异步数据库会话
            limit: 返回记录上限

        Returns:
            审计日志列表（按时间倒序）
        """
        query = (
            select(AuditLog)
            .where(
                AuditLog.entity_type == entity_type,
                AuditLog.entity_id == entity_id,
            )
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_actor_logs(
        self,
        actor_id: UUID,
        session: AsyncSession,
        limit: int = 100,
    ) -> list[AuditLog]:
        """检索某操作者的操作历史.

        Args:
            actor_id: 操作者 ID
            session: 异步数据库会话
            limit: 返回记录上限

        Returns:
            审计日志列表（按时间倒序）
        """
        query = (
            select(AuditLog)
            .where(AuditLog.actor_id == actor_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_logs_by_action(
        self,
        action: str,
        session: AsyncSession,
        limit: int = 100,
    ) -> list[AuditLog]:
        """按操作类型检索日志.

        Args:
            action: 操作类型
            session: 异步数据库会话
            limit: 返回记录上限

        Returns:
            审计日志列表（按时间倒序）
        """
        query = (
            select(AuditLog)
            .where(AuditLog.action == action)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(query)
        return list(result.scalars().all())
