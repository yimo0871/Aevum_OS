"""WorkflowTemplate ORM model - 可复用工作流模板."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.core.database import Base


class WorkflowTemplate(Base):
    """WorkflowTemplate 对象 - 标准化的可复用工作流模板.

    每个模板描述了在特定领域和任务类型下，
    Agent 应该遵循的步骤、使用的工具以及预期结果。
    """

    __tablename__ = "workflow_templates"

    # ── 标识 ──
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ── 基本信息 ──
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # ── 分类 ──
    domain = Column(String(100), nullable=False, index=True)
    task_type = Column(String(100), nullable=False, index=True)

    # ── 工作流定义 ──
    # steps: [{ name, action, description, expected_result }]
    steps = Column(JSONB, nullable=False, default=list)
    # tools: ["docker", "kubectl", ...]
    tools = Column(JSONB, nullable=False, default=list)
    # expected_outcome: { success_criteria, metrics, artifacts }
    expected_outcome = Column(JSONB, nullable=False, default=dict)

    # ── 统计 ──
    success_rate = Column(Float, nullable=False, default=0.0)
    usage_count = Column(Integer, nullable=False, default=0)

    # ── 可见性 ──
    # public: 所有人可见
    # private: 仅创建者可见
    visibility = Column(String(20), nullable=False, default="public", server_default="public", index=True)

    # ── 审计字段 ──
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<WorkflowTemplate(id={self.id}, name={self.name[:50]}...)>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "domain": self.domain,
            "task_type": self.task_type,
            "steps": self.steps,
            "tools": self.tools,
            "expected_outcome": self.expected_outcome,
            "success_rate": self.success_rate,
            "usage_count": self.usage_count,
            "visibility": self.visibility,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
