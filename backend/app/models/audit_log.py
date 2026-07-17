"""AuditLog ORM model - 审计日志记录."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.core.database import Base


class AuditLog(Base):
    """审计日志 - 记录系统中所有关键操作.

    支持的操作类型:
    - create: 创建
    - update: 更新
    - delete: 删除
    - access: 访问
    - fork: 分叉
    - cite: 引用
    - compress: 压缩
    - forget: 遗忘

    实体类型:
    - experience: 经验
    - workflow: 工作流
    - agent: Agent
    """

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action = Column(String(50), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    actor_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    actor_type = Column(String(20), nullable=False)  # user | agent | system
    details = Column(JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<AuditLog(action={self.action}, entity={self.entity_type}:{self.entity_id})>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": str(self.entity_id),
            "actor_id": str(self.actor_id) if self.actor_id else None,
            "actor_type": self.actor_type,
            "details": self.details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
