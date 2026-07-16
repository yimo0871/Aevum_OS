"""HumanExpression ORM 模型 - 人类表达层（双世界架构的人类世界）."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from pgvector.sqlalchemy import Vector

from app.core.database import Base


class HumanExpression(Base):
    """人类表达对象 - 与 Agent Experience 严格分离.

    人机分离四原则:
    - 人类数据不进入经验图谱（独立表，仅通过 WorldBridge 语义引用）
    - Agent 不得改写人类表达（写入需人类 JWT）
    - 人类输出仅供观察性使用（只读接口）
    - Agent 输出必须结构化（8步流水线保证）
    """

    __tablename__ = "human_expressions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    # text / image / video / audio / link / note
    type = Column(String(20), nullable=False, index=True)
    # 原始内容，完全自由 JSONB
    content = Column(JSONB, nullable=False, default=dict)
    # 可选元数据
    metadata_ = Column("metadata", JSONB, nullable=False, default=dict)
    # 语义向量（后端存储时自动生成，供 Agent 观察用）
    embedding = Column(Vector(1536), nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<HumanExpression(id={self.id}, type={self.type})>"

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "type": self.type,
            "content": self.content,
            "metadata": self.metadata_ if self.metadata_ else {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
