"""System metrics - 系统级指标追踪.

七个核心系统级追踪指标：

| 指标 | 含义 |
|------|------|
| experience_reuse_rate | 经验复用率 |
| workflow_success_rate | 工作流成功率 |
| cross_agent_transfer_rate | 跨 Agent 经验迁移率 |
| external_dependency_ratio | 外部依赖比例（越低越好） |
| learning_velocity | 学习速度 |
| convergence_speed | 收敛速度 |
| human_intervention_rate | 人类干预率（越低越好） |
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluation import SystemMetric
from app.models.experience import Experience, ExperienceRelation


class SystemMetricsCalculator:
    """系统指标计算器 - 计算和缓存系统级指标."""

    METRIC_NAMES = [
        "experience_reuse_rate",
        "workflow_success_rate",
        "cross_agent_transfer_rate",
        "external_dependency_ratio",
        "learning_velocity",
        "convergence_speed",
        "human_intervention_rate",
    ]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def compute_all(self) -> dict[str, float]:
        """计算所有系统指标."""
        return {
            "experience_reuse_rate": await self._compute_reuse_rate(),
            "workflow_success_rate": await self._compute_workflow_success_rate(),
            "cross_agent_transfer_rate": await self._compute_cross_agent_transfer_rate(),
            "external_dependency_ratio": await self._compute_external_dependency_ratio(),
            "learning_velocity": await self._compute_learning_velocity(),
            "convergence_speed": await self._compute_convergence_speed(),
            "human_intervention_rate": await self._compute_human_intervention_rate(),
        }

    async def _compute_reuse_rate(self) -> float:
        """经验复用率 = 被复用的经验数 / 总经验数."""
        total_result = await self.session.execute(
            select(func.count(Experience.id))
        )
        total = total_result.scalar() or 0
        if total == 0:
            return 0.0

        reuse_result = await self.session.execute(
            select(func.count(func.distinct(ExperienceRelation.source_id)))
            .where(ExperienceRelation.relation_type == "reuse")
        )
        reused = reuse_result.scalar() or 0

        return min(1.0, reused / total)

    async def _compute_workflow_success_rate(self) -> float:
        """工作流成功率 = 成功经验数 / 总经验数."""
        total_result = await self.session.execute(
            select(func.count(Experience.id))
        )
        total = total_result.scalar() or 0
        if total == 0:
            return 0.0

        # 基于 outcome.success 字段（JSONB 查询）
        success_result = await self.session.execute(
            select(func.count(Experience.id))
            .where(Experience.outcome["success"].astext == "true")
        )
        success = success_result.scalar() or 0

        return success / total

    async def _compute_cross_agent_transfer_rate(self) -> float:
        """跨 Agent 经验迁移率 = 有跨 Agent 引用的经验数 / 总经验数."""
        total_result = await self.session.execute(
            select(func.count(Experience.id))
        )
        total = total_result.scalar() or 0
        if total == 0:
            return 0.0

        # 基于 citation 和 fork 关系
        transfer_result = await self.session.execute(
            select(func.count(func.distinct(ExperienceRelation.source_id)))
            .where(ExperienceRelation.relation_type.in_(["citation", "fork"]))
        )
        transferred = transfer_result.scalar() or 0

        return min(1.0, transferred / total)

    async def _compute_external_dependency_ratio(self) -> float:
        """外部依赖比例 = 外部来源经验数 / 总经验数（越低越好）."""
        total_result = await self.session.execute(
            select(func.count(Experience.id))
        )
        total = total_result.scalar() or 0
        if total == 0:
            return 0.0

        # 基于 provenance.external_sources 非空的经验
        # MVP: 暂时返回 0（无外部来源数据）
        return 0.0

    async def _compute_learning_velocity(self) -> float:
        """学习速度 = 最近7天新增经验数 / 7."""
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        result = await self.session.execute(
            select(func.count(Experience.id))
            .where(Experience.created_at >= seven_days_ago)
        )
        count = result.scalar() or 0
        return count / 7.0  # 平均每天新增

    async def _compute_convergence_speed(self) -> float:
        """收敛速度 = 已评估经验数 / 总经验数."""
        total_result = await self.session.execute(
            select(func.count(Experience.id))
        )
        total = total_result.scalar() or 0
        if total == 0:
            return 0.0

        evaluated_result = await self.session.execute(
            select(func.count(Experience.id))
            .where(Experience.evaluation_status == "evaluated")
        )
        evaluated = evaluated_result.scalar() or 0

        return evaluated / total

    async def _compute_human_intervention_rate(self) -> float:
        """人类干预率 = 有人类信号的经验数 / 总经验数（越低越好）."""
        total_result = await self.session.execute(
            select(func.count(Experience.id))
        )
        total = total_result.scalar() or 0
        if total == 0:
            return 0.0

        # MVP: 暂时返回 0（无人类干预数据）
        return 0.0

    async def save_metrics(self, metrics: dict[str, float]) -> None:
        """保存指标到数据库."""
        now = datetime.now(timezone.utc)
        for name, value in metrics.items():
            metric = SystemMetric(
                metric_name=name,
                value=value,
                timestamp=now,
                metadata_={},
            )
            self.session.add(metric)
        await self.session.flush()

    async def get_history(
        self, metric_name: str, hours: int = 24
    ) -> list[dict]:
        """获取指标历史数据."""
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        result = await self.session.execute(
            select(SystemMetric)
            .where(SystemMetric.metric_name == metric_name)
            .where(SystemMetric.timestamp >= since)
            .order_by(SystemMetric.timestamp.desc())
        )
        metrics = result.scalars().all()
        return [
            {
                "value": m.value,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None,
            }
            for m in metrics
        ]
