"""ExecutionTrace ORM model - 执行追踪记录."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class ExecutionTrace(Base):
    """执行追踪 - 记录 Agent 任务的完整执行过程.

    对应 8 步流水线中的 Step 4: record_full_trace
    """

    __tablename__ = "execution_traces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ── 关联经验 ──
    experience_id = Column(UUID(as_uuid=True), ForeignKey("experiences.id", ondelete="CASCADE"), nullable=True)

    # ── 任务信息 ──
    intent = Column(Text, nullable=False)
    context = Column(JSONB, nullable=False, default=dict)

    # ── 执行状态 ──
    status = Column(String(20), nullable=False, default="pending")
    # pending | running | completed | failed | invalid

    # ── 执行步骤 ──
    steps = Column(JSONB, nullable=False, default=list)

    # ── 使用的工具 ──
    tools = Column(JSONB, nullable=False, default=list)

    # ── 完整追踪 ──
    trace = Column(JSONB, nullable=False, default=dict)

    # ── 执行时长（秒）──
    duration = Column(Float, nullable=True)

    # ── 错误信息 ──
    error = Column(Text, nullable=True)

    # ── 审计字段 ──
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── 8步流水线状态 ──
    pipeline_state = Column(JSONB, nullable=False, default=dict)
    # 记录每步的执行状态: { step1: {status, started_at, completed_at}, ... }

    # ── 关系 ──
    experience = relationship("Experience", back_populates="traces")

    def __repr__(self) -> str:
        return f"<ExecutionTrace(id={self.id}, status={self.status})>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "experience_id": str(self.experience_id) if self.experience_id else None,
            "intent": self.intent,
            "context": self.context,
            "status": self.status,
            "steps": self.steps,
            "tools": self.tools,
            "trace": self.trace,
            "duration": self.duration,
            "error": self.error,
            "pipeline_state": self.pipeline_state,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
