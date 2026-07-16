"""Experience ranker - 经验排序评分.

匹配评分函数:
    score = f(
        context_similarity,    # 上下文相似度
        success_rate,          # 历史成功率
        reuse_count,           # 复用次数
        domain_distance,       # 领域距离
        recency,               # 时效性
        confidence,            # 置信度
        trust_score,           # 信任评分（治理层）
    ) * decay_factor           # 衰减因子（治理层，乘法惩罚）

各因子权重可配置，默认等权重。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.models.experience import Experience
from app.services.governance.decay import DecayManager
from app.services.governance.trust import TrustScorer
from app.services.retrieval.matcher import MatchResult


@dataclass
class ScoreFactors:
    """评分因子."""

    context_similarity: float = 0.0  # 上下文相似度 [0, 1]
    success_rate: float = 0.0  # 历史成功率 [0, 1]
    reuse_count: float = 0.0  # 复用次数（归一化后） [0, 1]
    domain_distance: float = 0.0  # 领域距离（0=同域, 1=完全不同域） [0, 1]
    recency: float = 0.0  # 时效性 [0, 1] (1=最新)
    confidence: float = 0.0  # 置信度 [0, 1]
    trust_score: float = 0.0  # 信任评分（治理层） [0, 1]
    decay_factor: float = 1.0  # 衰减因子（治理层） [0.1, 1.0]（乘法惩罚）

    def to_dict(self) -> dict:
        return {
            "context_similarity": round(self.context_similarity, 4),
            "success_rate": round(self.success_rate, 4),
            "reuse_count": round(self.reuse_count, 4),
            "domain_distance": round(self.domain_distance, 4),
            "recency": round(self.recency, 4),
            "confidence": round(self.confidence, 4),
            "trust_score": round(self.trust_score, 4),
            "decay_factor": round(self.decay_factor, 4),
        }


@dataclass
class RankedResult:
    """排序后的结果."""

    experience: Experience
    total_score: float
    factors: ScoreFactors
    similarity: float = 0.0

    def to_dict(self) -> dict:
        return {
            "experience_id": str(self.experience.id),
            "total_score": round(self.total_score, 4),
            "similarity": round(self.similarity, 4),
            "factors": self.factors.to_dict(),
        }


# ── 默认权重 ──

DEFAULT_WEIGHTS: dict[str, float] = {
    "context_similarity": 0.25,
    "success_rate": 0.15,
    "reuse_count": 0.08,
    "domain_distance": 0.07,
    "recency": 0.12,
    "confidence": 0.13,
    "trust_score": 0.20,
}


class ExperienceRanker:
    """经验排序器 - 基于多因子评分函数排序.

    base_score = Σ(weight_i * factor_i)
    effective_score = base_score * decay_factor

    各因子:
    - context_similarity: 向量相似度（来自 matcher）
    - success_rate: outcome.success == True -> 1.0, False -> 0.0
    - reuse_count: 归一化的复用次数
    - domain_distance: 0 (同域) / 0.5 (相关域) / 1.0 (不同域)
    - recency: 基于时间衰减
    - confidence: experience.confidence_score
    - trust_score: 治理层信任评分（TrustScorer）
    - decay_factor: 治理层衰减因子（DecayManager），作为乘法惩罚
    """

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        max_reuse_count: int = 100,
        recency_half_life_days: int = 30,
    ) -> None:
        self.weights = weights or DEFAULT_WEIGHTS
        self.max_reuse_count = max_reuse_count
        self.recency_half_life_days = recency_half_life_days
        self._trust_scorer = TrustScorer()
        self._decay_manager = DecayManager()

    def rank(
        self,
        matches: list[MatchResult],
        query_domain: str | None = None,
        reuse_counts: dict | None = None,
    ) -> list[RankedResult]:
        """对匹配结果进行多因子排序.

        Args:
            matches: 匹配结果列表
            query_domain: 查询领域（用于计算领域距离）
            reuse_counts: 经验ID到复用次数的映射

        Returns:
            排序后的结果列表（按总分降序）
        """
        reuse_counts = reuse_counts or {}
        now = datetime.now(timezone.utc)
        results: list[RankedResult] = []

        for match in matches:
            exp = match.experience

            # ── 计算各因子 ──
            factors = ScoreFactors()

            # 1. 上下文相似度
            factors.context_similarity = match.similarity

            # 2. 成功率
            outcome = exp.outcome or {}
            factors.success_rate = 1.0 if outcome.get("success") else 0.0

            # 3. 复用次数（归一化）
            count = reuse_counts.get(str(exp.id), 0)
            factors.reuse_count = min(count / self.max_reuse_count, 1.0)

            # 4. 领域距离
            exp_domain = (exp.context or {}).get("domain", "")
            if query_domain and exp_domain:
                if exp_domain == query_domain:
                    factors.domain_distance = 0.0  # 同域
                else:
                    factors.domain_distance = 1.0  # 不同域
            else:
                factors.domain_distance = 0.5  # 未知

            # 5. 时效性（指数衰减）
            if exp.created_at:
                age_days = (now - exp.created_at).days
                half_life = self.recency_half_life_days
                factors.recency = 0.5 ** (age_days / half_life) if half_life > 0 else 0.5
            else:
                factors.recency = 0.0

            # 6. 置信度
            factors.confidence = exp.confidence_score or 0.0

            # 7. 信任评分（治理层 TrustScorer）
            factors.trust_score = self._trust_scorer.compute(exp)

            # 8. 衰减因子（治理层 DecayManager）
            factors.decay_factor = self._decay_manager.compute_decay_factor(exp)

            # ── 计算总分 ──
            total_score = self._compute_score(factors)

            results.append(RankedResult(
                experience=exp,
                total_score=total_score,
                factors=factors,
                similarity=match.similarity,
            ))

        # 按总分降序排序
        results.sort(key=lambda r: r.total_score, reverse=True)

        return results

    def _compute_score(self, factors: ScoreFactors) -> float:
        """计算加权总分.

        base_score = Σ(weight_i * factor_i)
        effective_score = base_score * decay_factor

        注意: domain_distance 越小越好（0=同域），所以用 (1 - domain_distance)
        decay_factor 作为乘法惩罚（1.0=无衰减, 0.1=严重衰减）
        """
        base_score = (
            self.weights["context_similarity"] * factors.context_similarity
            + self.weights["success_rate"] * factors.success_rate
            + self.weights["reuse_count"] * factors.reuse_count
            + self.weights["domain_distance"] * (1.0 - factors.domain_distance)
            + self.weights["recency"] * factors.recency
            + self.weights["confidence"] * factors.confidence
            + self.weights["trust_score"] * factors.trust_score
        )
        return base_score * factors.decay_factor

    def update_weights(self, new_weights: dict[str, float]) -> None:
        """更新评分权重."""
        self.weights.update(new_weights)

    def get_weights(self) -> dict[str, float]:
        """获取当前权重."""
        return self.weights.copy()
