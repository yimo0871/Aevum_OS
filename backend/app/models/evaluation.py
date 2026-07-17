"""Evaluation ORM model - 评估记录."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.core.database import Base


class Evaluation(Base):
    """评估记录 - 对任务、经验、工作流的评估结果.

    核心原则：无评估 = 无效输出
    """

    __tablename__ = "evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ── 评估目标 ──
    target_type = Column(String(20), nullable=False)  # task | experience | workflow | system
    target_id = Column(UUID(as_uuid=True), nullable=False)

    # ── 评估器 ──
    evaluator = Column(String(50), nullable=False)  # rule_based | llm_based | human

    # ── 评估得分 ──
    scores = Column(JSONB, nullable=False, default=dict)
    # 例: { completeness: 0.9, correctness: 0.85, efficiency: 0.8 }

    # ── 总分 ──
    overall_score = Column(Float, nullable=False, default=0.0)

    # ── 评估摘要 ──
    summary = Column(Text, nullable=True)

    # ── 详细评估 ──
    details = Column(JSONB, nullable=False, default=dict)

    # ── 审计字段 ──
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self) -> str:
        return f"<Evaluation(target={self.target_type}:{self.target_id}, score={self.overall_score})>"


class SystemMetric(Base):
    """系统级指标 - 持续追踪的七个核心指标.

    指标列表:
    - experience_reuse_rate: 经验复用率
    - workflow_success_rate: 工作流成功率
    - cross_agent_transfer_rate: 跨 Agent 经验迁移率
    - external_dependency_ratio: 外部依赖比例（越低越好）
    - learning_velocity: 学习速度
    - convergence_speed: 收敛速度
    - human_intervention_rate: 人类干预率（越低越好）
    """

    __tablename__ = "system_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_name = Column(String(50), nullable=False, index=True)
    value = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    metadata_ = Column("metadata", JSONB, nullable=False, default=dict)

    def __repr__(self) -> str:
        return f"<SystemMetric({self.metric_name}={self.value})>"


class HumanReview(Base):
    """人类专家评审记录 - 人机协同评估.

    用于记录人类专家对经验的评审意见，并据此调整信任评分。
    """

    __tablename__ = "human_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experience_id = Column(
        UUID(as_uuid=True),
        ForeignKey("experiences.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    rating = Column(Integer, nullable=False)  # 1-5 星
    notes = Column(Text, nullable=True)
    recommend_archive = Column(Boolean, nullable=False, default=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<HumanReview(experience={self.experience_id}, rating={self.rating})>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "experience_id": str(self.experience_id),
            "reviewer_id": str(self.reviewer_id),
            "rating": self.rating,
            "notes": self.notes,
            "recommend_archive": self.recommend_archive,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
