"""WorldBridge ORM 模型 - 双世界架构桥接表.

WorldBridge 是 HumanExpression 和 Experience 之间唯一的连接方式，
不通过向量匹配，而是通过语义引用建立关联。

四种桥接类型:
- inspiration:    人类 -> Agent (用户标记"这个想法可以变成 Agent 任务")
- observation:    Agent -> Human (Agent 执行任务前搜索相关人类表达)
- recommendation: Agent -> Human (Agent 基于经验向用户推荐行动方案)
- reflection:     人类 -> Agent (用户对 Agent 执行结果进行评价/反思)
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.core.database import Base


class WorldBridge(Base):
    """世界桥接 - HumanExpression 与 Experience 之间的语义引用."""

    __tablename__ = "world_bridges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bridge_type = Column(String(20), nullable=False, index=True)
    human_expression_id = Column(
        UUID(as_uuid=True), ForeignKey("human_expressions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    experience_id = Column(
        UUID(as_uuid=True), ForeignKey("experiences.id", ondelete="CASCADE"), nullable=False, index=True
    )
    metadata_ = Column("metadata", JSONB, nullable=False, default=dict)
    # 创建者标识（user_id 或 agent_id）
    created_by = Column(String(100), nullable=False)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # 防止重复桥接
    __table_args__ = (
        UniqueConstraint(
            "bridge_type", "human_expression_id", "experience_id",
            name="uq_bridge_type_expr_exp",
        ),
    )

    def __repr__(self) -> str:
        return f"<WorldBridge(id={self.id}, type={self.bridge_type})>"

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "bridge_type": self.bridge_type,
            "human_expression_id": str(self.human_expression_id) if self.human_expression_id else None,
            "experience_id": str(self.experience_id) if self.experience_id else None,
            "metadata": self.metadata_ if self.metadata_ else {},
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
