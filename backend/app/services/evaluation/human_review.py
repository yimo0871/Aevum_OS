"""人机协同评估服务 - 人类专家评审与信任评分调整."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluation import HumanReview
from app.models.experience import Experience, ExperienceRelation

logger = logging.getLogger(__name__)


class HumanReviewService:
    """人类专家评审服务.

    职责:
    - 创建人类评审记录并调整经验信任评分
    - 检索经验的评审历史
    - 查询待评审经验（低置信度、高使用量）
    """

    # 评分到信任评分调整的映射
    # rating 1-2: 降低信任；rating 3: 微调；rating 4-5: 提升信任
    RATING_WEIGHTS = {
        1: -0.20,
        2: -0.10,
        3: 0.0,
        4: 0.10,
        5: 0.20,
    }

    async def create_review(
        self,
        experience_id: UUID,
        reviewer_id: UUID,
        rating: int,
        session: AsyncSession,
        notes: str | None = None,
        recommend_archive: bool = False,
    ) -> HumanReview:
        """创建人类评审记录并调整经验信任评分.

        Args:
            experience_id: 经验 ID
            reviewer_id: 评审者 ID
            rating: 评分 (1-5)
            session: 异步数据库会话
            notes: 评审备注
            recommend_archive: 是否建议归档

        Returns:
            创建的 HumanReview 记录

        Raises:
            ValueError: 评分不在 1-5 范围内
            ValueError: 经验不存在
        """
        if not 1 <= rating <= 5:
            raise ValueError(f"评分必须在 1-5 范围内，收到: {rating}")

        experience = await session.get(Experience, experience_id)
        if experience is None:
            raise ValueError(f"经验不存在: {experience_id}")

        # ── 创建评审记录 ──
        review = HumanReview(
            experience_id=experience_id,
            reviewer_id=reviewer_id,
            rating=rating,
            notes=notes,
            recommend_archive=recommend_archive,
        )
        session.add(review)
        await session.flush()
        await session.refresh(review)

        # ── 调整信任评分 ──
        adjustment = self.RATING_WEIGHTS.get(rating, 0.0)
        original_confidence = experience.confidence_score or 0.0
        new_confidence = max(0.0, min(1.0, original_confidence + adjustment))
        experience.confidence_score = round(new_confidence, 4)

        # ── 若建议归档且评分极低，标记为待遗忘 ──
        if recommend_archive and rating <= 2:
            provenance = dict(experience.provenance) if experience.provenance else {}
            provenance["archive_recommended"] = True
            provenance["archive_recommended_by"] = str(reviewer_id)
            experience.provenance = provenance

        await session.flush()

        logger.info(
            "[HUMAN_REVIEW] 评审已创建: experience_id=%s, reviewer=%s, rating=%d, "
            "confidence %.4f -> %.4f",
            experience_id, reviewer_id, rating,
            original_confidence, experience.confidence_score,
        )
        return review

    async def get_reviews(
        self, experience_id: UUID, session: AsyncSession
    ) -> list[HumanReview]:
        """获取经验的所有人类评审记录.

        Args:
            experience_id: 经验 ID
            session: 异步数据库会话

        Returns:
            评审记录列表（按时间倒序）
        """
        query = (
            select(HumanReview)
            .where(HumanReview.experience_id == experience_id)
            .order_by(HumanReview.created_at.desc())
        )
        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_pending_reviews(
        self,
        session: AsyncSession,
        min_usage: int = 5,
        max_confidence: float = 0.5,
        limit: int = 50,
    ) -> list[Experience]:
        """获取待评审经验 -- 高使用量但低置信度的经验.

        判定条件:
        - 复用次数 >= min_usage（高使用量，影响范围大）
        - 置信度 <= max_confidence（低置信度，需要人类校准）
        - 状态为 active
        - 尚无人类评审记录

        Args:
            session: 异步数据库会话
            min_usage: 最小复用次数阈值
            max_confidence: 最大置信度阈值
            limit: 返回上限

        Returns:
            待评审经验列表
        """
        # ── 子查询：已有评审的经验 ID ──
        reviewed_subq = (
            select(HumanReview.experience_id)
            .distinct()
            .subquery()
        )

        # ── 查询候选经验 ──
        query = (
            select(Experience)
            .where(
                Experience.status == "active",
                Experience.confidence_score <= max_confidence,
                ~Experience.id.in_(select(reviewed_subq)),
            )
            .order_by(Experience.confidence_score.asc())
            .limit(limit)
        )
        result = await session.execute(query)
        candidates = list(result.scalars().all())

        # ── 过滤：复用次数 >= min_usage ──
        pending: list[Experience] = []
        for exp in candidates:
            reuse_count_result = await session.execute(
                select(func.count(ExperienceRelation.id)).where(
                    ExperienceRelation.target_id == exp.id,
                    ExperienceRelation.relation_type == "reuse",
                )
            )
            reuse_count = reuse_count_result.scalar() or 0
            if reuse_count >= min_usage:
                pending.append(exp)

        logger.info(
            "[HUMAN_REVIEW] 待评审经验: 候选 %d, 符合条件 %d",
            len(candidates), len(pending),
        )
        return pending

    @staticmethod
    def compute_trust_adjustment(rating: int) -> float:
        """根据评分计算信任评分调整量（纯函数，便于测试）.

        Args:
            rating: 评分 (1-5)

        Returns:
            信任评分调整量（负值降低，正值提升）
        """
        return HumanReviewService.RATING_WEIGHTS.get(rating, 0.0)
