"""Experience ORM model - 系统核心数据结构."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Experience(Base):
    """Experience 对象 - 系统的原子数据单元.

    每一次 Agent 任务执行都必须生成一个 Experience 对象。
    遵循设计蓝图 v2 的数据结构定义。
    """

    __tablename__ = "experiences"

    # ── 标识 ──
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # ── 上下文 ──
    # context: { domain, task_type, constraints }
    context = Column(JSONB, nullable=False, default=dict)

    # ── 意图 ──
    intent = Column(Text, nullable=False)

    # ── 执行过程 ──
    # execution: { steps, tools, trace }
    execution = Column(JSONB, nullable=False, default=dict)

    # ── 结果 ──
    # outcome: { success, metrics }
    outcome = Column(JSONB, nullable=False, default=dict)

    # ── 反思 ──
    # reflection: { what_worked, what_failed, why }
    reflection = Column(JSONB, nullable=False, default=dict)

    # ── 可复用模式 ──
    reusable_patterns = Column(JSONB, nullable=False, default=list)

    # ── 置信度评分 ──
    confidence_score = Column(Float, nullable=False, default=0.0)

    # ── 来源追溯 ──
    # provenance: { human_signals, agent_signals, external_sources }
    provenance = Column(JSONB, nullable=False, default=dict)

    # ── 版本 ──
    version = Column(Integer, nullable=False, default=1)

    # ── 向量嵌入（用于检索）──
    # embedding 列在迁移中通过 pgvector 创建，这里用类型注解
    # 实际类型: Vector(1536)
    # 注意：pgvector 的 Vector 类型需要在迁移中手动添加

    # ── 审计字段 ──
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── 评估状态 ──
    evaluation_status = Column(
        String(20), nullable=False, default="pending"
    )  # pending | evaluated | skipped

    # ── 关系 ──
    traces = relationship("ExecutionTrace", back_populates="experience", cascade="all, delete-orphan")
    relations_as_source = relationship(
        "ExperienceRelation",
        foreign_keys="ExperienceRelation.source_id",
        back_populates="source",
        cascade="all, delete-orphan",
    )
    relations_as_target = relationship(
        "ExperienceRelation",
        foreign_keys="ExperienceRelation.target_id",
        back_populates="target",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Experience(id={self.id}, intent={self.intent[:50]}...)>"

    def to_dict(self) -> dict:
        """Convert to dictionary (excluding embedding for performance)."""
        return {
            "id": str(self.id),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "context": self.context,
            "intent": self.intent,
            "execution": self.execution,
            "outcome": self.outcome,
            "reflection": self.reflection,
            "reusable_patterns": self.reusable_patterns,
            "confidence_score": self.confidence_score,
            "provenance": self.provenance,
            "version": self.version,
            "evaluation_status": self.evaluation_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ExperienceRelation(Base):
    """经验图谱中的边 - 描述经验之间的关系.

    边类型:
    - reuse: 复用
    - citation: 引用
    - fork: 分叉
    - improvement: 改进
    - dependency: 依赖
    """

    __tablename__ = "experience_relations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("experiences.id", ondelete="CASCADE"), nullable=False)
    target_id = Column(UUID(as_uuid=True), ForeignKey("experiences.id", ondelete="CASCADE"), nullable=False)
    relation_type = Column(String(20), nullable=False)  # reuse | citation | fork | improvement | dependency
    weight = Column(Float, nullable=False, default=1.0)
    metadata_ = Column("metadata", JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # ── 关系 ──
    source = relationship("Experience", foreign_keys=[source_id], back_populates="relations_as_source")
    target = relationship("Experience", foreign_keys=[target_id], back_populates="relations_as_target")

    def __repr__(self) -> str:
        return f"<ExperienceRelation({self.source_id} -[{self.relation_type}]-> {self.target_id})>"
