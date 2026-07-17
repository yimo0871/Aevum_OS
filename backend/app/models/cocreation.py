"""Co-creation Session ORM 模型 - 人机协同创作工作流."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.core.database import Base


class CoCreationSession(Base):
    """人机协同创作会话.

    工作流状态:
    - defined: 已定义（用户提交任务描述）
    - exploring: 探索中（Agent 搜索相关经验并生成方案）
    - completed: 已完成（用户接受 Agent 方案，经验已存入 Aevum）
    - rejected: 已拒绝（用户拒绝 Agent 方案）
    """

    __tablename__ = "cocreation_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_description = Column(Text, nullable=False)
    domain = Column(String(100), nullable=True)
    human_constraints = Column(JSONB, nullable=False, default=dict)
    agent_proposals = Column(JSONB, nullable=True)
    human_feedback = Column(Text, nullable=True)
    human_rating = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, default="defined", index=True)
    experience_id = Column(
        UUID(as_uuid=True),
        ForeignKey("experiences.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<CoCreationSession(id={self.id}, status={self.status})>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "task_description": self.task_description,
            "domain": self.domain,
            "human_constraints": self.human_constraints,
            "agent_proposals": self.agent_proposals,
            "human_feedback": self.human_feedback,
            "human_rating": self.human_rating,
            "status": self.status,
            "experience_id": str(self.experience_id) if self.experience_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
