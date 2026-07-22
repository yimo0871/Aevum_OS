"""经验压缩与遗忘系统 -- 低质/冗余/过期经验的压缩和软删除."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.experience import Experience, ExperienceRelation
from app.services.governance.decay import DecayManager
from app.services.governance.trust import TrustScorer

logger = logging.getLogger(__name__)


class CompressionManager:
    """经验压缩与遗忘管理.

    职责:
    - 压缩低质/冗余经验（保留摘要，降低权重）
    - 遗忘过期/零复用经验（软删除，记录原因）
    - 自动清理批量遗忘
    - 发现同域近似重复经验
    """

    VALID_FORGET_REASONS = {"expired", "low_quality", "redundant", "zero_reuse"}

    def __init__(self) -> None:
        self.decay_manager = DecayManager()
        self.trust_scorer = TrustScorer()

    async def compress_experience(
        self, experience_id: UUID, session: AsyncSession
    ) -> Experience | None:
        """压缩一条经验 -- 设置 compressed 标记、存储摘要、降低信任权重.

        Args:
            experience_id: 经验 ID
            session: 异步数据库会话

        Returns:
            更新后的 Experience，若不存在返回 None
        """
        logger.info("[COMPRESS] 开始压缩经验: experience_id=%s", experience_id)

        experience = await session.get(Experience, experience_id)
        if experience is None:
            logger.warning("[COMPRESS] 经验不存在: experience_id=%s", experience_id)
            return None

        # ── 生成摘要（基于意图 + 反思 + 可复用模式）──
        summary_parts = []
        if experience.intent:
            summary_parts.append(experience.intent[:200])
        reflection = experience.reflection or {}
        if isinstance(reflection, dict):
            what_worked = reflection.get("what_worked", [])
            if what_worked:
                summary_parts.append("worked: " + ", ".join(str(w) for w in what_worked[:3]))
            what_failed = reflection.get("what_failed", [])
            if what_failed:
                summary_parts.append("failed: " + ", ".join(str(f) for f in what_failed[:3]))
        summary = " | ".join(summary_parts) if summary_parts else "compressed experience"

        # ── 设置压缩标记与摘要 ──
        experience.compressed = True
        experience.compression_summary = summary

        # ── 降低信任权重（置信度减半）──
        original_confidence = experience.confidence_score or 0.0
        experience.confidence_score = round(original_confidence * 0.5, 4)

        # ── 记录压缩元数据到 provenance ──
        provenance = dict(experience.provenance) if experience.provenance else {}
        provenance["compressed_at"] = datetime.now(timezone.utc).isoformat()
        provenance["original_confidence"] = original_confidence
        experience.provenance = provenance

        await session.flush()
        logger.info(
            "[COMPRESS] 压缩完成: experience_id=%s, confidence %.4f -> %.4f",
            experience_id, original_confidence, experience.confidence_score,
        )
        return experience

    async def forget_experience(
        self,
        experience_id: UUID,
        reason: str,
        session: AsyncSession,
    ) -> Experience | None:
        """遗忘一条经验 -- 软删除，设置 status=forgotten 并记录原因.

        Args:
            experience_id: 经验 ID
            reason: 遗忘原因 (expired/low_quality/redundant/zero_reuse)
            session: 异步数据库会话

        Returns:
            更新后的 Experience，若不存在返回 None
        """
        if reason not in self.VALID_FORGET_REASONS:
            raise ValueError(
                f"无效的遗忘原因: {reason}，有效值: {self.VALID_FORGET_REASONS}"
            )

        logger.info(
            "[FORGET] 开始遗忘经验: experience_id=%s, reason=%s",
            experience_id, reason,
        )

        experience = await session.get(Experience, experience_id)
        if experience is None:
            logger.warning("[FORGET] 经验不存在: experience_id=%s", experience_id)
            return None

        experience.status = "forgotten"

        provenance = dict(experience.provenance) if experience.provenance else {}
        provenance["forget_reason"] = reason
        provenance["forgotten_at"] = datetime.now(timezone.utc).isoformat()
        experience.provenance = provenance

        await session.flush()
        logger.info(
            "[FORGET] 遗忘完成: experience_id=%s, reason=%s",
            experience_id, reason,
        )
        return experience

    async def auto_cleanup(
        self,
        session: AsyncSession,
        threshold_days: int = 90,
        min_trust: float = 0.1,
        min_reuse: int = 0,
    ) -> list[Experience]:
        """自动清理 -- 遗忘满足条件的经验.

        条件（全部满足）:
        - 创建时间超过 threshold_days 天
        - 信任评分低于 min_trust
        - 复用次数低于 min_reuse

        Args:
            session: 异步数据库会话
            threshold_days: 年龄阈值（天）
            min_trust: 信任评分上限（低于此值才清理）
            min_reuse: 复用次数上限（低于此值才清理）

        Returns:
            被遗忘的经验列表
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=threshold_days)
        logger.info(
            "[CLEANUP] 自动清理开始: cutoff=%s, min_trust=%s, min_reuse=%s",
            cutoff, min_trust, min_reuse,
        )

        # ── 查询候选经验：未遗忘 + 早于截止时间 ──
        query = select(Experience).where(
            Experience.created_at < cutoff,
        )
        # 仅处理未被遗忘的经验
        query = query.where(Experience.status == "active")
        result = await session.execute(query)
        candidates = list(result.scalars().all())

        logger.info("[CLEANUP] 候选经验数: %d", len(candidates))

        forgotten: list[Experience] = []
        for exp in candidates:
            # ── 计算信任评分 ──
            trust_score = self.trust_scorer.compute(exp)

            # ── 查询复用次数 ──
            reuse_result = await session.execute(
                select(func.count(ExperienceRelation.id)).where(
                    ExperienceRelation.target_id == exp.id,
                    ExperienceRelation.relation_type == "reuse",
                )
            )
            reuse_count = reuse_result.scalar() or 0

            # ── 判断是否满足清理条件 ──
            if trust_score < min_trust and reuse_count < min_reuse:
                # 决定原因
                if reuse_count == 0:
                    reason = "zero_reuse"
                elif trust_score < 0.05:
                    reason = "low_quality"
                else:
                    reason = "expired"

                exp.status = "forgotten"
                provenance = dict(exp.provenance) if exp.provenance else {}
                provenance["forget_reason"] = reason
                provenance["forgotten_at"] = datetime.now(timezone.utc).isoformat()
                provenance["cleanup_trust_score"] = trust_score
                provenance["cleanup_reuse_count"] = reuse_count
                exp.provenance = provenance
                forgotten.append(exp)

        if forgotten:
            await session.flush()
        logger.info("[CLEANUP] 自动清理完成: 遗忘 %d 条经验", len(forgotten))
        return forgotten

    async def find_redundant(
        self,
        domain: str,
        session: AsyncSession,
        similarity_threshold: float = 0.95,
    ) -> list[tuple[Experience, Experience, float]]:
        """发现同域近似重复经验.

        基于意图文本相似度（Jaccard 相似度）和相同域来检测近似重复。
        相似度 >= similarity_threshold 的经验对被视为冗余。

        Args:
            domain: 经验域 (context.domain)
            session: 异步数据库会话
            similarity_threshold: 相似度阈值 (0.0-1.0)

        Returns:
            冗余经验对列表 [(exp_a, exp_b, similarity), ...]
        """
        logger.info(
            "[REDUNDANT] 查找冗余经验: domain=%s, threshold=%s",
            domain, similarity_threshold,
        )

        # ── 查询同域活跃经验 ──
        query = select(Experience).where(
            Experience.context["domain"].astext == domain,
            Experience.status == "active",
        )
        result = await session.execute(query)
        experiences = list(result.scalars().all())

        logger.info("[REDUNDANT] 同域经验数: %d", len(experiences))

        redundant_pairs: list[tuple[Experience, Experience, float]] = []
        for i, exp_a in enumerate(experiences):
            tokens_a = self._tokenize(exp_a.intent)
            if not tokens_a:
                continue
            for exp_b in experiences[i + 1:]:
                tokens_b = self._tokenize(exp_b.intent)
                if not tokens_b:
                    continue
                similarity = self._jaccard_similarity(tokens_a, tokens_b)
                if similarity >= similarity_threshold:
                    redundant_pairs.append((exp_a, exp_b, similarity))

        logger.info(
            "[REDUNDANT] 查找完成: 发现 %d 对冗余经验",
            len(redundant_pairs),
        )
        return redundant_pairs

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        """将文本分词为小写 token 集合."""
        if not text:
            return set()
        return {token.strip(".,;:!?()[]{}\"'").lower() for token in text.split() if token.strip()}

    @staticmethod
    def _jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
        """计算两个集合的 Jaccard 相似度."""
        if not set_a or not set_b:
            return 0.0
        intersection = set_a & set_b
        union = set_a | set_b
        return len(intersection) / len(union) if union else 0.0
